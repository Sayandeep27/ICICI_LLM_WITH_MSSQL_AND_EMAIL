import pyodbc

def ensure_department_exists(dept_name):
    try:
        if not dept_name or not isinstance(dept_name, str):
            dept_name = "IT"
        dept_name = dept_name.strip().lower()

        mapping = {
            "hr": "HR",
            "finance": "Finance",
            "it": "IT",
            "hardware": "Hardware"
        }

        return mapping.get(dept_name, "IT")

    except Exception as e:
        print("Error ensuring department exists:", e)
        return "IT"

def insert_project(data):
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=localhost;"
            "DATABASE=ApplessDB;"
            "Trusted_Connection=yes;"
        )
        cursor = conn.cursor()

        project_type = data.get("project_type", "Unknown")
        owner_email = data.get("owner_email", "")
        assigned_dept = ensure_department_exists(data.get("assigned_dept"))
        time_required = data.get("time_required", "Not specified")
        status = data.get("status", "pending")
        priority = data.get("priority", "MEDIUM")
        summary = data.get("summary", "No summary provided")

        cursor.execute("""
            INSERT INTO projects (project_type, owner_email, assigned_dept, time_required, status, priority, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            project_type,
            owner_email,
            assigned_dept,
            time_required,
            status,
            priority,
            summary
        ))

        conn.commit()
        print(f"✅ Inserted new project: {project_type}")

    except Exception as e:
        print("Error inserting project:", e)
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass
