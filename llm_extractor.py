import torch_patch
import json
import re
from transformers import AutoTokenizer
from optimum.onnxruntime import ORTModelForSeq2SeqLM


# =========================================
# LLM Extractor using Hugging Face Optimum + ONNXRuntime
# =========================================

model_name = "google/flan-t5-base"

print(f"Loading model '{model_name}' using Optimum ONNXRuntime backend...")

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Load or export ONNX model
try:
    model = ORTModelForSeq2SeqLM.from_pretrained(model_name, export=True)
except Exception as e:
    print("❌ ONNX model load failed:", e)
    print("Falling back to normal model — please verify optimum installation.")
    raise SystemExit()

print("✅ Model loaded successfully (ONNXRuntime backend)")

def extract_task_info(subject: str, body: str):
    """
    Extract structured project details from email subject and body using FLAN-T5 (ONNX).
    """
    prompt = f"""
    Read the following email and extract task details as JSON.

    Subject: {subject}
    Body: {body}

    Return JSON with keys:
    owner_email, project_type, assigned_dept (HR, Finance, IT, Hardware),
    time_required, priority (LOW, MEDIUM, HIGH), status (pending or resolved)
    """

    try:
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(**inputs, max_new_tokens=200)
        text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Parse JSON from output
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            data = {
                "owner_email": "",
                "project_type": subject or "Unknown",
                "assigned_dept": "IT",
                "time_required": "",
                "priority": "MEDIUM",
                "status": "pending",
            }

        return data

    except Exception as e:
        print("❌ LLM extraction failed:", e)
        return {
            "owner_email": "",
            "project_type": subject or "Unknown",
            "assigned_dept": "IT",
            "time_required": "",
            "priority": "MEDIUM",
            "status": "pending",
        }
