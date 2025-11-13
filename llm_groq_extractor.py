import os
import json
import re
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    groq_api_key=os.getenv("GROQ_API_KEY")
)

# ------------------------------
# A) Extract NORMAL project info
# ------------------------------

def extract_task_info(subject, body):
    prompt = f"""
Extract the following fields from this email and return STRICT JSON:
- project_type (short label)
- assigned_dept (HR / Finance / IT / Hardware)
- time_required
- priority (LOW/MEDIUM/HIGH)
- status (pending/resolved)
- summary (2 lines)

Email Subject: {subject}
Email Body: {body}

Return ONLY JSON:
"""

    try:
        response = llm.invoke(prompt)
        text = response.content.strip()

        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON found in LLM response")

        data = json.loads(json_match.group(0))

        return {
            "project_type": data.get("project_type", subject[:40]),
            "assigned_dept": data.get("assigned_dept", "IT"),
            "time_required": data.get("time_required", "Not specified"),
            "priority": data.get("priority", "MEDIUM"),
            "status": data.get("status", "pending"),
            "summary": data.get("summary", subject)
        }

    except Exception as e:
        print("LLM extraction error:", e)
        return {
            "project_type": subject,
            "assigned_dept": "IT",
            "time_required": "Not specified",
            "priority": "MEDIUM",
            "status": "pending",
            "summary": subject
        }


# ---------------------------------------
# B) Extract STATUS UPDATE from any email
# ---------------------------------------

def extract_status_update(subject, body):
    prompt = f"""
Detect if this email is a STATUS UPDATE. Return STRICT JSON only.

Rules:
- If email mentions "task" or "ticket" with an ID → extract task_id
- Detect if the email says: resolved, completed, done → new_status = "resolved"
- Detect if email says: in progress, working on, pending → new_status = "pending"
- If no clear status → new_status = null

Return JSON ONLY in exactly this structure:
{{
  "is_status_update": true/false,
  "task_id": number or null,
  "new_status": "resolved" / "pending" / null
}}

Email Subject: {subject}
Email Body: {body}
"""

    try:
        response = llm.invoke(prompt)
        text = response.content.strip()

        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON found")

        data = json.loads(json_match.group(0))

        return {
            "is_status_update": data.get("is_status_update", False),
            "task_id": data.get("task_id"),
            "new_status": data.get("new_status")
        }

    except Exception as e:
        print("❌ Status update extraction failed:", e)
        return {"is_status_update": False, "task_id": None, "new_status": None}
