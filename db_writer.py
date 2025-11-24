# db_writer.py
import pyodbc
from datetime import datetime

def get_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost;DATABASE=ApplessDB;Trusted_Connection=yes;"
    )

def update_task_status(task_id, new_status):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE projects
            SET status = ?
            WHERE id = ?
        """, (new_status, task_id))
        conn.commit()
        print(f"✅ Task {task_id} updated to {new_status}")
    except Exception as e:
        print("❌ DB Update Error:", e)
    finally:
        try:
            conn.close()
        except:
            pass

def ensure_department_exists(name):
    mapping = {
        "hr": "HR",
        "finance": "Finance",
        "it": "IT",
        "hardware": "Hardware"
    }
    if not name:
        return "IT"
    return mapping.get(name.lower(), "IT")

def insert_project(data):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO projects (project_type, owner_email, assigned_dept, time_required, status, priority, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("project_type", "Unknown"),
            data.get("owner_email", ""),
            ensure_department_exists(data.get("assigned_dept")),
            data.get("time_required", "Not specified"),
            data.get("status", "pending"),
            data.get("priority", "MEDIUM"),
            data.get("summary", "No summary provided")
        ))
        conn.commit()
        print(f"🟩 Inserted new project: {data.get('project_type')}")
    except Exception as e:
        print("❌ DB Error insert:", e)
    finally:
        try:
            conn.close()
        except:
            pass

def insert_project_update(project_id, update_message, from_email, update_type="reply"):
    """
    Store an update for a project (admin reply or sender status message).
    update_type can be "reply" (admin) or "sender" (incoming sender update).
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO project_updates (project_id, update_message, from_email, update_type, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (project_id, update_message, from_email, update_type, datetime.utcnow()))
        conn.commit()
        print(f"📝 Inserted update for project {project_id}")
    except Exception as e:
        print("❌ DB Error insert_project_update:", e)
    finally:
        try:
            conn.close()
        except:
            pass
