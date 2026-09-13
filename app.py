from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from pathlib import Path
from datetime import date, timedelta
import secrets
import os
import mysql.connector
from flask import Flask, abort, render_template, request, redirect, url_for, flash, session, send_file
from dotenv import load_dotenv

load_dotenv()

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)
import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CA_PATH = os.path.join(BASE_DIR, "ca.pem")

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)

app.secret_key = os.environ.get("SECRET_KEY")

db = mysql.connector.connect(
    host=os.environ.get("DB_HOST"),
    port=int(os.environ.get("DB_PORT")),
    user=os.environ.get("DB_USER"),
    password=os.environ.get("DB_PASSWORD"),
    database=os.environ.get("DB_NAME"),
    ssl_ca=CA_PATH,
    ssl_verify_cert=True
)
print("Database connection established successfully.")









templates_dir = Path(app.template_folder)

# Home page
@app.route("/")
def index():
    return render_template("index.html")


#loginpage

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "")

    db_role_map = {
        "admin": "system_admin",
        "hospital": "hospital_admin",
        "doctor": "doctor",
        "patient": "patient"
    }
    db_role = db_role_map.get(role, role)

    try:
        db.ping(reconnect=True, attempts=1, delay=0)
        cursor = db.cursor(dictionary=True)

        # Patient credentials are stored on the patient record. Resolve that
        # record first so an unrelated users row cannot reject valid access.
        if db_role == "patient":
            cursor.execute(
                "SELECT p.patient_id, p.hospital_id, p.full_name, p.email, p.password, "
                "u.user_id FROM patients p "
                "LEFT JOIN users u ON u.email=p.email AND u.role='patient' "
                "WHERE p.email=%s LIMIT 1",
                (email,),
            )
            patient_user = cursor.fetchone()
            if patient_user:
                user = {
                    "user_id": patient_user["user_id"],
                    "full_name": patient_user["full_name"],
                    "email": patient_user["email"],
                    "password": patient_user["password"] or "",
                    "role": "patient",
                    "patient_id": patient_user["patient_id"],
                    "hospital_id": patient_user["hospital_id"],
                }
            else:
                user = None
        else:
            cursor.execute(
                "SELECT user_id, full_name, email, password, role FROM users "
                "WHERE email=%s AND role=%s",
                (email, db_role),
            )
            user = cursor.fetchone()

        if not user:
            flash("User is not registered.", "danger")
            return redirect(url_for("login"))

        # Password verification
        password_matches = (
            check_password_hash(user["password"], password)
            if user["password"].startswith(("scrypt:", "pbkdf2:", "argon2:"))
            else user["password"] == password
        )
        if not password_matches:
            flash("Incorrect password.", "danger")
            return redirect(url_for("login"))
        if user["role"] == "patient":
            session["patient_id"] = user["patient_id"]
            session["patient_hospital_id"] = user["hospital_id"]

        # Login success
        session["user_id"] = user["user_id"]
        session["user_name"] = user["full_name"]
        session["user_role"] = user["role"]

        flash("Login successful!", "success")

        # Redirect according to role
        if user["role"] == "system_admin":
            return redirect("/system-admin/dashboard")
        elif user["role"] == "hospital_admin":
            return redirect("/hospital-admin/dashboard")
        elif user["role"] == "doctor":
            return redirect("/doctor/dashboard")
        elif user["role"] == "patient":
            return redirect("/patient/dashboard")

        return redirect("/")

    except mysql.connector.Error as err:
        flash(f"Database Error: {err}", "danger")
        return redirect(url_for("login"))

    finally:
        if 'cursor' in locals():
            cursor.close()


# ====================================================================
# Doctor Dashboard Route
# ====================================================================
@app.route("/doctor/dashboard")
@app.route("/doctor/dashboard.html")
def doctor_dashboard():
    if session.get("user_role") != "doctor":
        return redirect(url_for("login"))

    empty = {
        "doctor": {"full_name": "N/A", "specialization": "N/A", "hospital_name": "N/A"},
        "stats": {"patients": "N/A", "appointments": "N/A", "records": "N/A", "prescriptions": "N/A", "pending": "N/A"},
        "today_appointments": [], "recent_patients": [], "recent_records": [],
        "weekly_appointments": {"labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "scheduled": [0] * 7, "completed": [0] * 7},
    }
    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT u.email AS user_email, u.full_name AS user_name, d.hospital_id, d.doctor_id, d.full_name, d.specialization, "
            "h.hospital_name FROM users u INNER JOIN doctors d ON (d.email=u.email OR d.full_name=u.full_name) "
            "LEFT JOIN hospitals h ON h.hospital_id=d.hospital_id "
            "WHERE u.user_id=%s AND u.role='doctor' "
            "ORDER BY CASE WHEN d.email=u.email THEN 0 ELSE 1 END, d.doctor_id LIMIT 1",
            (session.get("user_id"),),
        )
        doctor = cursor.fetchone()
        if not doctor:
            return render_template("doctor/dashboard.html", **empty)

        doctor_id = doctor["doctor_id"]
        hospital_id = doctor["hospital_id"]
        stats = {"patients": "N/A", "appointments": "N/A", "records": "N/A", "prescriptions": "N/A", "pending": "N/A"}
        today_appointments, recent_patients, recent_records = [], [], []
        weekly = {"labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "scheduled": [0] * 7, "completed": [0] * 7}

        def table_columns(table):
            cursor.execute(
                "SELECT COUNT(*) AS present FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name=%s",
                (table,),
            )
            if not cursor.fetchone()["present"]:
                return set()
            cursor.execute("SHOW COLUMNS FROM `" + table + "`")
            return {row["Field"] for row in cursor.fetchall()}

        record_columns = table_columns("medical_records")
        patient_columns = table_columns("patients")
        appointment_columns = table_columns("appointments")
        prescription_columns = table_columns("prescriptions")

        if {"hospital_id"}.issubset(patient_columns):
            cursor.execute("SELECT COUNT(*) AS count FROM patients WHERE hospital_id=%s", (hospital_id,))
            stats["patients"] = cursor.fetchone()["count"]
            if not record_columns:
                patient_date = "created_at" if "created_at" in patient_columns else None
                patient_order = f"ORDER BY {patient_date} DESC" if patient_date else "ORDER BY patient_id DESC"
                cursor.execute(f"SELECT patient_id, full_name, NULL AS last_visit, NULL AS diagnosis FROM patients WHERE hospital_id=%s {patient_order} LIMIT 5", (hospital_id,))
                recent_patients = cursor.fetchall()

        if record_columns and {"doctor_id", "hospital_id", "patient_id"}.issubset(record_columns):
            cursor.execute("SELECT COUNT(*) AS count FROM medical_records WHERE doctor_id=%s AND hospital_id=%s", (doctor_id, hospital_id))
            stats["records"] = cursor.fetchone()["count"]
            cursor.execute("SELECT COUNT(DISTINCT patient_id) AS count FROM medical_records WHERE doctor_id=%s AND hospital_id=%s", (doctor_id, hospital_id))
            stats["patients"] = cursor.fetchone()["count"]

            patient_name = "p.full_name" if "full_name" in patient_columns else "CAST(mr.patient_id AS CHAR)"
            patient_id = "p.patient_id" if "patient_id" in patient_columns else "mr.patient_id"
            last_visit = "MAX(mr.created_at)" if "created_at" in record_columns else "NULL"
            diagnosis = "MAX(mr.diagnosis)" if "diagnosis" in record_columns else ("MAX(mr.title)" if "title" in record_columns else "NULL")
            join = "LEFT JOIN patients p ON p.patient_id=mr.patient_id" if patient_columns else ""
            cursor.execute(
                f"SELECT {patient_name} AS full_name, {patient_id} AS patient_id, {last_visit} AS last_visit, {diagnosis} AS diagnosis "
                f"FROM medical_records mr {join} WHERE mr.doctor_id=%s AND mr.hospital_id=%s GROUP BY mr.patient_id, {patient_name} ORDER BY last_visit DESC LIMIT 5",
                (doctor_id, hospital_id),
            )
            recent_patients = cursor.fetchall()

            record_type = "mr.record_type" if "record_type" in record_columns else None
            record_id = next((f"mr.{name}" for name in ("medical_record_id", "record_id", "id") if name in record_columns), "NULL")
            record_title = "mr.title" if "title" in record_columns else ("mr.record_type" if "record_type" in record_columns else "NULL")
            record_date = "mr.created_at" if "created_at" in record_columns else "NULL"
            cursor.execute(
                f"SELECT {record_id} AS record_id, {record_title} AS title, mr.patient_id, {record_date} AS created_at "
                f"FROM medical_records mr WHERE mr.doctor_id=%s AND mr.hospital_id=%s ORDER BY created_at DESC LIMIT 5",
                (doctor_id, hospital_id),
            )
            recent_records = cursor.fetchall()
            if record_type:
                cursor.execute("SELECT COUNT(*) AS count FROM medical_records mr WHERE mr.doctor_id=%s AND mr.hospital_id=%s AND LOWER(mr.record_type)='prescription'", (doctor_id, hospital_id))
                stats["prescriptions"] = cursor.fetchone()["count"]
            if record_type and "status" in record_columns:
                cursor.execute("SELECT COUNT(*) AS count FROM medical_records mr WHERE mr.doctor_id=%s AND mr.hospital_id=%s AND LOWER(mr.record_type) IN ('lab result','lab') AND LOWER(mr.status) IN ('pending','new','review')", (doctor_id, hospital_id))
                stats["pending"] = cursor.fetchone()["count"]

        date_column = next((name for name in ("appointment_date", "scheduled_at", "appointment_time", "date", "created_at") if name in appointment_columns), None)
        if {"doctor_id", "hospital_id"}.issubset(appointment_columns) and date_column:
            cursor.execute(f"SELECT COUNT(*) AS count FROM appointments WHERE doctor_id=%s AND hospital_id=%s", (doctor_id, hospital_id))
            stats["appointments"] = cursor.fetchone()["count"]
            status_column = next((name for name in ("status", "appointment_status") if name in appointment_columns), None)
            patient_column = "patient_id" if "patient_id" in appointment_columns else None
            name_column = "full_name" if "full_name" in patient_columns else None
            patient_join = "LEFT JOIN patients p ON p.patient_id=a.patient_id" if patient_column and name_column else ""
            patient_select = "p.full_name AS patient_name" if patient_join else "'N/A' AS patient_name"
            status_select = f"a.{status_column} AS status" if status_column else "'N/A' AS status"
            cursor.execute(f"SELECT a.{date_column} AS appointment_date, {patient_select}, {status_select} FROM appointments a {patient_join} WHERE a.doctor_id=%s AND a.hospital_id=%s AND DATE(a.{date_column})=CURRENT_DATE() ORDER BY a.{date_column}", (doctor_id, hospital_id))
            today_appointments = cursor.fetchall()
            cursor.execute(f"SELECT WEEKDAY(a.{date_column}) AS weekday, COUNT(*) AS count FROM appointments a WHERE a.doctor_id=%s AND a.hospital_id=%s AND YEARWEEK(a.{date_column}, 1)=YEARWEEK(CURRENT_DATE(), 1) GROUP BY WEEKDAY(a.{date_column})", (doctor_id, hospital_id))
            for row in cursor.fetchall():
                if row["weekday"] is not None:
                    weekly["scheduled"][int(row["weekday"])] = row["count"]
            if status_column:
                cursor.execute(f"SELECT WEEKDAY(a.{date_column}) AS weekday, COUNT(*) AS count FROM appointments a WHERE a.doctor_id=%s AND a.hospital_id=%s AND YEARWEEK(a.{date_column}, 1)=YEARWEEK(CURRENT_DATE(), 1) AND LOWER(a.{status_column}) IN ('completed','complete') GROUP BY WEEKDAY(a.{date_column})", (doctor_id, hospital_id))
                for row in cursor.fetchall():
                    if row["weekday"] is not None:
                        weekly["completed"][int(row["weekday"])] = row["count"]

        if prescription_columns and "record_id" in prescription_columns and record_columns and "record_id" in record_columns:
            cursor.execute("SELECT COUNT(*) AS count FROM prescriptions pr INNER JOIN medical_records mr ON mr.record_id=pr.record_id WHERE mr.doctor_id=%s AND mr.hospital_id=%s", (doctor_id, hospital_id))
            stats["prescriptions"] = cursor.fetchone()["count"]

        return render_template("doctor/dashboard.html", doctor=doctor, stats=stats, today_appointments=today_appointments, recent_patients=recent_patients, recent_records=recent_records, weekly_appointments=weekly)
    except Exception as error:
        print("DB Error Doctor Dashboard:", error)
        return render_template("doctor/dashboard.html", **empty)
    finally:
        if cursor is not None:
            cursor.close()


# ====================================================================
# Doctor Patients Routes
# ====================================================================
def _get_logged_in_doctor(cursor):
    cursor.execute(
        "SELECT u.email AS user_email, u.full_name AS user_name, d.doctor_id, d.hospital_id, "
        "d.full_name, d.specialization, h.hospital_name "
        "FROM users u INNER JOIN doctors d ON (d.email=u.email OR d.full_name=u.full_name) "
        "LEFT JOIN hospitals h ON h.hospital_id=d.hospital_id "
        "WHERE u.user_id=%s AND u.role='doctor' "
        "ORDER BY CASE WHEN d.email=u.email THEN 0 ELSE 1 END, d.doctor_id LIMIT 1",
        (session.get("user_id"),),
    )
    return cursor.fetchone()


def _doctor_patients_redirect():
    return redirect(url_for("doctor_patients"))


def _doctor_profile_redirect(message=None, category=None):
    if message:
        flash(message, category or "info")
    return redirect(url_for("doctor_profile"))


@app.route("/doctor/profile", methods=["GET", "POST"])
@app.route("/doctor/profile.html", methods=["GET", "POST"])
def doctor_profile():
    if session.get("user_role") != "doctor":
        return redirect(url_for("login"))

    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        doctor = _get_logged_in_doctor(cursor)
        if not doctor:
            return redirect(url_for("login"))

        cursor.execute(
            "SELECT d.*, h.hospital_name FROM doctors d "
            "LEFT JOIN hospitals h ON h.hospital_id=d.hospital_id "
            "WHERE d.doctor_id=%s AND d.hospital_id=%s",
            (doctor["doctor_id"], doctor["hospital_id"]),
        )
        profile = cursor.fetchone()
        if not profile:
            return _doctor_profile_redirect("Your doctor profile could not be found.", "danger")
        profile["hospital_name"] = profile.get("hospital_name") or "N/A"
        for field in ("created_at",):
            if profile.get(field) is not None:
                profile[field] = str(profile[field])

        cursor.execute("SELECT COUNT(*) AS count FROM patients WHERE hospital_id=%s", (profile["hospital_id"],))
        patient_count = cursor.fetchone()["count"]
        cursor.execute(
            "SELECT COUNT(*) AS present FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name='medical_records'"
        )
        record_count = "N/A"
        if cursor.fetchone()["present"]:
            cursor.execute(
                "SELECT COUNT(*) AS count FROM medical_records "
                "WHERE doctor_id=%s AND hospital_id=%s",
                (profile["doctor_id"], profile["hospital_id"]),
            )
            record_count = cursor.fetchone()["count"]

        if request.method == "POST":
            action = request.form.get("action", "profile").strip().lower()
            if action == "password":
                current_password = request.form.get("current_password", "")
                new_password = request.form.get("new_password", "")
                confirm_password = request.form.get("confirm_password", "")
                cursor.execute(
                    "SELECT password FROM users WHERE user_id=%s AND role='doctor'",
                    (session.get("user_id"),),
                )
                user = cursor.fetchone()
                stored_password = user.get("password", "") if user else ""
                password_valid = (
                    check_password_hash(stored_password, current_password)
                    if stored_password.startswith(("scrypt:", "pbkdf2:", "argon2:"))
                    else stored_password == current_password
                )
                if not user or not password_valid:
                    return _doctor_profile_redirect("Current password is incorrect.", "danger")
                if len(new_password) < 8:
                    return _doctor_profile_redirect("New password must be at least 8 characters.", "danger")
                if new_password != confirm_password:
                    return _doctor_profile_redirect("New passwords do not match.", "danger")
                hashed_password = generate_password_hash(new_password)
                cursor.execute(
                    "UPDATE users SET password=%s WHERE user_id=%s AND role='doctor'",
                    (hashed_password, session.get("user_id")),
                )
                cursor.execute(
                    "UPDATE doctors SET password=%s WHERE doctor_id=%s AND hospital_id=%s",
                    (hashed_password, profile["doctor_id"], profile["hospital_id"]),
                )
                db.commit()
                return _doctor_profile_redirect("Password updated successfully.", "success")

            fields = {
                "full_name": request.form.get("full_name", "").strip(),
                "email": request.form.get("email", "").strip().lower(),
                "phone": request.form.get("phone", "").strip(),
                "specialization": request.form.get("specialization", "").strip(),
                "department": request.form.get("department", "").strip(),
                "qualification": request.form.get("qualification", "").strip(),
                "license_number": request.form.get("license_number", "").strip(),
                "experience_years": request.form.get("experience_years", "").strip(),
            }
            if not fields["full_name"] or not fields["email"]:
                return _doctor_profile_redirect("Full name and email are required.", "danger")
            if "@" not in fields["email"] or " " in fields["email"]:
                return _doctor_profile_redirect("Enter a valid email address.", "danger")
            try:
                experience_years = int(fields["experience_years"]) if fields["experience_years"] else None
                if experience_years is not None and experience_years < 0:
                    raise ValueError
            except ValueError:
                return _doctor_profile_redirect("Experience must be a non-negative whole number.", "danger")

            cursor.execute(
                "SELECT doctor_id FROM doctors WHERE email=%s AND doctor_id<>%s",
                (fields["email"], profile["doctor_id"]),
            )
            if cursor.fetchone():
                return _doctor_profile_redirect("Another doctor already uses that email address.", "danger")
            cursor.execute(
                "SELECT user_id FROM users WHERE email=%s AND user_id<>%s",
                (fields["email"], session.get("user_id")),
            )
            if cursor.fetchone():
                return _doctor_profile_redirect("That email address is already in use.", "danger")

            cursor.execute(
                "UPDATE doctors SET full_name=%s, email=%s, phone=%s, specialization=%s, "
                "department=%s, qualification=%s, license_number=%s, experience_years=%s "
                "WHERE doctor_id=%s AND hospital_id=%s",
                (
                    fields["full_name"], fields["email"], fields["phone"], fields["specialization"],
                    fields["department"], fields["qualification"], fields["license_number"],
                    experience_years, profile["doctor_id"], profile["hospital_id"],
                ),
            )
            cursor.execute(
                "UPDATE users SET full_name=%s, email=%s, phone=%s "
                "WHERE user_id=%s AND role='doctor'",
                (fields["full_name"], fields["email"], fields["phone"], session.get("user_id")),
            )
            db.commit()
            return _doctor_profile_redirect("Profile updated successfully.", "success")

        return render_template(
            "doctor/profile.html", doctor=profile, patient_count=patient_count, record_count=record_count
        )
    except Exception as error:
        db.rollback()
        print("DB Error Doctor Profile:", error)
        return _doctor_profile_redirect("Unable to load or update your profile.", "danger")
    finally:
        if cursor is not None:
            cursor.close()


@app.route("/doctor/patients")
@app.route("/doctor/patients.html")
def doctor_patients():
    if session.get("user_role") != "doctor":
        return redirect(url_for("login"))

    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        doctor = _get_logged_in_doctor(cursor)
        if not doctor:
            return redirect(url_for("login"))

        hospital_id = doctor["hospital_id"]
        cursor.execute("SELECT patient_id, hospital_id, full_name, email, phone, date_of_birth, gender, blood_group, address, emergency_contact, emergency_phone, status, created_at FROM patients WHERE hospital_id=%s ORDER BY created_at DESC, patient_id DESC", (hospital_id,))
        patients = cursor.fetchall()
        for patient in patients:
            for field in ("date_of_birth", "created_at"):
                if patient.get(field) is not None:
                    patient[field] = str(patient[field])
        cursor.execute("SELECT COUNT(*) AS count FROM patients WHERE hospital_id=%s", (hospital_id,))
        total = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) AS count FROM patients WHERE hospital_id=%s AND LOWER(status)='active'", (hospital_id,))
        active = cursor.fetchone()["count"]

        return render_template(
            "doctor/patients.html",
            doctor=doctor,
            patients=patients,
            hospital_name=doctor.get("hospital_name") or "N/A",
            stats={"total": total, "active": active, "scheduled": "N/A", "pending": "N/A", "records": "N/A"},
        )
    except Exception as error:
        print("DB Error Doctor Patients:", error)
        return render_template(
            "doctor/patients.html",
            doctor={"full_name": "N/A", "specialization": "N/A", "hospital_name": "N/A"},
            patients=[],
            hospital_name="N/A",
            stats={"total": "N/A", "active": "N/A", "scheduled": "N/A", "pending": "N/A", "records": "N/A"},
        )
    finally:
        if cursor is not None:
            cursor.close()


