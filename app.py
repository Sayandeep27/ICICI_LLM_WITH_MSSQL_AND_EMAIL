from flask import Flask, render_template, request, redirect, url_for
import pyodbc
import urllib.parse

app = Flask(__name__, template_folder="template")


def get_db_connection():
    # adjust connection string if you use SQL auth instead of Trusted_Connection
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=ApplessDB;"
        "Trusted_Connection=yes;"
    )
    return conn


@app.route("/")
def home():
    """Department dashboard (list of departments)"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT name
        FROM departments
        WHERE name IS NOT NULL AND name <> ''
        ORDER BY name
    """)
    departments = [row[0] for row in cur.fetchall()]
    conn.close()
    return render_template("index.html", departments=departments)


@app.route("/<dept_name>")
def department_view(dept_name):
    """Show projects assigned to a department"""
    dept_lower = dept_name.strip().lower()
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT name FROM departments
        WHERE LOWER(name) = ? AND name IS NOT NULL AND name <> ''
    """, (dept_lower,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return f"Invalid department name: {dept_name}", 400

    actual_name = row[0]

    cur.execute("""
        SELECT id, project_type, owner_email, assigned_dept,
               time_required, status, priority, created_at, summary
        FROM projects
        WHERE LOWER(assigned_dept) = ?
        ORDER BY created_at DESC
    """, (dept_lower,))
    projects = cur.fetchall()
    conn.close()

    return render_template("department.html", dept=actual_name, projects=projects)


#
# Sender dashboard pages
#
@app.route("/sender", methods=["GET", "POST"])
def sender_lookup():
    """
    If GET: show a small form where a user types their email address.
    If POST: redirect to /sender/results?email=<urlencoded>
    """
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            return render_template("sender_form.html", error="Please enter an email address.")
        # url encode so it can be passed in the URL safely
        return redirect(url_for("sender_results", email=urllib.parse.quote_plus(email)))

    # GET
    return render_template("sender_form.html")


@app.route("/sender/results")
def sender_results():
    """
    Display projects for a given owner_email.
    Use a LIKE search to match stored formats like 'Name <addr>' or '<addr>'.
    Example URL: /sender/results?email=alice%40example.com
    """
    raw_email = request.args.get("email", "")
    if not raw_email:
        return redirect(url_for("sender_lookup"))

    # decode if necessary (we encoded via quote_plus during redirect)
    email = urllib.parse.unquote_plus(raw_email).strip().lower()

    # prepare a LIKE pattern that will match stored values that include the email
    like_pattern = f"%{email}%"

    conn = get_db_connection()
    cur = conn.cursor()

    # fetch matching projects
    cur.execute("""
        SELECT id, project_type, owner_email, assigned_dept,
               time_required, status, priority, created_at, summary
        FROM projects
        WHERE LOWER(owner_email) LIKE ?
        ORDER BY created_at DESC
    """, (like_pattern,))

    projects = cur.fetchall()

    # Simple stat summary
    total = len(projects)
    pending = sum(1 for p in projects if (p.status or "").lower() == "pending")
    resolved = sum(1 for p in projects if (p.status or "").lower() == "resolved")

    conn.close()

    return render_template(
        "sender_dashboard.html",
        email_display=email,
        projects=projects,
        total=total,
        pending=pending,
        resolved=resolved
    )


if __name__ == "__main__":
    app.run(debug=True)
