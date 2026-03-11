import numpy as np
import pandas as pd
from ai_models import DiseasePredictor, generate_trend_graph, CAUSES
from datetime import datetime

# Initialize AI model once for efficiency
predictor = DiseasePredictor()

# ----------------------------------------
# CLINICAL CONFIGURATION & CONSTANTS
# ----------------------------------------

CLINICAL_THRESHOLDS = {
    "alt": {"min": 7, "max": 55, "unit": "U/L", "label": "Liver Function"},
    "creatinine": {"min": 0.7, "max": 1.3, "unit": "mg/dL", "label": "Kidney Function"},
    "hba1c": {"min": 4.0, "max": 5.6, "unit": "%", "label": "Glycemic Control"}
}

# ----------------------------------------
# HELPERS
# ----------------------------------------

def clean_numeric(val):
    if pd.isna(val) or str(val).strip().upper() == "N/A":
        return None
    try:
        raw = str(val)
        num = "".join(c for c in raw if c.isdigit() or c in ".-")
        return float(num) if num else None
    except:
        return None

def get_severity_color(marker, value):
    """Returns a color hex based on clinical thresholds."""
    if value is None: 
        return "#9ca3af" # Gray for missing data
    
    meta = CLINICAL_THRESHOLDS.get(marker)
    if not meta: 
        return "#000000"
    
    # Logic: Red if 50% over max, Orange if just over max, Green otherwise
    if value > meta["max"] * 1.5: 
        return "#ff4d4f" # Critical Red
    if value > meta["max"]: 
        return "#fb8500" # Warning Orange
    return "#38b000"     # Healthy Green

# ----------------------------------------
# CLINICAL LOGIC
# ----------------------------------------

def calculate_risk_level(score):
    if score < 40:
        return {"level": "LOW", "color": "#38b000"} # Green
    elif score < 70:
        return {"level": "MODERATE", "color": "#fb8500"} # Orange
    else:
        return {"level": "HIGH", "color": "#ff4d4f"} # Red

def calculate_confidence(predictions):
    values = list(predictions.values())
    variance = np.var(values)
    # Heuristic for AI confidence based on prediction spread
    confidence = min(95, 60 + variance)
    return round(confidence, 2)

def generate_patient_summary(predictions, labs):
    highest = max(predictions, key=predictions.get)
    value = predictions[highest]
    organ = highest.replace("_risk", "").capitalize()

    if value < 30:
        return f"Biomarker profile appears stable with low predicted risk for {organ}-related complications."
    elif value < 60:
        return f"Moderate risk indicators detected for {organ}. Continued monitoring of laboratory trends is recommended."
    else:
        return f"High probability of {organ} dysfunction detected based on current biomarker profile. Clinical evaluation is strongly recommended."

def generate_recommendations(predictions, labs):
    recs = []
    
    # Liver Logic
    if predictions.get("liver_risk", 0) > 60:
        recs.append("Monitor liver enzymes (ALT/AST) weekly.")
        recs.append("Evaluate for potential hepatotoxic medication interference.")
    
    # Kidney Logic
    if predictions.get("kidney_risk", 0) > 60:
        recs.append("Decline in GFR suspected. Evaluate renal clearance.")
    
    # HbA1c/Diabetes Logic
    hba1c_val = labs.get("hba1c")
    if hba1c_val:
        if hba1c_val >= 6.5:
            recs.append("Critical HbA1c detected. Urgent clinical diagnostic testing (OGTT) required.")
        elif hba1c_val >= 5.7:
            recs.append("HbA1c indicates prediabetes. Implement low-glycemic dietary changes.")
    
    if not recs:
        recs.append("Maintain current clinical monitoring schedule.")
    return recs

def generate_risk_heatmap(predictions):
    heatmap = []
    for k, v in predictions.items():
        severity = "high" if v >= 70 else "moderate" if v >= 40 else "low"
        heatmap.append({
            "organ": k.replace("_risk", "").capitalize(),
            "risk": v,
            "severity": severity
        })
    return heatmap

# ----------------------------------------
# MAIN ANALYSIS FUNCTION (UNIFIED)
# ----------------------------------------