@app.route("/doctor/patients/add", methods=["POST"])
def doctor_patients_add():
    if session.get("user_role") != "doctor":
        return redirect(url_for("login"))
    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        doctor = _get_logged_in_doctor(cursor)
        if not doctor:
            return redirect(url_for("login"))

        values = {field: request.form.get(field, "").strip() for field in (
            "full_name", "email", "phone", "date_of_birth", "gender", "blood_group", "address", "emergency_contact", "emergency_phone", "status"
        )}
        password = request.form.get("password", "").strip()
        if not values["full_name"] or not values["email"] or not password:
            flash("Name, email, and password are required.", "danger")
            return _doctor_patients_redirect()
        values["status"] = values["status"] or "active"
        cursor.execute("SELECT patient_id FROM patients WHERE email=%s", (values["email"],))
        if cursor.fetchone():
            flash("A patient with this email already exists.", "danger")
            return _doctor_patients_redirect()

        cursor.execute(
            "INSERT INTO patients (hospital_id, full_name, email, phone, password, date_of_birth, gender, blood_group, address, emergency_contact, emergency_phone, status) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (doctor["hospital_id"], values["full_name"], values["email"], values["phone"], password, values["date_of_birth"] or None, values["gender"], values["blood_group"], values["address"], values["emergency_contact"], values["emergency_phone"], values["status"]),
        )
        cursor.execute("SELECT user_id FROM users WHERE email=%s AND role='patient'", (values["email"],))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (hospital_id, full_name, email, password, role, phone) VALUES (%s,%s,%s,%s,'patient',%s)", (doctor["hospital_id"], values["full_name"], values["email"], password, values["phone"]))
        db.commit()
        flash("Patient added successfully.", "success")
    except Exception as error:
        db.rollback()
        flash(f"Unable to add patient: {error}", "danger")
    finally:
        if cursor is not None:
            cursor.close()
    return _doctor_patients_redirect()


@app.route("/doctor/patients/<int:patient_id>/edit", methods=["POST"])
def doctor_patients_edit(patient_id):
    if session.get("user_role") != "doctor":
        return redirect(url_for("login"))
    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        doctor = _get_logged_in_doctor(cursor)
        if not doctor:
            return redirect(url_for("login"))
        values = {field: request.form.get(field, "").strip() for field in (
            "full_name", "email", "phone", "date_of_birth", "gender", "blood_group", "address", "emergency_contact", "emergency_phone", "status"
        )}
        if not values["full_name"] or not values["email"]:
            flash("Name and email are required.", "danger")
            return _doctor_patients_redirect()
        cursor.execute("SELECT email FROM patients WHERE patient_id=%s AND hospital_id=%s", (patient_id, doctor["hospital_id"]))
        existing = cursor.fetchone()
        if not existing:
            flash("Patient not found or unauthorized.", "danger")
            return _doctor_patients_redirect()
        cursor.execute("SELECT patient_id FROM patients WHERE email=%s AND patient_id<>%s", (values["email"], patient_id))
        if cursor.fetchone():
            flash("Another patient already uses this email.", "danger")
            return _doctor_patients_redirect()
        values["status"] = values["status"] or "active"
        cursor.execute(
            "UPDATE patients SET full_name=%s,email=%s,phone=%s,date_of_birth=%s,gender=%s,blood_group=%s,address=%s,emergency_contact=%s,emergency_phone=%s,status=%s WHERE patient_id=%s AND hospital_id=%s",
            (values["full_name"], values["email"], values["phone"], values["date_of_birth"] or None, values["gender"], values["blood_group"], values["address"], values["emergency_contact"], values["emergency_phone"], values["status"], patient_id, doctor["hospital_id"]),
        )
        cursor.execute("UPDATE users SET full_name=%s,email=%s,phone=%s WHERE email=%s AND role='patient' AND hospital_id=%s", (values["full_name"], values["email"], values["phone"], existing["email"], doctor["hospital_id"]))
        db.commit()
        flash("Patient updated successfully.", "success")
    except Exception as error:
        db.rollback()
        flash(f"Unable to update patient: {error}", "danger")
    finally:
        if cursor is not None:
            cursor.close()
    return _doctor_patients_redirect()


@app.route("/doctor/patients/<int:patient_id>/status", methods=["POST"])
def doctor_patients_status(patient_id):
    if session.get("user_role") != "doctor":
        return redirect(url_for("login"))
    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        doctor = _get_logged_in_doctor(cursor)
        if not doctor:
            return redirect(url_for("login"))
        status = request.form.get("status", "active").strip() or "active"
        cursor.execute("UPDATE patients SET status=%s WHERE patient_id=%s AND hospital_id=%s", (status, patient_id, doctor["hospital_id"]))
        db.commit()
        flash("Patient status updated.", "success")
    except Exception as error:
        db.rollback()
        flash(f"Unable to update patient status: {error}", "danger")
    finally:
        if cursor is not None:
            cursor.close()
    return _doctor_patients_redirect()


@app.route("/doctor/patients/<int:patient_id>/delete", methods=["POST"])
def doctor_patients_delete(patient_id):
    if session.get("user_role") != "doctor":
        return redirect(url_for("login"))
    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        doctor = _get_logged_in_doctor(cursor)
        if not doctor:
            return redirect(url_for("login"))
        cursor.execute("SELECT email FROM patients WHERE patient_id=%s AND hospital_id=%s", (patient_id, doctor["hospital_id"]))
        patient = cursor.fetchone()
        if not patient:
            flash("Patient not found or unauthorized.", "danger")
            return _doctor_patients_redirect()
        cursor.execute("DELETE FROM users WHERE email=%s AND role='patient' AND hospital_id=%s", (patient["email"], doctor["hospital_id"]))
        cursor.execute("DELETE FROM patients WHERE patient_id=%s AND hospital_id=%s", (patient_id, doctor["hospital_id"]))
        db.commit()
        flash("Patient deleted successfully.", "success")
    except Exception as error:
        db.rollback()
        flash(f"Unable to delete patient: {error}", "danger")
    finally:
        if cursor is not None:
            cursor.close()
    return _doctor_patients_redirect()


# ====================================================================
# Doctor Create Record Routes
# ====================================================================
def _doctor_record_page(cursor, message=None, category=None):
    doctor = _get_logged_in_doctor(cursor)
    if not doctor:
        return None
    cursor.execute(
        "SELECT patient_id, full_name, email, phone, date_of_birth, gender, blood_group, address, status "
        "FROM patients WHERE hospital_id=%s ORDER BY full_name ASC, patient_id ASC",
        (doctor["hospital_id"],),
    )
    patients = cursor.fetchall()
    for patient in patients:
        if patient.get("date_of_birth") is not None:
            patient["date_of_birth"] = str(patient["date_of_birth"])
    cursor.execute(
        "SELECT COUNT(*) AS present FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='medical_records'"
    )
    record_table_exists = bool(cursor.fetchone()["present"])
    form_token = secrets.token_urlsafe(24)
    session["doctor_record_form_token"] = form_token
    return render_template(
        "doctor/create_record.html",
        doctor=doctor,
        patients=patients,
        record_table_exists=record_table_exists,
        record_form_token=form_token,
        default_visit_datetime=date.today().isoformat() + "T00:00",
        message=message,
        message_category=category,
    )


