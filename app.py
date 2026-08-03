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

cursor = db.cursor()
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
        
        cursor.execute("SELECT * FROM hospitals WHERE status='pending' ORDER BY created_at DESC LIMIT 5")
        pending_requests = cursor.fetchall()
        
        cursor.execute("SELECT * FROM hospitals ORDER BY created_at DESC LIMIT 5")
        recent_activities = cursor.fetchall()

        return render_template("system-admin/dashboard.html", 
                               active_hospitals=active_hospitals,
                               pending_requests_count=pending_requests_count,
                               suspended_count=suspended_count,
                               rejected_count=rejected_count,
                               pending_requests=pending_requests,
                               recent_activities=recent_activities)
    except Exception as e:
        print("DB Error:", e)
        return render_template("system-admin/dashboard.html", active_hospitals=0, pending_requests_count=0, suspended_count=0, rejected_count=0, pending_requests=[], recent_activities=[])

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
    period_params = []
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
        "system-admin/analytics.html"
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


