# app.py
from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import urllib.parse

from db_writer import (
    get_connection, insert_project_update
)
from mailer import send_email
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, template_folder="template")


# ---------------------------------------------------------
# Fetch Departments
# ---------------------------------------------------------
def fetch_departments():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM departments ORDER BY name")
    departments = [r[0] for r in cur.fetchall()]
    conn.close()
    return departments


# ---------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------
@app.route("/")
def home():
    departments = fetch_departments()
    return render_template("index.html", departments=departments)


# ---------------------------------------------------------
# DEPARTMENT PAGE WITH FILTERS (status, priority, email)
# ---------------------------------------------------------
@app.route("/<dept_name>")
def department_view(dept_name):
    dept_lower = dept_name.strip().lower()

    # NEW FILTER
    email_filter = request.args.get("email_filter", "").strip().lower()
    status_filter = request.args.get("status", "")
    priority_filter = request.args.get("priority", "")

    conn = get_connection()
    cur = conn.cursor()

    # Check if department exists
    cur.execute("SELECT name FROM departments WHERE LOWER(name)=?", (dept_lower,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return f"Invalid department: {dept_name}", 400
    actual_name = row[0]

    # Build Dynamic Query
    query = """
        SELECT id, project_type, owner_email, assigned_dept,
               time_required, status, priority, created_at, summary
        FROM projects
        WHERE LOWER(assigned_dept) = ?
    """
    params = [dept_lower]

    # Filter by email
    if email_filter:
        query += " AND LOWER(owner_email) LIKE ?"
        params.append(f"%{email_filter}%")

    # Filter by status
    if status_filter:
        query += " AND LOWER(status) = ?"
        params.append(status_filter.lower())

    # Filter by priority
    if priority_filter:
        query += " AND LOWER(priority) = ?"
        params.append(priority_filter.lower())

    query += " ORDER BY created_at DESC"

    cur.execute(query, params)
    projects = cur.fetchall()

    # Load project updates
    project_ids = [str(p.id) for p in projects]
    updates_map = {}

    if project_ids:
        placeholders = ",".join("?" for _ in project_ids)
        q = f"""
            SELECT project_id, update_message, from_email, update_type, created_at
            FROM project_updates
            WHERE project_id IN ({placeholders})
            ORDER BY created_at ASC
        """
        cur.execute(q, project_ids)
        rows = cur.fetchall()

        for r in rows:
            updates_map.setdefault(r.project_id, []).append({
                "message": r.update_message,
                "from_email": r.from_email,
                "update_type": r.update_type,
                "created_at": r.created_at
            })

    # Prepare data
    projects_list = []
    for p in projects:
        projects_list.append({
            "id": p.id,
            "project_type": p.project_type,
            "owner_email": p.owner_email,
            "assigned_dept": p.assigned_dept,
            "time_required": p.time_required,
            "status": p.status,
            "priority": p.priority,
            "created_at": p.created_at,
            "summary": p.summary,
            "updates": updates_map.get(p.id, [])
        })

    conn.close()

    return render_template(
        "department.html",
        dept=actual_name,
        projects=projects_list,
        status_filter=status_filter,
        priority_filter=priority_filter,
        email_filter=email_filter      # NEW
    )


# ---------------------------------------------------------
# DEPARTMENT STATISTICS PAGE
# ---------------------------------------------------------
@app.route("/<dept_name>/dashboard")
def department_dashboard(dept_name):
    dept_lower = dept_name.strip().lower()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT status, priority
        FROM projects
        WHERE LOWER(assigned_dept)=?
    """, (dept_lower,))

    rows = cur.fetchall()
    conn.close()

    total = len(rows)
    pending = sum(1 for r in rows if (r.status or "").lower() == "pending")
    resolved = sum(1 for r in rows if (r.status or "").lower() == "resolved")

    pending_priority = {"high": 0, "medium": 0, "low": 0}
    resolved_priority = {"high": 0, "medium": 0, "low": 0}

    for r in rows:
        pr = (r.priority or "").lower()
        if pr not in ["high", "medium", "low"]:
            continue

        if (r.status or "").lower() == "pending":
            pending_priority[pr] += 1
        else:
            resolved_priority[pr] += 1

    return render_template(
        "department_stats.html",
        dept=dept_name,
        total=total,
        pending=pending,
        resolved=resolved,
        pending_priority=pending_priority,
        resolved_priority=resolved_priority
    )


# ---------------------------------------------------------
# SENDER LOOKUP
# ---------------------------------------------------------
@app.route("/sender", methods=["GET", "POST"])
def sender_lookup():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            return render_template("sender_form.html", error="Please enter an email address.")
        return redirect(url_for("sender_results", email=urllib.parse.quote_plus(email)))
    return render_template("sender_form.html")



# ---------------------------------------------------------
# SENDER DASHBOARD
# ---------------------------------------------------------
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

    projects = cur.fetchall()

    projects_list = []
    project_ids = []

    for p in projects:
        projects_list.append({
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
        project_ids.append(str(p.id))

    updates_map = {}

    if project_ids:
        placeholders = ",".join("?" for _ in project_ids)
        q = f"""
            SELECT project_id, update_message, from_email, update_type, created_at
            FROM project_updates
            WHERE project_id IN ({placeholders})
            ORDER BY created_at ASC
        """
        cur.execute(q, project_ids)
        rows = cur.fetchall()

        for r in rows:
            updates_map.setdefault(r.project_id, []).append({
                "message": r.update_message,
                "from_email": r.from_email,
                "update_type": r.update_type,
                "created_at": r.created_at
            })

    total = len(projects_list)
    pending = sum(1 for p in projects_list if (p["status"] or "").lower() == "pending")
    resolved = sum(1 for p in projects_list if (p["status"] or "").lower() == "resolved")

    conn.close()

    return render_template(
        "sender_dashboard.html",
        email_display=email,
        projects=projects_list,
        total=total,
        pending=pending,
        resolved=resolved,
        updates_map=updates_map
    )


# ---------------------------------------------------------
# REPLY TO SENDER
# ---------------------------------------------------------
@app.route("/send_reply", methods=["POST"])
def send_reply():
    project_id = request.form.get("project_id")
    reply_message = request.form.get("reply_message", "").strip()

    if not project_id or not reply_message:
        return jsonify({"ok": False, "error": "Missing project_id or message"}), 400

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

    # Send Email
    try:
        send_email(to_address=owner_email, subject=subject, body=reply_message)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to send email: {e}"}), 500

    # Record update
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


# ---------------------------------------------------------
# RUN APP
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