@app.route("/doctor/create-record", methods=["GET", "POST"])
@app.route("/doctor/create_record.html", methods=["GET", "POST"])
def doctor_create_record():
    if session.get("user_role") != "doctor":
        return redirect(url_for("login"))

    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        if request.method == "GET":
            page = _doctor_record_page(cursor)
            return page or redirect(url_for("login"))

        submitted_token = request.form.get("form_token", "")
        if not submitted_token or submitted_token != session.pop("doctor_record_form_token", None):
            return _doctor_record_page(cursor, "This form was already submitted or has expired. Please reload and try again.", "warning")

        doctor = _get_logged_in_doctor(cursor)
        if not doctor:
            return redirect(url_for("login"))
        patient_id = request.form.get("patient_id", "").strip()
        record_type = request.form.get("record_type", "").strip()
        visit_datetime = request.form.get("visit_datetime", "").strip()
        diagnosis = request.form.get("diagnosis", "").strip()
        notes = request.form.get("notes", "").strip()
        if not patient_id or not record_type or not visit_datetime or not diagnosis or not notes or request.form.get("confirmed_by_doctor") != "1":
            return _doctor_record_page(cursor, "Patient, record type, date, diagnosis, notes, and doctor confirmation are required.", "danger")

        cursor.execute("SELECT patient_id FROM patients WHERE patient_id=%s AND hospital_id=%s", (patient_id, doctor["hospital_id"]))
        if not cursor.fetchone():
            return _doctor_record_page(cursor, "Selected patient is not part of your hospital.", "danger")

        cursor.execute("SELECT COUNT(*) AS present FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='medical_records'")
        if not cursor.fetchone()["present"]:
            return _doctor_record_page(cursor, "Medical records table is not available. No record was saved.", "warning")

        cursor.execute("SHOW COLUMNS FROM medical_records")
        columns = {row["Field"]: row for row in cursor.fetchall()}
        required = {"doctor_id", "hospital_id", "patient_id"}
        if not required.issubset(columns):
            return _doctor_record_page(cursor, "Medical records table does not support doctor and hospital links. No record was saved.", "warning")

        values = {"doctor_id": doctor["doctor_id"], "hospital_id": doctor["hospital_id"], "patient_id": int(patient_id)}
        field_values = {
            "record_type": record_type, "diagnosis": diagnosis,
            "icd10_code": request.form.get("icd10_code", "").strip(),
            "symptoms": request.form.get("symptoms", request.form.get("chief_complaint", "")).strip(),
            "clinical_notes": notes,
            "treatment_procedure": request.form.get("treatment", "").strip(),
            "followup_instructions": request.form.get("followup", "").strip(),
            "blood_pressure": request.form.get("bp", "").strip(),
            "heart_rate": request.form.get("hr", "").strip(),
            "temperature": request.form.get("temp", "").strip(),
            "spo2": request.form.get("spo2", "").strip(),
            "height_cm": request.form.get("height", "").strip(),
            "weight_kg": request.form.get("weight", "").strip(),
            "bmi": request.form.get("bmi", "").strip(),
            "confirmed_by_doctor": 1 if request.form.get("confirmed_by_doctor") == "1" else 0,
            "visit_datetime": visit_datetime, "status": "saved",
        }
        for field, value in field_values.items():
            if field in columns and value != "":
                values[field] = value

        insert_fields = list(values)
        placeholders = ",".join(["%s"] * len(insert_fields))
        cursor.execute(
            f"INSERT INTO medical_records ({','.join(insert_fields)}) VALUES ({placeholders})",
            tuple(values[field] for field in insert_fields),
        )
        record_id = cursor.lastrowid

        medication_rows = zip(
            request.form.getlist("med_name[]"),
            request.form.getlist("med_dose[]"),
            request.form.getlist("med_freq[]"),
            request.form.getlist("med_dur[]"),
        )
        for medication_name, dosage, frequency, duration in medication_rows:
            if medication_name.strip():
                cursor.execute(
                    "INSERT INTO prescriptions (record_id, medication_name, dosage, frequency, duration) VALUES (%s,%s,%s,%s,%s)",
                    (record_id, medication_name.strip(), dosage.strip(), frequency.strip(), duration.strip()),
                )

        upload_dir = Path(app.static_folder) / "uploads" / "medical_records"
        upload_dir.mkdir(parents=True, exist_ok=True)
        for uploaded_file in request.files.getlist("attachments[]"):
            if not uploaded_file or not uploaded_file.filename:
                continue
            safe_name = secure_filename(uploaded_file.filename)
            if not safe_name:
                continue
            stored_name = f"{record_id}_{secrets.token_hex(8)}_{safe_name}"
            stored_path = upload_dir / stored_name
            uploaded_file.save(stored_path)
            cursor.execute(
                "INSERT INTO record_attachments (record_id, file_name, file_path, file_type, file_size_kb) VALUES (%s,%s,%s,%s,%s)",
                (record_id, uploaded_file.filename, f"uploads/medical_records/{stored_name}", (uploaded_file.mimetype or "application/octet-stream")[:20], max(1, stored_path.stat().st_size // 1024)),
            )
        db.commit()
        flash("Medical record saved successfully.", "success")
        return redirect(url_for("doctor_medical_history", saved="1", patient_id=patient_id))
    except Exception as error:
        db.rollback()
        print("DB Error Doctor Create Record:", error)
        if cursor is not None:
            page = _doctor_record_page(cursor, "Unable to save the medical record. No data was changed.", "danger")
            return page or redirect(url_for("login"))
        return redirect(url_for("doctor_create_record"))
    finally:
        if cursor is not None:
            cursor.close()


@app.route("/doctor/medical-history")
@app.route("/doctor/medical_history.html")
def doctor_medical_history():
    if session.get("user_role") != "doctor":
        return redirect(url_for("login"))
    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        doctor = _get_logged_in_doctor(cursor)
        if not doctor:
            return redirect(url_for("login"))
        cursor.execute(
            "SELECT patient_id, full_name, email, phone, date_of_birth, gender, blood_group, address, status "
            "FROM patients WHERE hospital_id=%s ORDER BY full_name, patient_id",
            (doctor["hospital_id"],),
        )
        patients = cursor.fetchall()
        for patient in patients:
            for field in ("date_of_birth", "created_at", "updated_at"):
                if patient.get(field) is not None:
                    patient[field] = str(patient[field])

        cursor.execute(
            "SELECT COUNT(*) AS present FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name='medical_records'"
        )
        records = []
        if cursor.fetchone()["present"]:
            cursor.execute(
                "SELECT mr.*, p.full_name AS patient_name FROM medical_records mr "
                "INNER JOIN patients p ON p.patient_id=mr.patient_id "
                "WHERE mr.doctor_id=%s AND mr.hospital_id=%s AND p.hospital_id=%s "
                "ORDER BY mr.visit_datetime ASC, mr.record_id ASC",
                (doctor["doctor_id"], doctor["hospital_id"], doctor["hospital_id"]),
            )
            records = cursor.fetchall()

            cursor.execute(
                "SELECT COUNT(*) AS present FROM information_schema.tables "
                "WHERE table_schema=DATABASE() AND table_name='prescriptions'"
            )
            prescriptions_available = bool(cursor.fetchone()["present"])
            cursor.execute(
                "SELECT COUNT(*) AS present FROM information_schema.tables "
                "WHERE table_schema=DATABASE() AND table_name='record_attachments'"
            )
            attachments_available = bool(cursor.fetchone()["present"])
            for record in records:
                for field, value in record.items():
                    if value is not None and not isinstance(value, (str, int, float, bool)):
                        record[field] = str(value)
                record["prescriptions"] = []
                record["attachments"] = []
                if prescriptions_available:
                    cursor.execute(
                        "SELECT medication_name, dosage, frequency, duration "
                        "FROM prescriptions WHERE record_id=%s ORDER BY prescription_id",
                        (record["record_id"],),
                    )
                    record["prescriptions"] = cursor.fetchall()
                if attachments_available:
                    cursor.execute(
                        "SELECT file_name, file_path, file_type, file_size_kb "
                        "FROM record_attachments WHERE record_id=%s ORDER BY attachment_id",
                        (record["record_id"],),
                    )
                    record["attachments"] = cursor.fetchall()
        selected_patient_id = request.args.get("patient_id", "")
        if selected_patient_id:
            records = [record for record in records if str(record["patient_id"]) == str(selected_patient_id)]
        selected_patient = next((patient for patient in patients if str(patient["patient_id"]) == str(selected_patient_id)), None)
        return render_template("doctor/medical_history.html", doctor=doctor, patients=patients, records=records, selected_patient=selected_patient, selected_patient_id=selected_patient_id, saved=request.args.get("saved") == "1")
    except Exception as error:
        print("DB Error Doctor Medical History:", error)
        return render_template("doctor/medical_history.html", doctor={"full_name": "N/A", "specialization": "N/A", "hospital_name": "N/A"}, patients=[], records=[], selected_patient=None, selected_patient_id="", saved=False)
    finally:
        if cursor is not None:
            cursor.close()


@app.route("/doctor/medical-records/<int:record_id>/edit", methods=["POST"])
def doctor_medical_record_edit(record_id):
    if session.get("user_role") != "doctor":
        return redirect(url_for("login"))
    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        doctor = _get_logged_in_doctor(cursor)
        if not doctor:
            return redirect(url_for("login"))
        fields = {
            "record_type": request.form.get("record_type", "").strip(),
            "diagnosis": request.form.get("diagnosis", "").strip(),
            "clinical_notes": request.form.get("clinical_notes", "").strip(),
            "treatment_procedure": request.form.get("treatment_procedure", "").strip(),
            "followup_instructions": request.form.get("followup_instructions", "").strip(),
            "status": request.form.get("status", "saved").strip() or "saved",
        }
        if not fields["record_type"] or not fields["diagnosis"] or not fields["clinical_notes"]:
            flash("Record type, diagnosis, and clinical notes are required.", "danger")
            return redirect(url_for("doctor_medical_history"))
        cursor.execute("UPDATE medical_records SET record_type=%s, diagnosis=%s, clinical_notes=%s, treatment_procedure=%s, followup_instructions=%s, status=%s WHERE record_id=%s AND doctor_id=%s AND hospital_id=%s", (*fields.values(), record_id, doctor["doctor_id"], doctor["hospital_id"]))
        db.commit()
        flash("Medical record updated successfully.", "success")
    except Exception as error:
        db.rollback()
        flash(f"Unable to update medical record: {error}", "danger")
    finally:
        if cursor is not None:
            cursor.close()
    return redirect(url_for("doctor_medical_history"))


@app.route("/doctor/medical-records/<int:record_id>/delete", methods=["POST"])
def doctor_medical_record_delete(record_id):
    if session.get("user_role") != "doctor":
        return redirect(url_for("login"))
    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        doctor = _get_logged_in_doctor(cursor)
        if not doctor:
            return redirect(url_for("login"))
        cursor.execute("SELECT file_path FROM record_attachments WHERE record_id=%s", (record_id,))
        attachment_paths = [row["file_path"] for row in cursor.fetchall()]
        cursor.execute("DELETE FROM medical_records WHERE record_id=%s AND doctor_id=%s AND hospital_id=%s", (record_id, doctor["doctor_id"], doctor["hospital_id"]))
        db.commit()
        for relative_path in attachment_paths:
            file_path = Path(app.static_folder) / relative_path
            if file_path.exists():
                file_path.unlink()
        flash("Medical record deleted successfully.", "success")
    except Exception as error:
        db.rollback()
        flash(f"Unable to delete medical record: {error}", "danger")
    finally:
        if cursor is not None:
            cursor.close()
    return redirect(url_for("doctor_medical_history"))


# ====================================================================
# Doctor Upload Reports Routes
# ====================================================================
def _doctor_upload_page(cursor, message=None, category=None):
    doctor = _get_logged_in_doctor(cursor)
    if not doctor:
        return None
    cursor.execute("SELECT patient_id, full_name FROM patients WHERE hospital_id=%s ORDER BY full_name, patient_id", (doctor["hospital_id"],))
    patients = cursor.fetchall()
    cursor.execute(
        "SELECT mr.record_id, mr.patient_id, p.full_name AS patient_name, mr.record_type, mr.diagnosis, mr.visit_datetime "
        "FROM medical_records mr INNER JOIN patients p ON p.patient_id=mr.patient_id "
        "WHERE mr.doctor_id=%s AND mr.hospital_id=%s ORDER BY mr.visit_datetime DESC, mr.record_id DESC",
        (doctor["doctor_id"], doctor["hospital_id"]),
    )
    records = cursor.fetchall()
    for record in records:
        record["visit_datetime"] = str(record["visit_datetime"]) if record.get("visit_datetime") else "N/A"
    cursor.execute(
        "SELECT ra.attachment_id, ra.record_id, ra.file_name, ra.file_path, ra.file_type, ra.file_size_kb, ra.uploaded_at, "
        "p.patient_id, p.full_name AS patient_name, mr.record_type, mr.diagnosis "
        "FROM record_attachments ra INNER JOIN medical_records mr ON mr.record_id=ra.record_id "
        "INNER JOIN patients p ON p.patient_id=mr.patient_id "
        "WHERE mr.doctor_id=%s AND mr.hospital_id=%s ORDER BY ra.uploaded_at DESC, ra.attachment_id DESC LIMIT 50",
        (doctor["doctor_id"], doctor["hospital_id"]),
    )
    recent_uploads = cursor.fetchall()
    for upload in recent_uploads:
        upload["uploaded_at"] = str(upload["uploaded_at"]) if upload.get("uploaded_at") else "N/A"
    token = secrets.token_urlsafe(24)
    session["doctor_upload_form_token"] = token
    return render_template("doctor/upload_reports.html", doctor=doctor, patients=patients, records=records, recent_uploads=recent_uploads, upload_form_token=token, message=message, message_category=category)


@app.route("/doctor/upload-reports", methods=["GET", "POST"])
@app.route("/doctor/upload_reports.html", methods=["GET", "POST"])
def doctor_upload_reports():
    if session.get("user_role") != "doctor":
        return redirect(url_for("login"))
    cursor = None
    stored_paths = []
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        if request.method == "GET":
            page = _doctor_upload_page(cursor)
            return page or redirect(url_for("login"))

        submitted_token = request.form.get("upload_form_token", "")
        if not submitted_token or submitted_token != session.pop("doctor_upload_form_token", None):
            return _doctor_upload_page(cursor, "This upload form was already submitted or has expired. Please reload and try again.", "warning")
        doctor = _get_logged_in_doctor(cursor)
        if not doctor:
            return redirect(url_for("login"))
        patient_id = request.form.get("patient_id", "").strip()
        record_id = request.form.get("record_id", "").strip()
        report_type = request.form.get("report_type", "").strip()
        files = [file for file in request.files.getlist("files[]") if file and file.filename]
        allowed_extensions = {"pdf", "jpg", "jpeg", "png", "dcm"}
        if not patient_id or not record_id or not report_type or not files:
            return _doctor_upload_page(cursor, "Patient, medical record, report type, and at least one file are required.", "danger")
        if any("." not in file.filename or file.filename.rsplit(".", 1)[1].lower() not in allowed_extensions for file in files):
            return _doctor_upload_page(cursor, "Only PDF, JPG, PNG, and DICOM files are accepted.", "danger")
        if any(file.stream.seek(0, 2) > 20 * 1024 * 1024 for file in files):
            return _doctor_upload_page(cursor, "Each file must be 20MB or smaller.", "danger")
        for file in files:
            file.stream.seek(0)
        cursor.execute(
            "SELECT mr.record_id FROM medical_records mr INNER JOIN patients p ON p.patient_id=mr.patient_id "
            "WHERE mr.record_id=%s AND mr.patient_id=%s AND mr.doctor_id=%s AND mr.hospital_id=%s AND p.hospital_id=%s",
            (record_id, patient_id, doctor["doctor_id"], doctor["hospital_id"], doctor["hospital_id"]),
        )
        if not cursor.fetchone():
            return _doctor_upload_page(cursor, "The selected medical record is not authorized for this doctor and hospital.", "danger")

        upload_dir = Path(app.static_folder) / "uploads" / "medical_records"
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_names = [secure_filename(file.filename) for file in files]
        if any(not safe_name for safe_name in safe_names):
            return _doctor_upload_page(cursor, "One of the selected filenames is invalid.", "danger")
        for file, safe_name in zip(files, safe_names):
            stored_name = f"{record_id}_{secrets.token_hex(8)}_{safe_name}"
            stored_path = upload_dir / stored_name
            file.save(stored_path)
            stored_paths.append(stored_path)
            cursor.execute(
                "INSERT INTO record_attachments (record_id, file_name, file_path, file_type, file_size_kb) VALUES (%s,%s,%s,%s,%s)",
                (record_id, file.filename, f"uploads/medical_records/{stored_name}", (file.mimetype or "application/octet-stream")[:20], max(1, stored_path.stat().st_size // 1024)),
            )
        db.commit()
        return redirect(url_for("doctor_upload_reports", saved="1", record_id=record_id))
    except Exception as error:
        db.rollback()
        for stored_path in stored_paths:
            if stored_path.exists():
                stored_path.unlink()
        print("DB Error Doctor Upload Reports:", error)
        if cursor is not None:
            page = _doctor_upload_page(cursor, "Unable to save the uploaded report. No data was changed.", "danger")
            return page or redirect(url_for("login"))
        return redirect(url_for("doctor_upload_reports"))
    finally:
        if cursor is not None:
            cursor.close()


@app.route("/doctor/reports/<int:attachment_id>/download")
def doctor_report_download(attachment_id):
    if session.get("user_role") != "doctor":
        return redirect(url_for("login"))
    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        doctor = _get_logged_in_doctor(cursor)
        if not doctor:
            return redirect(url_for("login"))
        cursor.execute(
            "SELECT ra.file_path, ra.file_name FROM record_attachments ra INNER JOIN medical_records mr ON mr.record_id=ra.record_id "
            "WHERE ra.attachment_id=%s AND mr.doctor_id=%s AND mr.hospital_id=%s",
            (attachment_id, doctor["doctor_id"], doctor["hospital_id"]),
        )
        attachment = cursor.fetchone()
        if not attachment:
            abort(404)
        file_path = (Path(app.static_folder) / attachment["file_path"]).resolve()
        if not file_path.is_file() or Path(app.static_folder).resolve() not in file_path.parents:
            abort(404)
        return send_file(file_path, as_attachment=True, download_name=attachment["file_name"])
    finally:
        if cursor is not None:
            cursor.close()


@app.route("/doctor/reports/<int:attachment_id>/delete", methods=["POST"])
def doctor_report_delete(attachment_id):
    if session.get("user_role") != "doctor":
        return redirect(url_for("login"))
    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        doctor = _get_logged_in_doctor(cursor)
        if not doctor:
            return redirect(url_for("login"))
        cursor.execute(
            "SELECT ra.file_path FROM record_attachments ra INNER JOIN medical_records mr ON mr.record_id=ra.record_id "
            "WHERE ra.attachment_id=%s AND mr.doctor_id=%s AND mr.hospital_id=%s",
            (attachment_id, doctor["doctor_id"], doctor["hospital_id"]),
        )
        attachment = cursor.fetchone()
        if not attachment:
            abort(404)
        cursor.execute("DELETE ra FROM record_attachments ra INNER JOIN medical_records mr ON mr.record_id=ra.record_id WHERE ra.attachment_id=%s AND mr.doctor_id=%s AND mr.hospital_id=%s", (attachment_id, doctor["doctor_id"], doctor["hospital_id"]))
        db.commit()
        file_path = (Path(app.static_folder) / attachment["file_path"]).resolve()
        static_root = Path(app.static_folder).resolve()
        if static_root in file_path.parents and file_path.is_file():
            file_path.unlink()
        flash("Report deleted successfully.", "success")
    except Exception as error:
        db.rollback()
        flash(f"Unable to delete report: {error}", "danger")
    finally:
        if cursor is not None:
            cursor.close()
    return redirect(url_for("doctor_upload_reports"))

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))



# Hospital Registration
@app.route("/hospital_registration", methods=["GET", "POST"])
def hospital_registration():

    # Display Registration Page
    if request.method == "GET":
        return render_template("hospital_registration.html")

    # ======================================================
    # HOSPITAL DETAILS
    # ======================================================

    hospital_name = request.form.get("hospital_name")
    registration_number = request.form.get("reg_number")
    city = request.form.get("city")
    address = request.form.get("address")
    phone = request.form.get("phone")
    hospital_email = request.form.get("hospital_email")

    # ======================================================
    # HOSPITAL ADMIN DETAILS
    # ======================================================

    admin_name = request.form.get("admin_name")
    admin_email = request.form.get("admin_email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    # ======================================================
    # PASSWORD VALIDATION
    # ======================================================

    if password != confirm_password:
        flash("Passwords do not match.", "danger")
        return redirect(url_for("hospital_registration"))

    hashed_password = generate_password_hash(password)

    try:

        db.ping(reconnect=True)
        cursor = db.cursor()

        # ======================================================
        # CHECK HOSPITAL EMAIL
        # ======================================================

        cursor.execute(
            "SELECT hospital_id FROM hospitals WHERE hospital_email=%s",
            (hospital_email,)
        )

        if cursor.fetchone():
            flash("Hospital email already registered.", "danger")
            return redirect(url_for("hospital_registration"))

        # ======================================================
        # CHECK REGISTRATION NUMBER
        # ======================================================

        cursor.execute(
            "SELECT hospital_id FROM hospitals WHERE registration_number=%s",
            (registration_number,)
        )

        if cursor.fetchone():
            flash("Registration number already exists.", "danger")
            return redirect(url_for("hospital_registration"))

        # ======================================================
        # INSERT HOSPITAL
        # ======================================================

        hospital_sql = """
        INSERT INTO hospitals
        (
            hospital_name,
            registration_number,
            city,
            address,
            phone,
            hospital_email,
            reg_certificate,
            moh_license,
            admin_ic_doc,
            auth_letter
        )
        VALUES
        (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        )
        """

        import os
        from werkzeug.utils import secure_filename
        
        upload_folder = os.path.join(app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        def save_file(field_name):
            if field_name not in request.files:
                return None
            file = request.files[field_name]
            if file.filename == '':
                return None
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            return f"uploads/{filename}"

        reg_cert_path = save_file("reg_certificate")
        moh_license_path = save_file("moh_license")
        admin_ic_path = save_file("admin_ic_doc")
        auth_letter_path = save_file("auth_letter")

        hospital_values = (
            hospital_name,
            registration_number,
            city,
            address,
            phone,
            hospital_email,
            reg_cert_path,
            moh_license_path,
            admin_ic_path,
            auth_letter_path
        )

        cursor.execute(hospital_sql, hospital_values)
        db.commit()

        # Get Hospital ID
        hospital_id = cursor.lastrowid

        # ======================================================
        # CHECK ADMIN EMAIL
        # ======================================================

        cursor.execute(
            "SELECT user_id FROM users WHERE email=%s",
            (admin_email,)
        )

        if cursor.fetchone():
            flash("Administrator email already exists.", "danger")
            return redirect(url_for("hospital_registration"))

        # ======================================================
        # INSERT HOSPITAL ADMIN
        # ======================================================

        user_sql = """
        INSERT INTO users
        (
            hospital_id,
            full_name,
            email,
            password,
            role
        )
        VALUES
        (
            %s,%s,%s,%s,%s
        )
        """

        user_values = (
            hospital_id,
            admin_name,
            admin_email,
            hashed_password,
            "hospital_admin"
        )

        cursor.execute(user_sql, user_values)
        db.commit()

        # ======================================================
        # SUCCESS
        # ======================================================

        flash("Hospital registered successfully.", "success")
        return redirect(url_for("login"))

    except mysql.connector.Error as err:

        db.rollback()
        flash(f"Database Error: {err}", "danger")
        return redirect(url_for("hospital_registration"))

    finally:

        if 'cursor' in locals():
            cursor.close()

# System Admin Routes
@app.route("/system-admin/dashboard")
@app.route("/system-admin/dashboard.html")
def system_admin_dashboard():
    if session.get("user_role") != "system_admin":
        return redirect(url_for("login"))
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals WHERE status='approved'")
        active_hospitals = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals WHERE status='pending'")
        pending_requests_count = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals WHERE status='suspended'")
        suspended_count = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals WHERE status='rejected'")
        rejected_count = cursor.fetchone()["cnt"]

# ---- Total Records KPI (real DB count, only if medical_records table exists) ----
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = 'medical_records'"
        )
        records_table_exists = cursor.fetchone()["cnt"] > 0
        if records_table_exists:
            cursor.execute("SELECT COUNT(*) as cnt FROM medical_records")
            total_records = cursor.fetchone()["cnt"]
        else:
            total_records = None

        # ---- Patient / Doctor KPIs (real DB counts) ----
        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role='patient'")
        total_patients = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role='doctor'")
        total_doctors = cursor.fetchone()["cnt"]

        # Patients / doctors registered in the last 7 days (for stat change badges)
        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role='patient' AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
        patients_this_week = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role='doctor' AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
        doctors_this_week = cursor.fetchone()["cnt"]

        # ---- Weekly Activity: patients/doctors registered per weekday (Mon-Sun) ----
        weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        # MySQL WEEKDAY: 0=Mon ... 6=Sun
        cursor.execute(
            "SELECT WEEKDAY(created_at) as wd, role, COUNT(*) as cnt "
            "FROM users "
            "WHERE role IN ('patient','doctor') "
            "GROUP BY WEEKDAY(created_at), role"
        )
        weekly_rows = cursor.fetchall()
        new_patients_week = [0] * 7
        new_doctors_week = [0] * 7
        for row in weekly_rows:
            idx = int(row["wd"])
            if row["role"] == "patient":
                new_patients_week[idx] = int(row["cnt"])
            elif row["role"] == "doctor":
                new_doctors_week[idx] = int(row["cnt"])
        weekly_activity = {
            "labels": weekday_labels,
            "patients": new_patients_week,
            "doctors": new_doctors_week,
        }

        cursor.execute("SELECT * FROM hospitals WHERE status='pending' ORDER BY created_at DESC LIMIT 5")
        pending_requests = cursor.fetchall()
        
        cursor.execute("SELECT * FROM hospitals ORDER BY created_at DESC LIMIT 5")
        recent_activities = cursor.fetchall()

        return render_template("system-admin/dashboard.html", 
                               active_hospitals=active_hospitals,
                               pending_requests_count=pending_requests_count,
                               suspended_count=suspended_count,
                               rejected_count=rejected_count,
                               total_patients=total_patients,
                               total_doctors=total_doctors,
                               total_records=total_records,
                               patients_this_week=patients_this_week,
                               doctors_this_week=doctors_this_week,
                               weekly_activity=weekly_activity,
                               pending_requests=pending_requests,
                               recent_activities=recent_activities)
    except Exception as e:
        print("DB Error:", e)
        weekly_activity = {"labels": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], "patients": [0]*7, "doctors": [0]*7}
        return render_template("system-admin/dashboard.html", active_hospitals=0, pending_requests_count=0, suspended_count=0, rejected_count=0, total_patients=0, total_doctors=0, total_records=None, patients_this_week=0, doctors_this_week=0, weekly_activity=weekly_activity, pending_requests=[], recent_activities=[])

@app.route("/system-admin/hospital_requests")
@app.route("/system-admin/hospital_requests.html")
def system_admin_hospital_requests():
    if session.get("user_role") != "system_admin":
        return redirect(url_for("login"))
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM hospitals WHERE status='pending' ORDER BY created_at DESC")
        requests = cursor.fetchall()
        pending_count = len(requests)
        return render_template("system-admin/hospital_requests.html", requests=requests, pending_count=pending_count)
    except Exception as e:
        return render_template("system-admin/hospital_requests.html", requests=[], pending_count=0)

@app.route("/system-admin/analytics")
@app.route("/system-admin/analytics.html")
def system_admin_analytics():
    if session.get("user_role") != "system_admin":
        return redirect(url_for("login"))

    # ---- Date-range filter (All Time / 12m / 6m / 30d) ----
    period = request.args.get("period", "all")
    if period not in ("all", "12m", "6m", "30d"):
        period = "all"

# Build a SQL date filter based on the selected period
    date_filter = ""
    if period == "12m":
        date_filter = "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)"
    elif period == "6m":
        date_filter = "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)"
    elif period == "30d":
        date_filter = "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)"

    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)

        # ---- KPI Stats (always full-history counts) ----
        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals")
        total_hospitals = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals WHERE status='approved'")
        approved_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals WHERE status='pending'")
        pending_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals WHERE status='rejected'")
        rejected_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals WHERE status='suspended'")
        suspended_count = cursor.fetchone()["cnt"]

        # Doctors / Admins / Patients / System Admins from users table
        cursor.execute("SELECT role, COUNT(*) as cnt FROM users GROUP BY role")
        role_counts = {row["role"]: row["cnt"] for row in cursor.fetchall()}
        doctor_count = role_counts.get("doctor", 0)
        hospital_admin_count = role_counts.get("hospital_admin", 0)
        patient_count = role_counts.get("patient", 0)
        system_admin_count = role_counts.get("system_admin", 0)

        # ---- Registrations over time (monthly) ----
        # If a period is selected, restrict to registrations within that window.
        if period == "all":
            cursor.execute(
                """
                SELECT DATE_FORMAT(created_at, %s) as month,
                       COUNT(*) as cnt
                FROM hospitals
                GROUP BY DATE_FORMAT(created_at, %s)
                ORDER BY MIN(created_at) ASC
                """,
                ("%b %Y", "%b %Y"),
            )
        else:
            cursor.execute(
                """
                SELECT DATE_FORMAT(created_at, %s) as month,
                       COUNT(*) as cnt
                FROM hospitals
                {date_filter}
                GROUP BY DATE_FORMAT(created_at, %s)
                ORDER BY MIN(created_at) ASC
                """.format(date_filter=date_filter),
                ("%b %Y", "%b %Y"),
            )
        registrations_by_month = cursor.fetchall()
        reg_months = [r["month"] for r in registrations_by_month]
        reg_counts = [r["cnt"] for r in registrations_by_month]

        # ---- Status distribution ----
        status_distribution = [
            {"label": "Approved", "value": approved_count, "color": "#00c853"},
            {"label": "Pending", "value": pending_count, "color": "#ffab00"},
            {"label": "Rejected", "value": rejected_count, "color": "#f44336"},
            {"label": "Suspended", "value": suspended_count, "color": "#90a4ae"},
        ]

        # ---- City distribution ----
        cursor.execute(
            """
            SELECT city, COUNT(*) as cnt
            FROM hospitals
            {date_filter}
            GROUP BY city
            ORDER BY cnt DESC
            LIMIT 10
            """.format(date_filter=date_filter)
        )
        city_rows = cursor.fetchall()
        cities = [r["city"] for r in city_rows]
        city_counts = [r["cnt"] for r in city_rows]

        # ---- Recent hospitals ----
        cursor.execute(
            "SELECT hospital_id, hospital_name, registration_number, city, phone, hospital_email, status, created_at "
            "FROM hospitals {date_filter} ORDER BY created_at DESC LIMIT 10".format(date_filter=date_filter)
        )
        recent_hospitals = cursor.fetchall()

        return render_template(
            "system-admin/analytics.html",
            total_hospitals=total_hospitals,
            approved_count=approved_count,
            pending_count=pending_count,
            pending_requests_count=pending_count,
            rejected_count=rejected_count,
            suspended_count=suspended_count,
            doctor_count=doctor_count,
            hospital_admin_count=hospital_admin_count,
            patient_count=patient_count,
            system_admin_count=system_admin_count,
            reg_months=reg_months,
            reg_counts=reg_counts,
            status_distribution=status_distribution,
            cities=cities,
            city_counts=city_counts,
            recent_hospitals=recent_hospitals,
            selected_period=period,
            period=period,
        )
    except Exception as e:
        print("DB Error in analytics:", e)
        return render_template(
            "system-admin/analytics.html",
            total_hospitals=0,
            approved_count=0,
            pending_count=0,
            rejected_count=0,
            suspended_count=0,
            doctor_count=0,
            hospital_admin_count=0,
            patient_count=0,
            system_admin_count=0,
            reg_months=[],
            reg_counts=[],
            status_distribution=[],
            cities=[],
            city_counts=[],
            recent_hospitals=[],
            selected_period=period,
            period=period,
        )


@app.route("/system-admin/hospitals")
@app.route("/system-admin/hospitals.html")
def system_admin_hospitals():
    if session.get("user_role") != "system_admin":
        return redirect(url_for("login"))
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM hospitals ORDER BY created_at DESC")
        hospitals = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals WHERE status='approved'")
        active_count = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals WHERE status='pending'")
        pending_count = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals WHERE status='suspended'")
        suspended_count = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals WHERE status='rejected'")
        rejected_count = cursor.fetchone()["cnt"]

        # Count doctors per hospital
        cursor.execute("SELECT hospital_id, COUNT(*) as cnt FROM users WHERE role='doctor' GROUP BY hospital_id")
        doctor_counts = {row["hospital_id"]: row["cnt"] for row in cursor.fetchall()}
        for h in hospitals:
            h["doctor_count"] = doctor_counts.get(h["hospital_id"], 0)
            if h.get("created_at"):
                h["created_at_str"] = h["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                h["joined_display"] = h["created_at"].strftime("%b %Y")
            else:
                h["created_at_str"] = ""
                h["joined_display"] = ""
            # Convert to string so the embedded JSON cache serializes cleanly
            h["created_at"] = h["created_at_str"]

        return render_template("system-admin/hospitals.html",
                               hospitals=hospitals,
                               active_count=active_count,
                               pending_count=pending_count,
                               suspended_count=suspended_count,
                               rejected_count=rejected_count)
    except Exception as e:
        return render_template("system-admin/hospitals.html", hospitals=[], active_count=0, pending_count=0, suspended_count=0, rejected_count=0)

@app.route("/system-admin/approve_hospital/<int:hospital_id>", methods=["POST"])
def approve_hospital(hospital_id):
    if session.get("user_role") != "system_admin":
        return abort(403)
    try:
        db.ping(reconnect=True)
        cursor = db.cursor()
        cursor.execute("UPDATE hospitals SET status='approved' WHERE hospital_id=%s", (hospital_id,))
        db.commit()
        flash("Hospital approved successfully.", "success")
    except Exception as e:
        db.rollback()
        flash("Error approving hospital.", "danger")
    return redirect(url_for("system_admin_hospital_requests"))

@app.route("/system-admin/reject_hospital/<int:hospital_id>", methods=["POST"])
def reject_hospital(hospital_id):
    if session.get("user_role") != "system_admin":
        return abort(403)
    try:
        db.ping(reconnect=True)
        cursor = db.cursor()
        cursor.execute("UPDATE hospitals SET status='rejected' WHERE hospital_id=%s", (hospital_id,))
        db.commit()
        flash("Hospital rejected.", "info")
    except Exception as e:
        db.rollback()
        flash("Error rejecting hospital.", "danger")
    return redirect(url_for("system_admin_hospital_requests"))


@app.route("/system-admin/settings")
@app.route("/system-admin/settings.html")
def system_admin_settings():
    if session.get("user_role") != "system_admin":
        return redirect(url_for("login"))
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as cnt FROM hospitals WHERE status='pending'")
        pending_requests_count = cursor.fetchone()["cnt"]
        return render_template("system-admin/settings.html", pending_requests_count=pending_requests_count)
    except Exception as e:
        return render_template("system-admin/settings.html", pending_requests_count=0)

from flask import jsonify

# ---- JSON API for Manage Hospitals ----

@app.route("/system-admin/api/hospitals", methods=["GET"])
def system_admin_hospitals_api():
    if session.get("user_role") != "system_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM hospitals ORDER BY created_at DESC")
        hospitals = cursor.fetchall()

        cursor.execute("SELECT hospital_id, COUNT(*) as cnt FROM users WHERE role='doctor' GROUP BY hospital_id")
        doctor_counts = {row["hospital_id"]: row["cnt"] for row in cursor.fetchall()}

        data = []
        for h in hospitals:
            h["doctor_count"] = doctor_counts.get(h["hospital_id"], 0)
            h["created_at_str"] = h["created_at"].strftime("%Y-%m-%d %H:%M:%S") if h["created_at"] else ""
            h["joined_display"] = h["created_at"].strftime("%b %Y") if h["created_at"] else ""
            data.append(h)

        return jsonify({"success": True, "hospitals": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/system-admin/hospitals/update", methods=["POST"])
def system_admin_hospital_update():
    if session.get("user_role") != "system_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        data = request.get_json(silent=True) or request.form
        hospital_id = data.get("hospital_id")
        if not hospital_id:
            return jsonify({"success": False, "error": "Missing hospital id"}), 400

        hospital_name = (data.get("hospital_name") or "").strip()
        registration_number = (data.get("registration_number") or "").strip()
        city = (data.get("city") or "").strip()
        address = (data.get("address") or "").strip()
        phone = (data.get("phone") or "").strip()
        hospital_email = (data.get("hospital_email") or "").strip()
        status = (data.get("status") or "").strip()

        if not hospital_name or not registration_number or not city or not hospital_email:
            return jsonify({"success": False, "error": "Required fields cannot be empty"}), 400

        allowed_statuses = {"pending", "approved", "rejected", "suspended"}
        if status and status not in allowed_statuses:
            return jsonify({"success": False, "error": "Invalid status value"}), 400

        db.ping(reconnect=True)
        cursor = db.cursor()

        cursor.execute(
            "SELECT hospital_id FROM hospitals WHERE hospital_email=%s AND hospital_id!=%s",
            (hospital_email, hospital_id)
        )
        if cursor.fetchone():
            return jsonify({"success": False, "error": "Hospital email already registered"}), 400

        cursor.execute(
            "SELECT hospital_id FROM hospitals WHERE registration_number=%s AND hospital_id!=%s",
            (registration_number, hospital_id)
        )
        if cursor.fetchone():
            return jsonify({"success": False, "error": "Registration number already exists"}), 400

        cursor.execute(
            """UPDATE hospitals
               SET hospital_name=%s, registration_number=%s, city=%s,
                   address=%s, phone=%s, hospital_email=%s
                   {status_set}
               WHERE hospital_id=%s""".format(
                status_set=", status=%s" if status else ""
            ),
            (
                hospital_name, registration_number, city, address, phone, hospital_email,
                *([status] if status else []),
                hospital_id
            )
        )
        db.commit()
        return jsonify({"success": True, "message": "Hospital updated successfully."})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/system-admin/hospitals/<int:hospital_id>/status", methods=["POST"])
def system_admin_hospital_status(hospital_id):
    if session.get("user_role") != "system_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        data = request.get_json(silent=True) or request.form
        status = (data.get("status") or "").strip()
        allowed_statuses = {"pending", "approved", "rejected", "suspended"}
        if status not in allowed_statuses:
            return jsonify({"success": False, "error": "Invalid status"}), 400

        db.ping(reconnect=True)
        cursor = db.cursor()
        cursor.execute("UPDATE hospitals SET status=%s WHERE hospital_id=%s", (status, hospital_id))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"success": False, "error": "Hospital not found"}), 404

        return jsonify({"success": True, "message": f"Hospital status set to {status}.", "status": status})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/system-admin/hospitals/<int:hospital_id>/delete", methods=["POST"])
def system_admin_hospital_delete(hospital_id):
    if session.get("user_role") != "system_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        db.ping(reconnect=True)
        cursor = db.cursor()

        # Remove linked users first to satisfy FK constraint
        cursor.execute("DELETE FROM users WHERE hospital_id=%s", (hospital_id,))
        cursor.execute("DELETE FROM hospitals WHERE hospital_id=%s", (hospital_id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"success": False, "error": "Hospital not found"}), 404

        return jsonify({"success": True, "message": "Hospital deleted successfully."})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# ====================================================================
# Hospital Admin Dashboard Route
# ====================================================================
@app.route("/hospital-admin/dashboard")
@app.route("/hospital-admin/dashboard.html")
def hospital_admin_dashboard():
    if session.get("user_role") != "hospital_admin":
        return redirect(url_for("login"))
    
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        user_id = session.get("user_id")
        
        # Get hospital_id for this admin
        cursor.execute("SELECT hospital_id FROM users WHERE user_id=%s", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            return redirect(url_for("login"))
        hospital_id = user_row["hospital_id"]
        
        # Get hospital information
        cursor.execute("SELECT hospital_name, city, address, phone FROM hospitals WHERE hospital_id=%s", (hospital_id,))
        hospital_row = cursor.fetchone()
        hospital_name = hospital_row["hospital_name"] if hospital_row else "Hospital"
        
        # ---- KPI: Active Doctors (from doctors table) ----
        cursor.execute("SELECT COUNT(*) as cnt FROM doctors WHERE hospital_id=%s AND status='active'", (hospital_id,))
        active_doctors = cursor.fetchone()["cnt"]
        
        # ---- KPI: Total Patients (from patients table) ----
        cursor.execute("SELECT COUNT(*) as cnt FROM patients WHERE hospital_id=%s", (hospital_id,))
        total_patients = cursor.fetchone()["cnt"]
        
        # ---- KPI: Medical Records (check if table exists) ----
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = 'medical_records'"
        )
        records_table_exists = cursor.fetchone()["cnt"] > 0
        total_records = "N/A"
        latest_records = []
        if records_table_exists:
            try:
                cursor.execute("SELECT COUNT(*) as cnt FROM medical_records WHERE hospital_id=%s", (hospital_id,))
                total_records = cursor.fetchone()["cnt"]
                # Get latest 4 records
                cursor.execute(
                    "SELECT medical_record_id, title, patient_id, created_at FROM medical_records "
                    "WHERE hospital_id=%s ORDER BY created_at DESC LIMIT 4",
                    (hospital_id,)
                )
                latest_records = cursor.fetchall()
            except:
                total_records = "N/A"
                latest_records = []
        
        # ---- KPI: Appointments & Blockchain Txs (N/A - tables don't exist) ----
        total_appointments = "N/A"
        blockchain_txs = "N/A"
        
        # ---- Recent Doctors (up to 4) ----
        cursor.execute(
            "SELECT doctor_id, full_name, specialization, status, created_at FROM doctors "
            "WHERE hospital_id=%s ORDER BY created_at DESC LIMIT 4",
            (hospital_id,)
        )
        recent_doctors = cursor.fetchall()
        
        # ---- Chart Data: Patient Registrations by Month This Year ----
        cursor.execute(
            "SELECT MONTH(created_at) as m, COUNT(*) as cnt FROM patients "
            "WHERE hospital_id=%s AND YEAR(created_at) = YEAR(CURRENT_DATE()) "
            "GROUP BY MONTH(created_at) ORDER BY m",
            (hospital_id,)
        )
        patient_chart_rows = cursor.fetchall()
        patient_chart_dict = {row["m"]: row["cnt"] for row in patient_chart_rows}
        patient_chart_data = [patient_chart_dict.get(m, 0) for m in range(1, 13)]
        
        # ---- Chart Data: Records by Type (if medical_records table exists) ----
        records_by_type_data = [0, 0, 0, 0]  # Default empty
        if records_table_exists:
            try:
                cursor.execute(
                    "SELECT record_type, COUNT(*) as cnt FROM medical_records "
                    "WHERE hospital_id=%s GROUP BY record_type",
                    (hospital_id,)
                )
                type_rows = cursor.fetchall()
                type_map = {
                    "Consultation": 0,
                    "Lab Result": 1,
                    "Radiology": 2,
                    "Prescription": 3
                }
                for row in type_rows:
                    rtype = row.get("record_type", "")
                    if rtype in type_map:
                        records_by_type_data[type_map[rtype]] = row["cnt"]
            except:
                pass
        
        # ---- Prepare stats dictionary ----
        stats = {
            "hospital_name": hospital_name,
            "active_doctors": active_doctors,
            "total_patients": total_patients,
            "total_records": total_records,
            "total_appointments": total_appointments,
            "blockchain_txs": blockchain_txs
        }
        
        return render_template(
            "hospital-admin/dashboard.html",
            stats=stats,
            recent_doctors=recent_doctors,
            latest_records=latest_records,
            patient_chart_data=patient_chart_data,
            records_by_type_data=records_by_type_data
        )
    except Exception as e:
        print("DB Error HA Dashboard:", e)
        # Return with N/A values if error
        return render_template(
            "hospital-admin/dashboard.html",
            stats={
                "hospital_name": "Error",
                "active_doctors": "N/A",
                "total_patients": "N/A",
                "total_records": "N/A",
                "total_appointments": "N/A",
                "blockchain_txs": "N/A"
            },
            recent_doctors=[],
            latest_records=[],
            patient_chart_data=[0]*12,
            records_by_type_data=[0, 0, 0, 0]
        )

# ====================================================================
# Hospital Admin Settings Routes
# ====================================================================
@app.route("/hospital-admin/settings", methods=["GET", "POST"])
@app.route("/hospital-admin/settings.html", methods=["GET", "POST"])
def hospital_admin_settings():
    if session.get("user_role") != "hospital_admin":
        return redirect(url_for("login"))

    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        user_id = session.get("user_id")

        def load_settings():
            cursor.execute(
                "SELECT u.user_id, u.hospital_id, u.full_name, u.email, u.password, "
                "u.phone AS admin_phone, u.designation, h.hospital_name, "
                "h.registration_number, h.city, h.address, h.phone AS hospital_phone, "
                "h.hospital_email, h.status FROM users u "
                "JOIN hospitals h ON h.hospital_id=u.hospital_id "
                "WHERE u.user_id=%s AND u.role='hospital_admin'",
                (user_id,)
            )
            return cursor.fetchone()

        settings = load_settings()
        if not settings:
            session.clear()
            return redirect(url_for("login"))

        if request.method == "POST":
            action = request.form.get("action", "profile")
            if action == "password":
                current_password = request.form.get("current_password", "")
                new_password = request.form.get("new_password", "")
                confirm_password = request.form.get("confirm_password", "")
                stored_password = settings["password"]
                password_valid = (
                    check_password_hash(stored_password, current_password)
                    if stored_password.startswith(("scrypt:", "pbkdf2:", "argon2:"))
                    else stored_password == current_password
                )
                if not password_valid:
                    flash("Current password is incorrect.", "danger")
                elif len(new_password) < 8:
                    flash("New password must be at least 8 characters.", "danger")
                elif new_password != confirm_password:
                    flash("New passwords do not match.", "danger")
                else:
                    cursor.execute(
                        "UPDATE users SET password=%s WHERE user_id=%s AND role='hospital_admin'",
                        (generate_password_hash(new_password), user_id)
                    )
                    db.commit()
                    flash("Password updated successfully.", "success")
            else:
                values = {field: request.form.get(field, "").strip() for field in (
                    "hospital_name", "hospital_email", "hospital_phone", "address",
                    "full_name", "admin_email", "admin_phone", "designation"
                )}
                if any(not value for value in values.values()):
                    flash("All profile fields are required.", "danger")
                elif any("@" not in values[field] for field in ("hospital_email", "admin_email")):
                    flash("Enter valid email addresses.", "danger")
                elif any(len(values[field]) < 7 for field in ("hospital_phone", "admin_phone")):
                    flash("Enter valid phone numbers.", "danger")
                else:
                    cursor.execute(
                        "SELECT user_id FROM users WHERE email=%s AND user_id!=%s",
                        (values["admin_email"], user_id)
                    )
                    email_in_use = cursor.fetchone()
                    cursor.execute(
                        "SELECT hospital_id FROM hospitals WHERE hospital_email=%s AND hospital_id!=%s",
                        (values["hospital_email"], settings["hospital_id"])
                    )
                    hospital_email_in_use = cursor.fetchone()
                    if email_in_use:
                        flash("Administrator email is already in use.", "danger")
                    elif hospital_email_in_use:
                        flash("Hospital email is already in use.", "danger")
                    else:
                        cursor.execute(
                            "UPDATE hospitals SET hospital_name=%s, hospital_email=%s, phone=%s, address=%s WHERE hospital_id=%s",
                            (values["hospital_name"], values["hospital_email"], values["hospital_phone"], values["address"], settings["hospital_id"])
                        )
                        cursor.execute(
                            "UPDATE users SET full_name=%s, email=%s, phone=%s, designation=%s WHERE user_id=%s AND role='hospital_admin'",
                            (values["full_name"], values["admin_email"], values["admin_phone"], values["designation"], user_id)
                        )
                        db.commit()
                        session["user_name"] = values["full_name"]
                        flash("Settings updated successfully.", "success")
            return redirect(url_for("hospital_admin_settings"))

        return render_template("hospital-admin/settings.html", settings=settings)
    except mysql.connector.Error as err:
        db.rollback()
        flash(f"Database error: {err}", "danger")
        return redirect(url_for("hospital_admin_settings"))
    finally:
        if cursor is not None:
            cursor.close()

# ====================================================================
# Hospital Admin Doctors Routes
# ====================================================================
@app.route("/hospital-admin/doctors")
@app.route("/hospital-admin/doctors.html")
def hospital_admin_doctors():
    if session.get("user_role") != "hospital_admin":
        return redirect(url_for("login"))
    
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        user_id = session.get("user_id")
        
        # Get hospital_id for this admin
        cursor.execute("SELECT hospital_id FROM users WHERE user_id=%s", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            return redirect(url_for("login"))
        hospital_id = user_row["hospital_id"]
        
        # Get stats by status
        cursor.execute("SELECT status, COUNT(*) as cnt FROM doctors WHERE hospital_id=%s GROUP BY status", (hospital_id,))
        status_counts = {r['status']: r['cnt'] for r in cursor.fetchall()}
        active_doctors = status_counts.get('active', 0)
        inactive_doctors = status_counts.get('inactive', 0)
        
        # Count distinct specializations
        cursor.execute("SELECT COUNT(DISTINCT specialization) as cnt FROM doctors WHERE hospital_id=%s AND specialization IS NOT NULL AND specialization != ''", (hospital_id,))
        spec_row = cursor.fetchone()
        specializations_count = spec_row['cnt'] if spec_row else 0
        
        stats = {
            "active": active_doctors,
            "inactive": inactive_doctors,
            "specializations": specializations_count
        }
        
        # Get all doctors for this hospital
        cursor.execute("SELECT * FROM doctors WHERE hospital_id=%s ORDER BY created_at DESC", (hospital_id,))
        doctors = cursor.fetchall()
        for d in doctors:
            if d.get("created_at"):
                d["joined_display"] = d["created_at"].strftime("%b %Y")
            else:
                d["joined_display"] = ""
        
        return render_template("hospital-admin/doctors.html", doctors=doctors, stats=stats)
    except Exception as e:
        print("DB Error Doctors Page:", e)
        return render_template("hospital-admin/doctors.html", doctors=[], stats={"active":0,"inactive":0,"specializations":0})

@app.route("/hospital-admin/doctors/add", methods=["POST"])
def hospital_admin_doctors_add():
    if session.get("user_role") != "hospital_admin":
        return redirect(url_for("login"))
    try:
        db.ping(reconnect=True)
        cursor = db.cursor()
        user_id = session.get("user_id")
        
        cursor.execute("SELECT hospital_id FROM users WHERE user_id=%s", (user_id,))
        hospital_id = cursor.fetchone()["hospital_id"]
        
        full_name = request.form.get("full_name", "").strip()
        license_number = request.form.get("license_number", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        specialization = request.form.get("specialization", "").strip()
        department = request.form.get("department", "").strip()
        password = request.form.get("password", "").strip()
        
        if not full_name or not email or not password:
            flash("Full Name, Email, and Password are required.", "danger")
            return redirect(url_for("hospital_admin_doctors"))
        
        # Insert into doctors table
        cursor.execute(
            "INSERT INTO doctors (hospital_id, full_name, email, phone, password, specialization, license_number, department, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active')",
            (hospital_id, full_name, email, phone, password, specialization, license_number, department)
        )
        
        # Also insert into users table so they can login
        cursor.execute(
            "INSERT INTO users (hospital_id, full_name, email, password, role) VALUES (%s, %s, %s, %s, 'doctor')",
            (hospital_id, full_name, email, password)
        )
        
        db.commit()
        flash("Doctor added successfully.", "success")
    except mysql.connector.Error as err:
        db.rollback()
        flash(f"Error adding doctor: {err}", "danger")
    except Exception as e:
        db.rollback()
        flash(f"Error: {e}", "danger")
    finally:
        if 'cursor' in locals():
            cursor.close()
    return redirect(url_for("hospital_admin_doctors"))

@app.route("/hospital-admin/doctors/<int:doctor_id>/edit", methods=["POST"])
def hospital_admin_doctors_edit(doctor_id):
    if session.get("user_role") != "hospital_admin":
        return redirect(url_for("login"))
    try:
        db.ping(reconnect=True)
        cursor = db.cursor()
        
        full_name = request.form.get("full_name", "").strip()
        license_number = request.form.get("license_number", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        specialization = request.form.get("specialization", "").strip()
        department = request.form.get("department", "").strip()
        
        cursor.execute(
            "UPDATE doctors SET full_name=%s, email=%s, phone=%s, specialization=%s, license_number=%s, department=%s WHERE doctor_id=%s",
            (full_name, email, phone, specialization, license_number, department, doctor_id)
        )
        db.commit()
        flash("Doctor updated successfully.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error updating doctor: {e}", "danger")
    finally:
        if 'cursor' in locals():
            cursor.close()
    return redirect(url_for("hospital_admin_doctors"))

@app.route("/hospital-admin/doctors/<int:doctor_id>/status", methods=["POST"])
def hospital_admin_doctors_status(doctor_id):
    if session.get("user_role") != "hospital_admin":
        return redirect(url_for("login"))
    try:
        db.ping(reconnect=True)
        cursor = db.cursor()
        status = request.form.get("status", "").strip()
        cursor.execute("UPDATE doctors SET status=%s WHERE doctor_id=%s", (status, doctor_id))
        db.commit()
        flash("Doctor status updated.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error updating status: {e}", "danger")
    finally:
        if 'cursor' in locals():
            cursor.close()
    return redirect(url_for("hospital_admin_doctors"))

@app.route("/hospital-admin/doctors/<int:doctor_id>/delete", methods=["POST"])
def hospital_admin_doctors_delete(doctor_id):
    if session.get("user_role") != "hospital_admin":
        return redirect(url_for("login"))
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        # Get doctor email before deleting
        cursor.execute("SELECT email FROM doctors WHERE doctor_id=%s", (doctor_id,))
        doc = cursor.fetchone()
        if doc:
            # Delete from users table
            cursor.execute("DELETE FROM users WHERE email=%s AND role='doctor'", (doc['email'],))
            # Delete from doctors table
            cursor.execute("DELETE FROM doctors WHERE doctor_id=%s", (doctor_id,))
            db.commit()
            flash("Doctor deleted successfully.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error deleting doctor: {e}", "danger")
    finally:
        if 'cursor' in locals():
            cursor.close()
    return redirect(url_for("hospital_admin_doctors"))

# ====================================================================
# Hospital Admin Patients Routes
# ====================================================================
@app.route("/hospital-admin/patients")
@app.route("/hospital-admin/patients.html")
def hospital_admin_patients():
    if session.get("user_role") != "hospital_admin":
        return redirect(url_for("login"))
    
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        user_id = session.get("user_id")
        
        # Get hospital_id and admin_name for this admin
        cursor.execute("SELECT hospital_id, full_name FROM users WHERE user_id=%s", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            return redirect(url_for("login"))
        hospital_id = user_row.get("hospital_id") or 1
        admin_name = user_row.get("full_name") or "Hospital Admin"
        
        # Get hospital information
        cursor.execute("SELECT hospital_name FROM hospitals WHERE hospital_id=%s", (hospital_id,))
        hospital_row = cursor.fetchone()
        hospital_name = hospital_row["hospital_name"] if hospital_row else "Hospital"
        
        # Stats counts
        cursor.execute("SELECT COUNT(*) as cnt FROM patients WHERE hospital_id=%s", (hospital_id,))
        total_patients = cursor.fetchone()["cnt"]
        
        cursor.execute("SELECT COUNT(*) as cnt FROM patients WHERE hospital_id=%s AND status='active'", (hospital_id,))
        active_patients = cursor.fetchone()["cnt"]
        
        cursor.execute("SELECT COUNT(*) as cnt FROM patients WHERE hospital_id=%s AND status='inactive'", (hospital_id,))
        inactive_patients = cursor.fetchone()["cnt"]
        
        cursor.execute("SELECT COUNT(*) as cnt FROM patients WHERE hospital_id=%s AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)", (hospital_id,))
        new_this_week = cursor.fetchone()["cnt"]
        
        stats = {
            "hospital_name": hospital_name,
            "total": total_patients,
            "active": active_patients,
            "inactive": inactive_patients,
            "new_this_week": new_this_week
        }
        
        # Fetch active doctors for hospital for assignment
        cursor.execute("SELECT doctor_id, full_name, specialization FROM doctors WHERE hospital_id=%s AND status='active' ORDER BY full_name ASC", (hospital_id,))
        doctors = cursor.fetchall()
        
        # Check if medical_records table exists
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = 'medical_records'"
        )
        records_table_exists = cursor.fetchone()["cnt"] > 0
        
        # Fetch all patients for this hospital
        cursor.execute("SELECT * FROM patients WHERE hospital_id=%s ORDER BY created_at DESC", (hospital_id,))
        patients = cursor.fetchall()
        import datetime
        today = datetime.date.today()
        for p in patients:
            # Format ID
            p["formatted_id"] = f"PAT-{p['patient_id']:04d}"
            
            # Calculate Age & format DOB
            if p.get("date_of_birth"):
                dob = p["date_of_birth"]
                p["age"] = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                p["dob_str"] = dob.strftime("%Y-%m-%d")
            else:
                p["age"] = "N/A"
                p["dob_str"] = "N/A"
                
            # Format created_at
            if p.get("created_at"):
                p["created_at_str"] = p["created_at"].strftime("%b %d, %Y")
            else:
                p["created_at_str"] = "N/A"
                
            # Medical records count
            p["records_count"] = 0
            if records_table_exists:
                try:
                    cursor.execute("SELECT COUNT(*) as cnt FROM medical_records WHERE patient_id=%s", (p["patient_id"],))
                    p["records_count"] = cursor.fetchone()["cnt"]
                except:
                    p["records_count"] = 0
        
        return render_template(
            "hospital-admin/patients.html",
            patients=patients,
            stats=stats,
            doctors=doctors,
            hospital_name=hospital_name,
            admin_name=admin_name
        )
    except Exception as e:
        print("DB Error Patients Page:", e)
        return render_template(
            "hospital-admin/patients.html",
            patients=[],
            stats={"hospital_name": "Hospital", "total": 0, "active": 0, "inactive": 0, "new_this_week": 0},
            doctors=[],
            hospital_name="Hospital",
            admin_name="Hospital Admin"
        )
    finally:
        if 'cursor' in locals():
            cursor.close()


@app.route("/hospital-admin/patients/register", methods=["POST"])
def hospital_admin_patients_register():
    if session.get("user_role") != "hospital_admin":
        return redirect(url_for("login"))
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        user_id = session.get("user_id")
        
        cursor.execute("SELECT hospital_id FROM users WHERE user_id=%s", (user_id,))
        user_row = cursor.fetchone()
        hospital_id = user_row.get("hospital_id") or 1 if user_row else 1
        
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip() or "123456"
        date_of_birth = request.form.get("date_of_birth", "").strip() or None
        gender = request.form.get("gender", "").strip() or "Other"
        blood_group = request.form.get("blood_group", "").strip() or "O+"
        address = request.form.get("address", "").strip()
        emergency_contact = request.form.get("emergency_contact", "").strip()
        emergency_phone = request.form.get("emergency_phone", "").strip()
        
        if not full_name or not email:
            flash("Full Name and Email are required.", "danger")
            return redirect(url_for("hospital_admin_patients"))
            
        # Check duplicate email in patients
        cursor.execute("SELECT patient_id FROM patients WHERE email=%s", (email,))
        if cursor.fetchone():
            flash("Patient with this email already exists.", "danger")
            return redirect(url_for("hospital_admin_patients"))
            
        # Insert into patients table
        cursor.execute(
            """INSERT INTO patients 
               (hospital_id, full_name, email, phone, password, date_of_birth, gender, blood_group, address, emergency_contact, emergency_phone, status) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')""",
            (hospital_id, full_name, email, phone, password, date_of_birth, gender, blood_group, address, emergency_contact, emergency_phone)
        )
        
        # Check if email exists in users table
        cursor.execute("SELECT user_id FROM users WHERE email=%s", (email,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (hospital_id, full_name, email, password, role) VALUES (%s, %s, %s, %s, 'patient')",
                (hospital_id, full_name, email, password)
            )
            
        db.commit()
        flash("Patient registered successfully.", "success")
    except mysql.connector.Error as err:
        db.rollback()
        flash(f"Database Error: {err}", "danger")
    except Exception as e:
        db.rollback()
        flash(f"Error registering patient: {e}", "danger")
    finally:
        if 'cursor' in locals():
            cursor.close()
    return redirect(url_for("hospital_admin_patients"))


@app.route("/hospital-admin/patients/<int:patient_id>/edit", methods=["POST"])
def hospital_admin_patients_edit(patient_id):
    if session.get("user_role") != "hospital_admin":
        return redirect(url_for("login"))
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        user_id = session.get("user_id")
        
        cursor.execute("SELECT hospital_id FROM users WHERE user_id=%s", (user_id,))
        user_row = cursor.fetchone()
        hospital_id = user_row.get("hospital_id") or 1 if user_row else 1
        
        # Fetch current patient to get old email for updating users table
        cursor.execute("SELECT email FROM patients WHERE patient_id=%s AND hospital_id=%s", (patient_id, hospital_id))
        old_patient = cursor.fetchone()
        if not old_patient:
            flash("Patient not found or unauthorized.", "danger")
            return redirect(url_for("hospital_admin_patients"))
            
        old_email = old_patient["email"]
        
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        date_of_birth = request.form.get("date_of_birth", "").strip() or None
        gender = request.form.get("gender", "").strip()
        blood_group = request.form.get("blood_group", "").strip()
        address = request.form.get("address", "").strip()
        emergency_contact = request.form.get("emergency_contact", "").strip()
        emergency_phone = request.form.get("emergency_phone", "").strip()
        status = request.form.get("status", "active").strip()
        
        if not full_name or not email:
            flash("Full Name and Email are required.", "danger")
            return redirect(url_for("hospital_admin_patients"))
            
        cursor.execute(
            """UPDATE patients 
               SET full_name=%s, email=%s, phone=%s, date_of_birth=%s, gender=%s, blood_group=%s, 
                   address=%s, emergency_contact=%s, emergency_phone=%s, status=%s 
               WHERE patient_id=%s AND hospital_id=%s""",
            (full_name, email, phone, date_of_birth, gender, blood_group, address, emergency_contact, emergency_phone, status, patient_id, hospital_id)
        )
        
        # Also update users table if user exists
        cursor.execute(
            "UPDATE users SET full_name=%s, email=%s WHERE email=%s AND role='patient'",
            (full_name, email, old_email)
        )
        
        db.commit()
        flash("Patient details updated successfully.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error updating patient: {e}", "danger")
    finally:
        if 'cursor' in locals():
            cursor.close()
    return redirect(url_for("hospital_admin_patients"))


@app.route("/hospital-admin/patients/<int:patient_id>/status", methods=["POST"])
def hospital_admin_patients_status(patient_id):
    if session.get("user_role") != "hospital_admin":
        return redirect(url_for("login"))
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        user_id = session.get("user_id")
        
        cursor.execute("SELECT hospital_id FROM users WHERE user_id=%s", (user_id,))
        user_row = cursor.fetchone()
        hospital_id = user_row.get("hospital_id") or 1 if user_row else 1
        
        status = request.form.get("status", "active").strip()
        cursor.execute(
            "UPDATE patients SET status=%s WHERE patient_id=%s AND hospital_id=%s",
            (status, patient_id, hospital_id)
        )
        db.commit()
        flash(f"Patient status updated to {status.capitalize()}.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error updating patient status: {e}", "danger")
    finally:
        if 'cursor' in locals():
            cursor.close()
    return redirect(url_for("hospital_admin_patients"))


@app.route("/hospital-admin/patients/<int:patient_id>/delete", methods=["POST"])
def hospital_admin_patients_delete(patient_id):
    if session.get("user_role") != "hospital_admin":
        return redirect(url_for("login"))
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        user_id = session.get("user_id")
        
        cursor.execute("SELECT hospital_id FROM users WHERE user_id=%s", (user_id,))
        user_row = cursor.fetchone()
        hospital_id = user_row.get("hospital_id") or 1 if user_row else 1
        
        # Get patient email before deletion
        cursor.execute("SELECT email FROM patients WHERE patient_id=%s AND hospital_id=%s", (patient_id, hospital_id))
        patient = cursor.fetchone()
        if patient:
            p_email = patient["email"]
            cursor.execute("DELETE FROM users WHERE email=%s AND role='patient'", (p_email,))
            cursor.execute("DELETE FROM patients WHERE patient_id=%s AND hospital_id=%s", (patient_id, hospital_id))
            db.commit()
            flash("Patient deleted successfully.", "success")
        else:
            flash("Patient not found or unauthorized.", "danger")
    except Exception as e:
        db.rollback()
        flash(f"Error deleting patient: {e}", "danger")
    finally:
        if 'cursor' in locals():
            cursor.close()
    return redirect(url_for("hospital_admin_patients"))

# ====================================================================
# Patient Dashboard Route
# ====================================================================
@app.route("/patient/my-records")
@app.route("/patient/my_records.html")
def patient_my_records():
    if session.get("user_role") != "patient" or not session.get("patient_id"):
        return redirect(url_for("login"))

    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT p.*, h.hospital_name FROM patients p "
            "LEFT JOIN hospitals h ON h.hospital_id=p.hospital_id "
            "WHERE p.patient_id=%s AND p.hospital_id=%s LIMIT 1",
            (session["patient_id"], session.get("patient_hospital_id")),
        )
        patient = cursor.fetchone()
        if not patient:
            session.pop("patient_id", None)
            session.pop("patient_hospital_id", None)
            flash("Your patient profile could not be found.", "danger")
            return redirect(url_for("login"))

        cursor.execute(
            "SELECT COUNT(*) AS present FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name='medical_records'"
        )
        records_available = bool(cursor.fetchone()["present"])
        records = []
        prescriptions_available = False
        attachments_available = False
        if records_available:
            cursor.execute(
                "SELECT mr.*, d.full_name AS doctor_name, d.specialization, "
                "h.hospital_name FROM medical_records mr "
                "LEFT JOIN doctors d ON d.doctor_id=mr.doctor_id "
                "LEFT JOIN hospitals h ON h.hospital_id=mr.hospital_id "
                "WHERE mr.patient_id=%s AND mr.hospital_id=%s "
                "ORDER BY mr.visit_datetime DESC, mr.record_id DESC",
                (patient["patient_id"], patient["hospital_id"]),
            )
            records = cursor.fetchall()
            cursor.execute(
                "SELECT COUNT(*) AS present FROM information_schema.tables "
                "WHERE table_schema=DATABASE() AND table_name='prescriptions'"
            )
            prescriptions_available = bool(cursor.fetchone()["present"])
            cursor.execute(
                "SELECT COUNT(*) AS present FROM information_schema.tables "
                "WHERE table_schema=DATABASE() AND table_name='record_attachments'"
            )
            attachments_available = bool(cursor.fetchone()["present"])
        for record in records:
            for field, value in record.items():
                if value is not None and not isinstance(value, (str, int, float, bool)):
                    record[field] = str(value)
            record["prescriptions"] = []
            record["attachments"] = []
            if prescriptions_available:
                cursor.execute(
                    "SELECT medication_name, dosage, frequency, duration "
                    "FROM prescriptions WHERE record_id=%s ORDER BY prescription_id",
                    (record["record_id"],),
                )
                record["prescriptions"] = cursor.fetchall()
            if attachments_available:
                cursor.execute(
                    "SELECT attachment_id, file_name, file_type, file_size_kb, uploaded_at "
                    "FROM record_attachments WHERE record_id=%s ORDER BY attachment_id",
                    (record["record_id"],),
                )
                record["attachments"] = cursor.fetchall()
            for attachment in record["attachments"]:
                if attachment.get("uploaded_at") is not None:
                    attachment["uploaded_at"] = str(attachment["uploaded_at"])

        return render_template("patient/my_records.html", patient=patient, records=records)
    except Exception as error:
        db.rollback()
        print("DB Error Patient My Records:", error)
        return render_template(
            "patient/my_records.html",
            patient={"full_name": "N/A", "hospital_name": "N/A"},
            records=[],
        )
    finally:
        if cursor is not None:
            cursor.close()


@app.route("/patient/records/<int:record_id>/attachments/<int:attachment_id>/download")
def patient_record_attachment_download(record_id, attachment_id):
    if session.get("user_role") != "patient" or not session.get("patient_id"):
        return redirect(url_for("login"))

    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT ra.file_path, ra.file_name FROM record_attachments ra "
            "INNER JOIN medical_records mr ON mr.record_id=ra.record_id "
            "WHERE ra.attachment_id=%s AND ra.record_id=%s "
            "AND mr.patient_id=%s AND mr.hospital_id=%s",
            (attachment_id, record_id, session["patient_id"], session.get("patient_hospital_id")),
        )
        attachment = cursor.fetchone()
        if not attachment:
            abort(404)
        file_path = Path(app.static_folder) / attachment["file_path"]
        if not file_path.is_file():
            abort(404)
        return send_file(file_path, as_attachment=True, download_name=attachment["file_name"])
    finally:
        if cursor is not None:
            cursor.close()


@app.route("/patient/reports")
@app.route("/patient/reports.html")
def patient_reports():
    if session.get("user_role") != "patient" or not session.get("patient_id"):
        return redirect(url_for("login"))

    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT p.full_name, p.patient_id, p.hospital_id, h.hospital_name "
            "FROM patients p LEFT JOIN hospitals h ON h.hospital_id=p.hospital_id "
            "WHERE p.patient_id=%s AND p.hospital_id=%s LIMIT 1",
            (session["patient_id"], session.get("patient_hospital_id")),
        )
        patient = cursor.fetchone()
        if not patient:
            return redirect(url_for("login"))

        cursor.execute(
            "SELECT COUNT(*) AS present FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name='medical_records'"
        )
        records_available = bool(cursor.fetchone()["present"])
        attachments_available = False
        reports = []
        if records_available:
            cursor.execute(
                "SELECT COUNT(*) AS present FROM information_schema.tables "
                "WHERE table_schema=DATABASE() AND table_name='record_attachments'"
            )
            attachments_available = bool(cursor.fetchone()["present"])
            attachment_select = (
                "ra.attachment_id, ra.file_name, ra.file_type, ra.file_size_kb, ra.uploaded_at"
                if attachments_available else
                "NULL AS attachment_id, NULL AS file_name, NULL AS file_type, "
                "NULL AS file_size_kb, NULL AS uploaded_at"
            )
            attachment_join = "LEFT JOIN record_attachments ra ON ra.record_id=mr.record_id" if attachments_available else ""
            cursor.execute(
                "SELECT mr.record_id, mr.record_type, mr.visit_datetime, mr.diagnosis, "
                "mr.symptoms, mr.clinical_notes, mr.treatment_procedure, mr.status, "
                "d.full_name AS doctor_name, d.specialization, h.hospital_name, "
                f"{attachment_select} FROM medical_records mr "
                "LEFT JOIN doctors d ON d.doctor_id=mr.doctor_id "
                "LEFT JOIN hospitals h ON h.hospital_id=mr.hospital_id "
                f"{attachment_join} "
                "WHERE mr.patient_id=%s AND mr.hospital_id=%s "
                "ORDER BY mr.visit_datetime DESC, mr.record_id DESC, ra.attachment_id",
                (patient["patient_id"], patient["hospital_id"]),
            )
            for report in cursor.fetchall():
                record_type = (report.get("record_type") or "").lower()
                is_report_record = any(term in record_type for term in ("lab", "radiology", "imaging", "ecg", "report"))
                if not report.get("attachment_id") and not is_report_record:
                    continue
                for field, value in report.items():
                    if value is not None and not isinstance(value, (str, int, float, bool)):
                        report[field] = str(value)
                report["report_name"] = report.get("file_name") or report.get("diagnosis") or "N/A"
                reports.append(report)

        return render_template("patient/reports.html", patient=patient, reports=reports)
    except Exception as error:
        db.rollback()
        print("DB Error Patient Reports:", error)
        return render_template(
            "patient/reports.html",
            patient={"full_name": "N/A", "hospital_name": "N/A"},
            reports=[],
        )
    finally:
        if cursor is not None:
            cursor.close()


@app.route("/patient/access-history")
@app.route("/patient/access_history.html")
def patient_access_history():
    if session.get("user_role") != "patient" or not session.get("patient_id"):
        return redirect(url_for("login"))

    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT p.full_name, p.patient_id, p.hospital_id, h.hospital_name "
            "FROM patients p LEFT JOIN hospitals h ON h.hospital_id=p.hospital_id "
            "WHERE p.patient_id=%s AND p.hospital_id=%s LIMIT 1",
            (session["patient_id"], session.get("patient_hospital_id")),
        )
        patient = cursor.fetchone()
        if not patient:
            return redirect(url_for("login"))

        cursor.execute(
            "SELECT COUNT(*) AS present FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name IN "
            "('access_logs', 'audit_logs', 'record_access_logs', 'patient_consents')"
        )
        access_history_available = bool(cursor.fetchone()["present"])
        access_logs = []
        active_consents = []
        # No access/consent schema exists in the current database. Do not
        # infer access events from medical records or create a new table.
        return render_template(
            "patient/access_history.html",
            patient=patient,
            access_logs=access_logs,
            active_consents=active_consents,
            access_history_available=access_history_available,
        )
    except Exception as error:
        db.rollback()
        print("DB Error Patient Access History:", error)
        return render_template(
            "patient/access_history.html",
            patient={"full_name": "N/A", "hospital_name": "N/A"},
            access_logs=[], active_consents=[], access_history_available=False,
        )
    finally:
        if cursor is not None:
            cursor.close()


@app.route("/patient/profile", methods=["GET", "POST"])
@app.route("/patient/profile.html", methods=["GET", "POST"])
def patient_profile():
    if session.get("user_role") != "patient" or not session.get("patient_id"):
        return redirect(url_for("login"))

    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT p.*, h.hospital_name FROM patients p "
            "LEFT JOIN hospitals h ON h.hospital_id=p.hospital_id "
            "WHERE p.patient_id=%s AND p.hospital_id=%s LIMIT 1",
            (session["patient_id"], session.get("patient_hospital_id")),
        )
        patient = cursor.fetchone()
        if not patient:
            return redirect(url_for("login"))

        if request.method == "POST":
            action = request.form.get("action", "profile").strip().lower()
            if action == "password":
                current_password = request.form.get("current_password", "")
                new_password = request.form.get("new_password", "")
                confirm_password = request.form.get("confirm_password", "")
                stored_password = patient.get("password") or ""
                password_valid = (
                    check_password_hash(stored_password, current_password)
                    if stored_password.startswith(("scrypt:", "pbkdf2:", "argon2:"))
                    else stored_password == current_password
                )
                if not password_valid:
                    flash("Current password is incorrect.", "danger")
                    return redirect(url_for("patient_profile"))
                if len(new_password) < 8:
                    flash("New password must be at least 8 characters.", "danger")
                    return redirect(url_for("patient_profile"))
                if new_password != confirm_password:
                    flash("New passwords do not match.", "danger")
                    return redirect(url_for("patient_profile"))
                hashed_password = generate_password_hash(new_password)
                cursor.execute(
                    "UPDATE patients SET password=%s WHERE patient_id=%s AND hospital_id=%s",
                    (hashed_password, patient["patient_id"], patient["hospital_id"]),
                )
                if session.get("user_id"):
                    cursor.execute(
                        "UPDATE users SET password=%s WHERE user_id=%s AND role='patient'",
                        (hashed_password, session["user_id"]),
                    )
                db.commit()
                flash("Password updated successfully.", "success")
                return redirect(url_for("patient_profile"))

            fields = {
                "full_name": request.form.get("full_name", "").strip(),
                "email": request.form.get("email", "").strip().lower(),
                "phone": request.form.get("phone", "").strip(),
                "date_of_birth": request.form.get("date_of_birth", "").strip(),
                "gender": request.form.get("gender", "").strip(),
                "blood_group": request.form.get("blood_group", "").strip(),
                "address": request.form.get("address", "").strip(),
                "emergency_contact": request.form.get("emergency_contact", "").strip(),
                "emergency_phone": request.form.get("emergency_phone", "").strip(),
            }
            if not fields["full_name"] or not fields["email"]:
                flash("Full name and email are required.", "danger")
                return redirect(url_for("patient_profile"))
            if "@" not in fields["email"] or " " in fields["email"]:
                flash("Enter a valid email address.", "danger")
                return redirect(url_for("patient_profile"))
            if fields["date_of_birth"]:
                try:
                    date.fromisoformat(fields["date_of_birth"])
                except ValueError:
                    flash("Enter a valid date of birth.", "danger")
                    return redirect(url_for("patient_profile"))
            cursor.execute(
                "SELECT patient_id FROM patients WHERE email=%s AND patient_id<>%s",
                (fields["email"], patient["patient_id"]),
            )
            if cursor.fetchone():
                flash("Another patient already uses that email address.", "danger")
                return redirect(url_for("patient_profile"))
            if session.get("user_id"):
                cursor.execute(
                    "SELECT user_id FROM users WHERE email=%s AND user_id<>%s",
                    (fields["email"], session["user_id"]),
                )
                if cursor.fetchone():
                    flash("That email address is already in use.", "danger")
                    return redirect(url_for("patient_profile"))
            cursor.execute(
                "UPDATE patients SET full_name=%s, email=%s, phone=%s, date_of_birth=%s, "
                "gender=%s, blood_group=%s, address=%s, emergency_contact=%s, emergency_phone=%s "
                "WHERE patient_id=%s AND hospital_id=%s",
                (
                    fields["full_name"], fields["email"], fields["phone"], fields["date_of_birth"] or None,
                    fields["gender"], fields["blood_group"], fields["address"], fields["emergency_contact"],
                    fields["emergency_phone"], patient["patient_id"], patient["hospital_id"],
                ),
            )
            if session.get("user_id"):
                cursor.execute(
                    "UPDATE users SET full_name=%s, email=%s, phone=%s "
                    "WHERE user_id=%s AND role='patient'",
                    (fields["full_name"], fields["email"], fields["phone"], session["user_id"]),
                )
            db.commit()
            flash("Profile updated successfully.", "success")
            return redirect(url_for("patient_profile"))

        cursor.execute(
            "SELECT COUNT(*) AS count FROM medical_records WHERE patient_id=%s AND hospital_id=%s",
            (patient["patient_id"], patient["hospital_id"]),
        )
        record_count = cursor.fetchone()["count"]
        cursor.execute(
            "SELECT MAX(visit_datetime) AS last_visit FROM medical_records WHERE patient_id=%s AND hospital_id=%s",
            (patient["patient_id"], patient["hospital_id"]),
        )
        last_visit = cursor.fetchone()["last_visit"]
        last_visit = str(last_visit) if last_visit else "N/A"
        cursor.execute(
            "SELECT d.full_name FROM medical_records mr INNER JOIN doctors d ON d.doctor_id=mr.doctor_id "
            "WHERE mr.patient_id=%s AND mr.hospital_id=%s ORDER BY mr.visit_datetime DESC LIMIT 1",
            (patient["patient_id"], patient["hospital_id"]),
        )
        doctor_row = cursor.fetchone()
        patient["doctor_name"] = doctor_row["full_name"] if doctor_row else "N/A"
        patient["record_count"] = record_count
        patient["last_visit"] = last_visit
        patient["age"] = "N/A"
        if patient.get("date_of_birth"):
            today = date.today()
            dob = patient["date_of_birth"]
            patient["age"] = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            patient["date_of_birth"] = dob.isoformat()
        return render_template("patient/profile.html", patient=patient)
    except Exception as error:
        db.rollback()
        print("DB Error Patient Profile:", error)
        return render_template("patient/profile.html", patient={"full_name": "N/A", "hospital_name": "N/A"})
    finally:
        if cursor is not None:
            cursor.close()


