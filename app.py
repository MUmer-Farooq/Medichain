from __future__ import annotations

from pathlib import Path
import os,mysql.connector
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



# Make sure includes can resolve from the repo-level `components/` directory.
# Some templates use: {% include 'components/footer.html' %}
# but `components/` is not under `templates/`.
components_dir = os.path.join(os.path.dirname(__file__), "components")
# Allow templates to include 'components/footer.html' etc.
app.jinja_loader.searchpath.append(os.path.dirname(components_dir))





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

    if request.method == "GET":
        return render_template("hospital_registration.html")

    hospital_name = request.form.get("hospital_name")
    registration_number = request.form.get("reg_number")
    city = request.form.get("city")
    address = request.form.get("address")
    phone = request.form.get("phone")
    hospital_email = request.form.get("hospital_email")

    try:
        db.ping(reconnect=True)

        cursor = db.cursor()

        # Check if email already exists
        cursor.execute(
            "SELECT hospital_id FROM hospitals WHERE hospital_email=%s",
            (hospital_email,)
        )

        if cursor.fetchone():
            flash("Hospital email already registered.", "danger")
            return redirect(url_for("hospital_registration"))

        # Check registration number
        cursor.execute(
            "SELECT hospital_id FROM hospitals WHERE registration_number=%s",
            (registration_number,)
        )

        if cursor.fetchone():
            flash("Registration number already exists.", "danger")
            return redirect(url_for("hospital_registration"))

        sql = """
            INSERT INTO hospitals
            (
                hospital_name,
                registration_number,
                city,
                address,
                phone,
                hospital_email
            )
            VALUES (%s,%s,%s,%s,%s,%s)
        """

        values = (
            hospital_name,
            registration_number,
            city,
            address,
            phone,
            hospital_email
        )

        cursor.execute(sql, values)
        db.commit()

        flash("Hospital registered successfully.", "success")
        return redirect(url_for("hospital_registration"))

    except mysql.connector.Error as err:
        db.rollback()
        flash(f"Database Error: {err}", "danger")
        return redirect(url_for("hospital_registration"))

    finally:
        cursor.close()

# Automatically create routes for every HTML file
for html in templates_dir.rglob("*.html"):

    relative = html.relative_to(templates_dir).as_posix()

    # Skip pages already created above
    if relative in [
        "index.html",
        "login.html",
        "hospital_registration.html",
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


