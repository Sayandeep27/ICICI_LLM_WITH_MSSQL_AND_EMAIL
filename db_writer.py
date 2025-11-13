import pyodbc

def get_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=ApplessDB;"
        "Trusted_Connection=yes;"
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
        conn.close()


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
            data["project_type"],
            data["owner_email"],
            ensure_department_exists(data["assigned_dept"]),
            data["time_required"],
            data["status"],
            data["priority"],
            data["summary"]
        ))

        conn.commit()
        print(f"🟩 Inserted new project: {data['project_type']}")

    except Exception as e:
        print("❌ DB Error insert:", e)
    finally:
        conn.close()