@app.route("/patient/dashboard")
@app.route("/patient/dashboard.html")
def patient_dashboard():
    if session.get("user_role") != "patient":
        return redirect(url_for("login"))

    cursor = None
    empty = {
        "patient": {"full_name": "N/A", "patient_id": None, "hospital_name": "N/A"},
        "stats": {"records": "N/A", "verified": "N/A", "doctors": "N/A", "appointments": "N/A", "prescriptions": "N/A"},
        "recent_records": [], "doctors": [], "appointments": [], "last_visit": "N/A",
    }
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT p.*, h.hospital_name FROM patients p "
            "LEFT JOIN hospitals h ON h.hospital_id=p.hospital_id "
            "WHERE p.patient_id=%s AND p.hospital_id=%s LIMIT 1",
            (session.get("patient_id"), session.get("patient_hospital_id")),
        )
        patient = cursor.fetchone()
        if not patient:
            return redirect(url_for("login"))
        patient["hospital_name"] = patient.get("hospital_name") or "N/A"
        if patient.get("date_of_birth"):
            today = date.today()
            dob = patient["date_of_birth"]
            patient["age"] = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        else:
            patient["age"] = "N/A"
        for field in ("date_of_birth", "created_at"):
            if patient.get(field) is not None:
                patient[field] = str(patient[field])

        stats = {"records": 0, "verified": 0, "doctors": 0, "appointments": "N/A", "prescriptions": "N/A"}
        recent_records, doctors, appointments = [], [], []
        last_visit = "N/A"
        cursor.execute(
            "SELECT COUNT(*) AS present FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name='medical_records'"
        )
        records_available = bool(cursor.fetchone()["present"])
        if records_available:
            cursor.execute(
                "SELECT mr.*, d.full_name AS doctor_name, d.specialization, h.hospital_name "
                "FROM medical_records mr "
                "LEFT JOIN doctors d ON d.doctor_id=mr.doctor_id "
                "LEFT JOIN hospitals h ON h.hospital_id=mr.hospital_id "
                "WHERE mr.patient_id=%s AND mr.hospital_id=%s "
                "ORDER BY mr.visit_datetime DESC, mr.record_id DESC LIMIT 5",
                (patient["patient_id"], patient["hospital_id"]),
            )
            recent_records = cursor.fetchall()
            for record in recent_records:
                for field, value in record.items():
                    if value is not None and not isinstance(value, (str, int, float, bool)):
                        record[field] = str(value)
                record["prescriptions"] = []
            cursor.execute(
                "SELECT COUNT(*) AS present FROM information_schema.tables "
                "WHERE table_schema=DATABASE() AND table_name='prescriptions'"
            )
            prescriptions_available = bool(cursor.fetchone()["present"])
            if prescriptions_available:
                cursor.execute(
                    "SELECT COUNT(*) AS count FROM prescriptions pr "
                    "INNER JOIN medical_records mr ON mr.record_id=pr.record_id "
                    "WHERE mr.patient_id=%s AND mr.hospital_id=%s",
                    (patient["patient_id"], patient["hospital_id"]),
                )
                stats["prescriptions"] = cursor.fetchone()["count"]
                for record in recent_records:
                    cursor.execute(
                        "SELECT medication_name, dosage, frequency, duration FROM prescriptions "
                        "WHERE record_id=%s ORDER BY prescription_id",
                        (record["record_id"],),
                    )
                    record["prescriptions"] = cursor.fetchall()
            cursor.execute(
                "SELECT COUNT(*) AS count FROM medical_records WHERE patient_id=%s AND hospital_id=%s",
                (patient["patient_id"], patient["hospital_id"]),
            )
            stats["records"] = cursor.fetchone()["count"]
            stats["verified"] = stats["records"]
            cursor.execute(
                "SELECT COUNT(DISTINCT doctor_id) AS count FROM medical_records "
                "WHERE patient_id=%s AND hospital_id=%s AND doctor_id IS NOT NULL",
                (patient["patient_id"], patient["hospital_id"]),
            )
            stats["doctors"] = cursor.fetchone()["count"]
            if recent_records:
                last_visit = recent_records[0].get("visit_datetime") or "N/A"
            cursor.execute(
                "SELECT DISTINCT d.doctor_id, d.full_name, d.specialization, d.department, "
                "d.status, h.hospital_name FROM medical_records mr "
                "INNER JOIN doctors d ON d.doctor_id=mr.doctor_id "
                "LEFT JOIN hospitals h ON h.hospital_id=d.hospital_id "
                "WHERE mr.patient_id=%s AND mr.hospital_id=%s ORDER BY d.full_name",
                (patient["patient_id"], patient["hospital_id"]),
            )
            doctors = cursor.fetchall()

        cursor.execute(
            "SELECT COUNT(*) AS present FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name='appointments'"
        )
        appointments_available = bool(cursor.fetchone()["present"])
        if appointments_available:
            cursor.execute("SHOW COLUMNS FROM appointments")
            appointment_columns = {row["Field"] for row in cursor.fetchall()}
            appointment_date = next((name for name in ("appointment_datetime", "appointment_date", "scheduled_at", "date") if name in appointment_columns), None)
            if "patient_id" in appointment_columns and appointment_date:
                status_select = "a.status" if "status" in appointment_columns else "'N/A' AS status"
                doctor_join = "LEFT JOIN doctors d ON d.doctor_id=a.doctor_id" if "doctor_id" in appointment_columns else ""
                doctor_select = "d.full_name AS doctor_name" if "doctor_id" in appointment_columns else "'N/A' AS doctor_name"
                cursor.execute(
                    f"SELECT a.{appointment_date} AS appointment_date, {status_select}, {doctor_select} "
                    f"FROM appointments a {doctor_join} WHERE a.patient_id=%s "
                    f"ORDER BY a.{appointment_date} DESC LIMIT 5",
                    (patient["patient_id"],),
                )
                appointments = cursor.fetchall()
                for appointment in appointments:
                    for field, value in appointment.items():
                        if value is not None and not isinstance(value, (str, int, float, bool)):
                            appointment[field] = str(value)
                cursor.execute("SELECT COUNT(*) AS count FROM appointments WHERE patient_id=%s", (patient["patient_id"],))
                stats["appointments"] = cursor.fetchone()["count"]

        return render_template(
            "patient/dashboard.html", patient=patient, stats=stats,
            recent_records=recent_records, doctors=doctors, appointments=appointments,
            appointments_available=appointments_available, last_visit=last_visit,
        )
    except Exception as error:
        db.rollback()
        print("DB Error Patient Dashboard:", error)
        return render_template("patient/dashboard.html", **empty, appointments_available=False)
    finally:
        if cursor is not None:
            cursor.close()

