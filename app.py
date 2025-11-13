from flask import Flask, render_template
import pyodbc

app = Flask(__name__, template_folder="template")

def get_db_connection():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=ApplessDB;"
        "Trusted_Connection=yes;"
    )
    return conn


@app.route("/")
def home():
    conn = get_db_connection()
    cursor = conn.cursor()

    # FIX: Remove empty department names
    cursor.execute("""
        SELECT name 
        FROM departments 
        WHERE name IS NOT NULL AND name <> ''
        ORDER BY name
    """)

    departments = cursor.fetchall()
    conn.close()

    return render_template("index.html", departments=departments)


@app.route("/<dept_name>")
def department_view(dept_name):
    dept_lower = dept_name.strip().lower()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check department exists (with safety)
    cursor.execute("""
        SELECT name 
        FROM departments 
        WHERE LOWER(name) = ?
          AND name IS NOT NULL 
          AND name <> ''
    """, (dept_lower,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return f"Invalid department name: {dept_name}", 400

    actual_name = row[0]

    # Fetch projects under this department
    cursor.execute("""
        SELECT id, project_type, owner_email, assigned_dept,
               time_required, status, priority, created_at, summary
        FROM projects
        WHERE LOWER(assigned_dept) = ?
        ORDER BY created_at DESC
    """, (dept_lower,))

    projects = cursor.fetchall()
    conn.close()

    return render_template("department.html", dept=actual_name, projects=projects)


if __name__ == "__main__":
    app.run(debug=True)
