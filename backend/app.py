import os
import time
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
import groq
from groq import Groq
from dotenv import load_dotenv

from analysis.patient_analysis import analyze_patient
from ai_models import CAUSES

# ---------------- CONFIG ----------------
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Assumes frontend is in a sibling folder to the backend folder
FRONTEND_FOLDER = os.path.join(BASE_DIR, "..", "frontend")
STATIC_FOLDER = os.path.join(BASE_DIR, "static")

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["mortality_risk_db"] 
collection = db["patients"]

# Groq Client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)
app = Flask(__name__)
CORS(app)

# In-memory session tracking for chat context efficiency
chat_sessions = {}

# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return send_from_directory(FRONTEND_FOLDER, "index.html")

# ---------------------------------------
# PATIENT ANALYSIS API
# ---------------------------------------

@app.route("/analyze/<path:patient_id>", methods=["GET"])
def analyze_by_id(patient_id):
    try:
        # 1. Fetch history
        history_cursor = collection.find(
            {"patient_id": {"$regex": f"^{patient_id}$", "$options": "i"}}
        )
        history = list(history_cursor)

        if len(history) == 0:
            return jsonify({"error": f"Patient {patient_id} not found"}), 404

        # Sort manually by converting string dates to datetime objects
        try:
            history.sort(key=lambda x: datetime.strptime(x.get("test_date", "01/01/2000"), "%d/%m/%Y"))
        except Exception as e:
            print(f"Manual sort failed: {e}")

        # 2. Clean IDs for JSON serialization
        for record in history:
            if "_id" in record:
                record["_id"] = str(record["_id"])

        # 3. Run analysis
        result = analyze_patient(history)
        
        if not result or "latest_labs" not in result:
            return jsonify({"error": "Insufficient lab data for analysis"}), 400

        # Ensure fundamental structures exist
        result.setdefault("latest_labs", {})
        result["latest_labs"].setdefault("hba1c", None)
        
        # Ensure SHAP is included if not already handled inside analyze_patient
        if "shap_explanation" not in result:
            result["shap_explanation"] = result.get("feature_contributions", [])
            
        result["patient_id"] = patient_id
        result["patient_name"] = history[-1].get("patient_name", "Unknown")

        # --- High-Level Critical Alerts ---
        enhanced = result.get("enhanced_labs", {})
        alt_val = enhanced.get("alt", {}).get("current_value") or 0
        creat_val = enhanced.get("creatinine", {}).get("current_value") or 0
        hba1c_val = enhanced.get("hba1c", {}).get("current_value") or 0

        if alt_val > 1000:
            result["critical_alert"] = "Severe Liver Injury Suspected"
        elif creat_val > 2:
            result["critical_alert"] = "Severe Kidney Dysfunction"
        elif hba1c_val >= 6.5:
            result["critical_alert"] = "Diabetes Diagnostic Level"
        else:
            result["critical_alert"] = None

        # --- Reference Notes & Possible Causes ---
        if not result.get("reference_notes") or result.get("reference_notes") == "N/A":
            result["reference_notes"] = {
                "ALT": "Enzyme found in liver cells; elevation suggests injury.",
                "Creatinine": "Waste product filtered by kidneys; reflects filtration health.",
                "HbA1c": "Average blood sugar over 3 months."
            }

        if not result.get("possible_causes"):
            result["possible_causes"] = CAUSES

        return jsonify(result)
        
    except Exception:
        print(traceback.format_exc())
        return jsonify({"error": "Analysis failed"}), 500

# ---------------------------------------
# AI CHAT ASSISTANT
# ---------------------------------------

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_msg = data.get("message", "").strip()
        patient_info = data.get("patient_data", {})
        patient_id = str(patient_info.get("patient_id", "unknown"))

        if not user_msg:
            return jsonify({"reply": "Please enter a message."})

        # 1. TOKEN SAVER: Use a tiny session window (Last 2 exchanges only)
        if patient_id not in chat_sessions:
            chat_sessions[patient_id] = []
        
        # Keep only the last 2 rounds of chat (4 messages total)
        short_memory = chat_sessions[patient_id][-4:]

        # 2. TOKEN SAVER: Distill the labs
        labs = patient_info.get('enhanced_labs', {})
        distilled = {k: v.get('current_value') for k, v in labs.items()}

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the HealthTrustAI Clinical Assistant. Your goal is to interpret lab results "
                    f"(ALT, Creatinine, HbA1c) with high precision for Patient {patient_id}. "
                    f"Latest Labs: {distilled}. Always prioritize: "
                    "1. Explain the 'Why' behind the numbers. "
                    "2. Be empathetic but professional. "
                    "3. Use 2-3 sentences max to save tokens. "
                    "4. End with: 'Note: This is an AI interpretation. Please consult your physician for a formal diagnosis.'"
                )
            }
        ]

        # Add the short memory
        messages.extend(short_memory)
        
        # Add current question
        messages.append({"role": "user", "content": user_msg})

        # 3. CALL MODEL
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=150,
            temperature=0.3
        )

        reply_text = response.choices[0].message.content

        # Update Memory
        chat_sessions[patient_id].append({"role": "user", "content": user_msg})
        chat_sessions[patient_id].append({"role": "assistant", "content": reply_text})

        return jsonify({"reply": reply_text})

    except groq.RateLimitError as e:
        # Groq headers often provide 'retry-after'
        retry_after = e.response.headers.get("retry-after", "10") 
        
        # Strip letters if Groq sends "1.5s"
        numeric_wait = "".join(filter(str.isdigit, str(retry_after))) or "10"

        return jsonify({
            "reply": f"Quota reached. Clinical AI will reset in {numeric_wait} seconds.",
            "retry_after": numeric_wait
        }), 429

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"reply": "AI service is temporarily busy."}), 500

# ---------------- STATIC FILES & ASSETS ----------------

@app.route("/health")
def health():
    return jsonify({"status": "running"})

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(FRONTEND_FOLDER, path)

# ---------------- RUN SERVER ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)