# ====================================================================
# Hospital Admin Reports Route
# ====================================================================
@app.route("/hospital-admin/reports")
@app.route("/hospital-admin/reports.html")
def hospital_admin_reports():
    if session.get("user_role") != "hospital_admin":
        return redirect(url_for("login"))

    cursor = None
    empty_data = {
        "patient_growth": [0] * 12,
        "active_patient_growth": [0] * 12,
        "record_labels": [],
        "record_counts": [],
        "weekly": {"labels": [], "patients": [0] * 7, "doctors": [0] * 7},
        "top_doctors": [],
        "doctor_total": "N/A",
        "patient_total": "N/A",
        "record_total": "N/A",
        "appointment_total": "N/A"
    }
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT hospital_id, full_name FROM users WHERE user_id=%s", (session.get("user_id"),))
        user_row = cursor.fetchone()
        if not user_row or user_row.get("hospital_id") is None:
            return redirect(url_for("login"))

        hospital_id = user_row["hospital_id"]
        cursor.execute("SELECT hospital_name FROM hospitals WHERE hospital_id=%s", (hospital_id,))
        hospital_row = cursor.fetchone()
        hospital_name = hospital_row["hospital_name"] if hospital_row else "Hospital"
        report_data = dict(empty_data)
        report_data["patient_growth"] = [0] * 12
        report_data["active_patient_growth"] = [0] * 12
        report_data["record_labels"] = []
        report_data["record_counts"] = []
        report_data["top_doctors"] = []
        report_data["weekly"] = dict(empty_data["weekly"])
        report_data["weekly"]["labels"] = []
        report_data["weekly"]["patients"] = [0] * 7
        report_data["weekly"]["doctors"] = [0] * 7

        cursor.execute("SELECT COUNT(*) AS count FROM doctors WHERE hospital_id=%s", (hospital_id,))
        report_data["doctor_total"] = cursor.fetchone()["count"]

        cursor.execute("SELECT MONTH(created_at) AS month, COUNT(*) AS count FROM patients WHERE hospital_id=%s AND YEAR(created_at)=YEAR(CURRENT_DATE()) GROUP BY MONTH(created_at)", (hospital_id,))
        for row in cursor.fetchall():
            report_data["patient_growth"][row["month"] - 1] = row["count"]
        cursor.execute("SELECT MONTH(created_at) AS month, COUNT(*) AS count FROM patients WHERE hospital_id=%s AND status='active' AND YEAR(created_at)=YEAR(CURRENT_DATE()) GROUP BY MONTH(created_at)", (hospital_id,))
        for row in cursor.fetchall():
            report_data["active_patient_growth"][row["month"] - 1] = row["count"]
        cursor.execute("SELECT COUNT(*) AS count FROM patients WHERE hospital_id=%s", (hospital_id,))
        report_data["patient_total"] = cursor.fetchone()["count"]

        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        report_data["weekly"]["labels"] = [(week_start + timedelta(days=index)).strftime("%a %d") for index in range(7)]
        for table, key in (("patients", "patients"), ("doctors", "doctors")):
            cursor.execute(f"SELECT DAYOFWEEK(created_at) - 2 AS weekday, COUNT(*) AS count FROM {table} WHERE hospital_id=%s AND created_at >= %s AND created_at < %s GROUP BY DAYOFWEEK(created_at)", (hospital_id, week_start, today + timedelta(days=1)))
            for row in cursor.fetchall():
                if 0 <= row["weekday"] <= 6:
                    report_data["weekly"][key][row["weekday"]] = row["count"]

        cursor.execute("SELECT COUNT(*) AS count FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='medical_records'")
        records_exist = cursor.fetchone()["count"] > 0
        if records_exist:
            cursor.execute("SHOW COLUMNS FROM medical_records")
            record_columns = {column["Field"] for column in cursor.fetchall()}
            type_field = next((field for field in ("record_type", "type", "category", "record_category") if field in record_columns), None)
            date_field = next((field for field in ("created_at", "record_date", "date_created") if field in record_columns), None)
            doctor_field = next((field for field in ("doctor_id", "doctor", "doctor_id_fk") if field in record_columns), None)
            patient_field = next((field for field in ("patient_id", "patient", "patient_id_fk") if field in record_columns), None)
            if "hospital_id" in record_columns:
                cursor.execute("SELECT COUNT(*) AS count FROM medical_records WHERE hospital_id=%s", (hospital_id,))
                report_data["record_total"] = cursor.fetchone()["count"]
                if type_field:
                    cursor.execute(f"SELECT COALESCE(NULLIF(TRIM({type_field}), ''), 'N/A') AS label, COUNT(*) AS count FROM medical_records WHERE hospital_id=%s GROUP BY {type_field} ORDER BY count DESC", (hospital_id,))
                    type_rows = cursor.fetchall()
                    report_data["record_labels"] = [row["label"] for row in type_rows]
                    report_data["record_counts"] = [row["count"] for row in type_rows]
                if doctor_field and patient_field:
                    month_clause = f" AND mr.{date_field} >= DATE_FORMAT(CURRENT_DATE(), '%%Y-%%m-01')" if date_field else ""
                    cursor.execute(f"SELECT d.full_name, d.specialization, COUNT(mr.{doctor_field}) AS records, COUNT(DISTINCT mr.{patient_field}) AS patients FROM medical_records mr INNER JOIN doctors d ON d.doctor_id=mr.{doctor_field} WHERE mr.hospital_id=%s{month_clause} GROUP BY d.doctor_id, d.full_name, d.specialization ORDER BY records DESC LIMIT 5", (hospital_id,))
                    report_data["top_doctors"] = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) AS count FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='appointments'")
        if cursor.fetchone()["count"] > 0:
            cursor.execute("SHOW COLUMNS FROM appointments")
            appointment_columns = {column["Field"] for column in cursor.fetchall()}
            if "hospital_id" in appointment_columns:
                cursor.execute("SELECT COUNT(*) AS count FROM appointments WHERE hospital_id=%s", (hospital_id,))
                report_data["appointment_total"] = cursor.fetchone()["count"]

        return render_template("hospital-admin/reports.html", hospital_name=hospital_name, admin_name=user_row.get("full_name") or "Hospital Admin", report_year=today.year, report_data=report_data)
    except Exception as error:
        print("DB Error Reports Page:", error)
        return render_template("hospital-admin/reports.html", hospital_name="Hospital", admin_name="Hospital Admin", report_year=date.today().year, report_data=empty_data)
    finally:
        if cursor is not None:
            cursor.close()

