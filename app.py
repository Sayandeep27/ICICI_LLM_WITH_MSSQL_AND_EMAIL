from flask import Flask, render_template, request, redirect, url_for, jsonify
import pyodbc
import urllib.parse
import os
from db_writer import (
    get_connection,
    ensure_department_exists,
    insert_project,
    update_task_status,
    insert_project_update
)
from mailer import send_email

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, template_folder="template")


# -----------------------------------------------------------
# FETCH DEPARTMENTS
# -----------------------------------------------------------
def fetch_departments():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM departments WHERE name IS NOT NULL AND name <> '' ORDER BY name")
    departments = [r[0] for r in cur.fetchall()]
    conn.close()
    return departments


# -----------------------------------------------------------
# HOME PAGE
# -----------------------------------------------------------
@app.route("/")
def home():
    departments = fetch_departments()
    return render_template("index.html", departments=departments)


# -----------------------------------------------------------
# DEPARTMENT PROJECT LIST
# -----------------------------------------------------------
@app.route("/<dept_name>")
def department_view(dept_name):
    dept_lower = dept_name.strip().lower()

    conn = get_connection()
    cur = conn.cursor()

    # Validate department
    cur.execute("SELECT name FROM departments WHERE LOWER(name)=?", (dept_lower,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return f"Invalid department name: {dept_name}", 400

    actual_name = row[0]

    # Get projects for this department
    cur.execute("""
        SELECT id, project_type, owner_email, assigned_dept,
               time_required, status, priority, created_at, summary
        FROM projects
        WHERE LOWER(assigned_dept)=?
        ORDER BY created_at DESC
    """, (dept_lower,))

    rows = cur.fetchall()

    projects = []
    for p in rows:
        projects.append({
            "id": p.id,
            "project_type": p.project_type,
            "owner_email": p.owner_email,
            "assigned_dept": p.assigned_dept,
            "time_required": p.time_required,
            "status": p.status,
            "priority": p.priority,
            "created_at": p.created_at,
            "summary": p.summary
        })

    conn.close()

    return render_template("department.html", dept=actual_name, projects=projects)


# -----------------------------------------------------------
# SENDER LOOKUP FORM
# -----------------------------------------------------------
@app.route("/sender", methods=["GET", "POST"])
def sender_lookup():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            return render_template("sender_form.html", error="Please enter an email address.")
        return redirect(url_for("sender_results", email=urllib.parse.quote_plus(email)))

    return render_template("sender_form.html")


# -----------------------------------------------------------
# SENDER DASHBOARD PAGE
# -----------------------------------------------------------
@app.route("/sender/results")
def sender_results():
    raw_email = request.args.get("email", "")
    if not raw_email:
        return redirect(url_for("sender_lookup"))

    email = urllib.parse.unquote_plus(raw_email).strip().lower()
    like_pattern = f"%{email}%"

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, project_type, owner_email, assigned_dept,
               time_required, status, priority, created_at, summary
        FROM projects
        WHERE LOWER(owner_email) LIKE ?
        ORDER BY created_at DESC
    """, (like_pattern,))

    rows = cur.fetchall()

    projects = []
    id_list = []

    for p in rows:
        projects.append({
            "id": p.id,
            "project_type": p.project_type,
            "owner_email": p.owner_email,
            "assigned_dept": p.assigned_dept,
            "time_required": p.time_required,
            "status": p.status,
            "priority": p.priority,
            "created_at": p.created_at,
            "summary": p.summary
        })
        id_list.append(str(p.id))

    # Load updates for these tasks
    updates_map = {}

    if id_list:
        placeholders = ",".join("?" for _ in id_list)
        q = f"""
            SELECT project_id, update_message, from_email, update_type, created_at
            FROM project_updates
            WHERE project_id IN ({placeholders})
            ORDER BY created_at ASC
        """
        cur.execute(q, id_list)
        updates = cur.fetchall()

        for r in updates:
            updates_map.setdefault(r.project_id, []).append({
                "message": r.update_message,
                "from_email": r.from_email,
                "update_type": r.update_type,
                "created_at": r.created_at
            })

    total = len(projects)
    pending = sum(1 for p in projects if (p["status"] or "").lower() == "pending")
    resolved = sum(1 for p in projects if (p["status"] or "").lower() == "resolved")

    conn.close()

    return render_template(
        "sender_dashboard.html",
        email_display=email,
        projects=projects,
        total=total,
        pending=pending,
        resolved=resolved,
        updates_map=updates_map
    )


# -----------------------------------------------------------
# SEND REPLY (AJAX endpoint)
# -----------------------------------------------------------
@app.route("/send_reply", methods=["POST"])
def send_reply():
    project_id = request.form.get("project_id")
    reply_message = request.form.get("reply_message", "").strip()

    if not project_id or not reply_message:
        return jsonify({"ok": False, "error": "Missing project_id or reply message"}), 400

    # Fetch original project to get owner email
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT owner_email, project_type FROM projects WHERE id = ?", (project_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({"ok": False, "error": "Project not found"}), 404

    owner_email = row.owner_email
    project_type = row.project_type

    subject = f"Update on your request: {project_type} (Task {project_id})"

    # --- SEND EMAIL ---
    try:
        send_email(
            to_address=owner_email,
            subject=subject,
            body=reply_message
        )
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to send email: {e}"}), 500

    # --- RECORD UPDATE IN DB ---
    try:
        insert_project_update(
            project_id=int(project_id),
            update_message=reply_message,
            from_email=os.getenv("EMAIL_ADDRESS"),
            update_type="reply"
        )
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to record update: {e}"}), 500

    return jsonify({"ok": True})


# -----------------------------------------------------------
# RUN FLASK
# -----------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
