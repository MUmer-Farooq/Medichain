from __future__ import annotations
from werkzeug.security import generate_password_hash
from pathlib import Path
import mysql.connector
from flask import Flask, abort, render_template, request, redirect, url_for, flash, session


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)

app.secret_key = "N!ghtFalcon"
#sql connection build
db = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="1234",
    database="registration"
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

        # Search user by email and role
        query = """
            SELECT user_id, full_name, email, password, role
            FROM users
            WHERE email = %s AND role = %s
        """

        cursor.execute(query, (email, db_role))
        user = cursor.fetchone()

        # User not found
        if not user:
            flash("User is not registered.", "danger")
            return redirect(url_for("login"))

        # Password verification
        if user["password"] != password:
            flash("Incorrect password.", "danger")
            return redirect(url_for("login"))

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
        "hospital-admin/patients.html"
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