# ====================================================================
# Hospital Admin Medical Records Route
# ====================================================================
@app.route("/hospital-admin/medical_records")
@app.route("/hospital-admin/medical_records.html")
def hospital_admin_medical_records():
    if session.get("user_role") != "hospital_admin":
        return redirect(url_for("login"))

    cursor = None
    try:
        db.ping(reconnect=True)
        cursor = db.cursor(dictionary=True)
        user_id = session.get("user_id")

        cursor.execute("SELECT hospital_id, full_name FROM users WHERE user_id=%s", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            return redirect(url_for("login"))

        hospital_id = user_row.get("hospital_id")
        admin_name = user_row.get("full_name") or "Hospital Admin"

        if hospital_id is None:
            return render_template(
                "hospital-admin/medical_records.html",
                records=[],
                stats={
                    "total_records": "N/A",
                    "consultations": "N/A",
                    "lab_results": "N/A",
                    "radiology": "N/A",
                    "prescriptions": "N/A"
                },
                hospital_name="Hospital",
                admin_name=admin_name,
                table_exists=False
            )

        cursor.execute("SELECT hospital_name FROM hospitals WHERE hospital_id=%s", (hospital_id,))
        hospital_row = cursor.fetchone()
        hospital_name = hospital_row["hospital_name"] if hospital_row else "Hospital"

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = 'medical_records'"
        )
        table_exists = cursor.fetchone()["cnt"] > 0

        stats = {
            "total_records": "N/A",
            "consultations": "N/A",
            "lab_results": "N/A",
            "radiology": "N/A",
            "prescriptions": "N/A"
        }
        records = []

        if table_exists:
            try:
                cursor.execute("SHOW COLUMNS FROM medical_records")
                columns = [col["Field"] for col in cursor.fetchall()]
                if columns:
                    id_field = next((name for name in ["medical_record_id", "record_id", "id"] if name in columns), "medical_record_id")
                    patient_field = next((name for name in ["patient_id", "patient", "patient_id_fk"] if name in columns), "patient_id")
                    doctor_field = next((name for name in ["doctor_id", "doctor", "doctor_id_fk"] if name in columns), "doctor_id")
                    record_type_field = next((name for name in ["record_type", "type", "category", "record_category"] if name in columns), "record_type")
                    title_field = next((name for name in ["title", "record_title", "name"] if name in columns), "title")
                    diagnosis_field = next((name for name in ["diagnosis", "summary", "details", "notes"] if name in columns), "diagnosis")
                    status_field = next((name for name in ["status", "record_status"] if name in columns), "status")
                    date_field = next((name for name in ["created_at", "record_date", "date_created"] if name in columns), "created_at")
                    notes_field = next((name for name in ["notes", "description", "details"] if name in columns), "notes")

                    select_cols = [
                        f"mr.{id_field} AS record_id",
                        f"mr.{patient_field} AS patient_id",
                        f"mr.{doctor_field} AS doctor_id",
                        f"mr.{record_type_field} AS record_type",
                        f"mr.{title_field} AS title",
                        f"mr.{diagnosis_field} AS diagnosis",
                        f"mr.{status_field} AS status",
                        f"mr.{date_field} AS created_at",
                        f"mr.{notes_field} AS notes"
                    ]

                    query = f"""
                        SELECT {', '.join(select_cols)},
                               p.full_name AS patient_name,
                               d.full_name AS doctor_name
                        FROM medical_records mr
                        LEFT JOIN patients p ON p.patient_id = mr.{patient_field}
                        LEFT JOIN doctors d ON d.doctor_id = mr.{doctor_field}
                        WHERE mr.hospital_id = %s
                        ORDER BY mr.{date_field} DESC
                    """
                    cursor.execute(query, (hospital_id,))
                    records = cursor.fetchall()

                    for record in records:
                        record["patient_name"] = record.get("patient_name") or "Unknown Patient"
                        record["doctor_name"] = record.get("doctor_name") or "Unknown Doctor"
                        record["record_type"] = (record.get("record_type") or "N/A").strip() or "N/A"
                        record["title"] = record.get("title") or record.get("record_type") or "Medical Record"
                        record["diagnosis"] = record.get("diagnosis") or record.get("notes") or "No diagnosis recorded"
                        record["status"] = (record.get("status") or "").strip() or "Unknown"
                        record["notes"] = record.get("notes") or "No additional notes available."
                        if record.get("created_at"):
                            created_at = record["created_at"]
                            if hasattr(created_at, "strftime"):
                                record["created_at_display"] = created_at.strftime("%b %d, %Y")
                                record["created_at_full"] = created_at.strftime("%d %b %Y, %H:%M")
                            else:
                                record["created_at_display"] = str(created_at)
                                record["created_at_full"] = str(created_at)
                        else:
                            record["created_at_display"] = "N/A"
                            record["created_at_full"] = "N/A"
                        record["record_id_display"] = str(record.get("record_id") or "N/A")

                    stats["total_records"] = len(records)
                    type_counts = {
                        "Consultation": 0,
                        "Lab Result": 0,
                        "Radiology": 0,
                        "Prescription": 0
                    }
                    for rec in records:
                        rtype = str(rec.get("record_type") or "").strip()
                        rtype_lower = rtype.lower()
                        if "consult" in rtype_lower:
                            type_counts["Consultation"] += 1
                        elif "lab" in rtype_lower:
                            type_counts["Lab Result"] += 1
                        elif "radi" in rtype_lower:
                            type_counts["Radiology"] += 1
                        elif "pres" in rtype_lower:
                            type_counts["Prescription"] += 1
                    stats["consultations"] = type_counts["Consultation"]
                    stats["lab_results"] = type_counts["Lab Result"]
                    stats["radiology"] = type_counts["Radiology"]
                    stats["prescriptions"] = type_counts["Prescription"]
            except Exception as e:
                print("Medical record fetch error:", e)
                records = []
                stats = {
                    "total_records": 0,
                    "consultations": 0,
                    "lab_results": 0,
                    "radiology": 0,
                    "prescriptions": 0
                }

        return render_template(
            "hospital-admin/medical_records.html",
            records=records,
            stats=stats,
            hospital_name=hospital_name,
            admin_name=admin_name,
            table_exists=table_exists
        )
    except Exception as e:
        print("DB Error Medical Records Page:", e)
        return render_template(
            "hospital-admin/medical_records.html",
            records=[],
            stats={
                "total_records": "N/A",
                "consultations": "N/A",
                "lab_results": "N/A",
                "radiology": "N/A",
                "prescriptions": "N/A"
            },
            hospital_name="Hospital",
            admin_name="Hospital Admin",
            table_exists=False
        )
    finally:
        if cursor is not None:
            cursor.close()

