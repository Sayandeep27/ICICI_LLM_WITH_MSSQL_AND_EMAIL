import os
import json
import re
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

load_dotenv()

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    groq_api_key=os.getenv("GROQ_API_KEY")
)

prompt_template = PromptTemplate(
    input_variables=["subject", "body"],
    template="""
Analyze the email below and extract the following fields in JSON format:
- project_type (short name based on email subject)
- assigned_dept (choose from HR, Finance, IT, Hardware — if unsure, default to IT)
- time_required (in words like '1 day', '2 hours', etc., or 'Not specified')
- priority (LOW, MEDIUM, HIGH)
- status (pending or resolved)
- summary (2-line summary of what the email is about)

Email Subject: {subject}
Email Body: {body}

Respond strictly in JSON only.
"""
)

def extract_task_info(subject, body):
    try:
        prompt = prompt_template.format(subject=subject, body=body)
        response = llm.invoke(prompt)
        text = response.content.strip()

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            data = {}

        return {
            "project_type": data.get("project_type", subject or "Unknown"),
            "assigned_dept": data.get("assigned_dept", "IT"),
            "time_required": data.get("time_required", "Not specified"),
            "priority": data.get("priority", "MEDIUM"),
            "status": data.get("status", "pending"),
            "summary": data.get("summary", "No summary provided")
        }

    except Exception as e:
        print("Groq LLM extraction failed:", e)
        return {
            "project_type": subject or "Unknown",
            "assigned_dept": "IT",
            "time_required": "Not specified",
            "priority": "MEDIUM",
            "status": "pending",
            "summary": "No summary provided"
        }