def analyze_patient(history):
    if not history or len(history) == 0:
        return {"error": "No patient records found"}

    # 1. CLEAN DATA & MAP DATES
    for record in history:
        try:
            d = datetime.strptime(record.get("test_date"), "%d/%m/%Y")
            record['date'] = d.strftime("%Y-%m-%d")
        except:
            record['date'] = None
        
        record['alt'] = clean_numeric(record.get('alt'))
        record['creatinine'] = clean_numeric(record.get('creatinine'))
        record['hba1c'] = clean_numeric(record.get('hba1c'))

    # 2. EXTRACT LATEST DATA & ENRICH WITH CLINICAL CONTEXT
    latest = history[-1]
    labs = {
        "alt": latest.get("alt"),
        "creatinine": latest.get("creatinine"),
        "hba1c": latest.get("hba1c")
    }

    enhanced_labs = {}
    for key in ["alt", "creatinine", "hba1c"]:
        val = labs.get(key)
        meta = CLINICAL_THRESHOLDS.get(key)
        enhanced_labs[key] = {
            "current_value": val,
            "unit": meta["unit"],
            "reference_range": f"{meta['min']}-{meta['max']} {meta['unit']}",
            "status_color": get_severity_color(key, val),
            "label": meta["label"]
        }

    patterns = {
        "alt_pattern": latest.get("liver_pattern"),
        "creatinine_pattern": latest.get("kidney_pattern")
    }

    # 3. AI PREDICTIONS & EXPLANATIONS
    predictions = predictor.predict(labs)
    insights = predictor.explain_prediction(labs)
    feature_importance = predictor.feature_contributions(labs)

    # 4. RISK & CONFIDENCE
    risk_score = round(np.mean(list(predictions.values())), 2)
    risk_info = calculate_risk_level(risk_score)
    confidence = calculate_confidence(predictions)

    # 5. EXTRACT PATTERNS
    detected_patterns = []
    
    # Check Kidney Patterns
    k_pattern = patterns.get("creatinine_pattern", "N/A")
    if k_pattern not in ["N/A", None]:
        detected_patterns.append({
            "area": "Kidney", 
            "pattern": k_pattern, 
            "status": latest.get("kidney_status", "Normal")
        })

    # Check Liver Patterns
    l_pattern = patterns.get("alt_pattern", "N/A")
    if l_pattern not in ["N/A", None]:
        detected_patterns.append({
            "area": "Liver", 
            "pattern": l_pattern, 
            "status": latest.get("liver_status", "Normal")
        })

    # Check HbA1c/Diabetes Patterns
    d_pattern = latest.get("diabetes_pattern", "N/A")
    if d_pattern not in ["N/A", None]:
        detected_patterns.append({
            "area": "Diabetes", 
            "pattern": d_pattern, 
            "status": "High Risk" if (labs.get("hba1c") or 0) >= 6.5 else "Elevated"
        })

    # 6. GENERATE VISUAL DATA & SUMMARIES
    alt_graph = generate_trend_graph(history, "alt")
    creatinine_graph = generate_trend_graph(history, "creatinine")
    hba1c_graph = generate_trend_graph(history, "hba1c")
    
    heatmap = generate_risk_heatmap(predictions)
    summary = generate_patient_summary(predictions, labs)
    recommendations = generate_recommendations(predictions, labs)

    # 7. RETURN UNIFIED DATA OBJECT
    return {
        "enhanced_labs": enhanced_labs, # Primary data for UI Cards
        "latest_labs": labs,
        "predictions": predictions,
        "risk_assessment": {
            "risk_score": risk_score,
            "level": risk_info["level"],
            "color": risk_info["color"],
            "confidence": confidence
        },
        "patient_summary": summary,
        "feature_contributions": feature_importance,
        "shap_explanation": feature_importance,
        "ai_insights_cards": insights, 
        "ai_insights": insights,       
        "recommendations": recommendations,
        "risk_heatmap": heatmap,
        "patterns": detected_patterns,
        
        "reference_notes": {
            "ALT": "ALT is an enzyme found in liver cells. Elevated ALT suggests liver cell injury.",
            "Creatinine": "Creatinine reflects kidney filtration ability and renal health.",
            "HbA1c": "HbA1c measures average blood sugar levels over the past 3 months."
        },
        "possible_causes": CAUSES, 
        "clinical_trajectories": {
            "alt": alt_graph,
            "creatinine": creatinine_graph,
            "hba1c": hba1c_graph
        },
        "visit_history": history
    }