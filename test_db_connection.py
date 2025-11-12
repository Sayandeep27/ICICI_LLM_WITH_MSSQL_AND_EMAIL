import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

try:
    conn = pyodbc.connect(os.getenv("MSSQL_DSN"))
    print("✅ Connected successfully to SQL Server!")
    conn.close()
except Exception as e:
    print("❌ Connection failed:", e)
