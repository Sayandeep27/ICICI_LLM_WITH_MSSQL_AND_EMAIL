# llm_groq_extractor.py
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

Return ONLY JSON.
"""
    try:
        response = llm.invoke(prompt)
        text = response.content.strip()
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON found in LLM response")
        data = json.loads(json_match.group(0))
        return {
            "project_type": data.get("project_type", (subject or "Unknown")[:100]),
            "assigned_dept": data.get("assigned_dept", "IT"),
            "time_required": data.get("time_required", "Not specified"),
            "priority": data.get("priority", "MEDIUM"),
            "status": data.get("status", "pending"),
            "summary": data.get("summary", subject or "No summary provided")
        }
    except Exception as e:
        print("LLM extraction error:", e)
        return {
            "project_type": subject or "Unknown",
            "assigned_dept": "IT",
            "time_required": "Not specified",
            "priority": "MEDIUM",
            "status": "pending",
            "summary": subject or "No summary provided"
        }

# ---------------------------------------
# B) Extract STATUS UPDATE from any email
# ---------------------------------------
def extract_status_update(subject, body):
    """
    Return dict:
    {
      "is_status_update": bool,
      "task_id": int or None,
      "new_status": "resolved" / "pending" / "in-progress" / None,
      "raw_text": "..."
    }
    Uses LLM first; fallback to regex and keyword heuristics.
    """
    combined = f"Subject: {subject}\n\n{body or ''}"
    prompt = f"""
Detect if this email is a STATUS UPDATE. Return STRICT JSON only.

Rules:
- If email mentions "task" or "ticket" with an ID → extract task_id
- Detect if the email says: resolved, completed, done, fixed, solved, closed, no longer needed
  → new_status = "resolved"
- Detect if the email says: in progress, working on, pending → new_status = "pending"
- If no clear status → new_status = null

Return JSON ONLY in exactly this structure:
{{
  "is_status_update": true/false,
  "task_id": number or null,
  "new_status": "resolved" / "pending" / null
}}

Email:
{combined}
"""
    try:
        response = llm.invoke(prompt)
        text = response.content.strip()
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            return {
                "is_status_update": bool(data.get("is_status_update")),
                "task_id": data.get("task_id"),
                "new_status": data.get("new_status"),
                "raw_text": text
            }
    except Exception as e:
        print("Status update detection via LLM failed:", e)

    # --- fallback heuristic (regex + keywords) ---
    lower = combined.lower() if combined else ""
    # find task id like "task 138" or "#138" or "ticket 138"
    id_match = re.search(r"(?:task|ticket|id)\s*[:#]?\s*(\d{1,6})", lower)
    tid = int(id_match.group(1)) if id_match else None

    resolved_keywords = ["resolved", "done", "completed", "issue fixed", "fixed", "solved", "closed", "no longer needed"]
    pending_keywords = ["in progress", "working on", "pending", "not yet"]

    new_status = None
    for kw in resolved_keywords:
        if kw in lower:
            new_status = "resolved"
            break
    if new_status is None:
        for kw in pending_keywords:
            if kw in lower:
                new_status = "pending"
                break

    is_status = (tid is not None) and (new_status is not None)
    return {"is_status_update": bool(is_status), "task_id": tid, "new_status": new_status, "raw_text": combined}