# Automatically create routes for every HTML file
for html in templates_dir.rglob("*.html"):

    relative = html.relative_to(templates_dir).as_posix()

    # Skip pages already created above
    if relative in [
        "index.html",
        "login.html",
        "hospital_registration.html",
        "system-admin/dashboard.html",
        "system-admin/hospital_requests.html",
        "system-admin/hospitals.html",
        "system-admin/analytics.html",
        "system-admin/settings.html",
        "hospital-admin/dashboard.html",
        "hospital-admin/doctors.html",
        "hospital-admin/patients.html",
        "hospital-admin/reports.html",
        "hospital-admin/settings.html",
        "doctor/dashboard.html",
        "doctor/patients.html",
        "doctor/create_record.html",
        "doctor/upload_reports.html",
        "doctor/medical_history.html",
        "doctor/profile.html",
        "patient/dashboard.html",
        "patient/my_records.html",
        "patient/reports.html",
        "patient/access_history.html",
        "patient/profile.html"
    ]:
        continue

    # /doctor/dashboard
    route = "/" + relative.replace(".html", "")

    # /doctor/dashboard.html (alias)
    route_html = "/" + relative

    endpoint = relative.replace("/", "_").replace(".html", "")

    def make_view(template_name):
        def view():
            return render_template(template_name)
        return view

    app.add_url_rule(
        route,
        endpoint=endpoint,
        view_func=make_view(relative)
    )

    app.add_url_rule(
        route_html,
        endpoint=endpoint + "_html",
        view_func=make_view(relative)
    )


@app.route("/__health__")
def health__():
    return "ok"


# Safety fallback: serve templates by their relative path under templates/
# This prevents 500/TemplateNotFound when navigation links don't match endpoints.
@app.route("/<path:template_path>.html")
def template_by_path(template_path: str):
    # Prefer to only render existing templates.
    candidate = f"{template_path}.html"
    if (templates_dir / candidate).exists():
        return render_template(candidate)
    abort(404)



@app.route("/<path:template_path>")
def template_by_path_no_ext(template_path: str):
    # Only attempt to load templates if the requested path matches an existing template
    candidate = f"{template_path}.html"
    if (templates_dir / candidate).exists():
        return render_template(candidate)
    abort(404)


if __name__ == "__main__":
    # Ensure stack traces are visible in console for debugging
    app.run(debug=True, use_reloader=False)


