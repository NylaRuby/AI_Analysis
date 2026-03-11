import numpy as np
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# -------------------------------------
# Clinical Knowledge Base
# -------------------------------------

CAUSES = {
    "ALT": [
        "Hepatocellular injury or liver inflammation",
        "Fatty liver disease (metabolic syndrome)",
        "Alcohol-related liver stress",
        "Medication-induced hepatotoxicity",
        "Viral or inflammatory liver conditions"
    ],
    "Creatinine": [
        "Reduced kidney filtration (decreased eGFR)",
        "Chronic kidney disease progression",
        "Dehydration or renal perfusion issues",
        "Medication-induced nephrotoxicity",
        "Long-standing diabetes or hypertension"
    ],
    "HbA1c": [
        "Poor long-term glucose regulation",
        "Type 2 diabetes progression",
        "Insulin resistance or metabolic syndrome",
        "High dietary carbohydrate load",
        "Sedentary lifestyle affecting glycemic control"
    ]
}

# -------------------------------------
# Disease Prediction Model
# -------------------------------------

class DiseasePredictor:

    def __init__(self):
        np.random.seed(42)

        # -------------------------------------
        # Synthetic Medical Dataset (Realistic Scale)
        # -------------------------------------
        samples = 300
        alt = np.random.normal(45, 25, samples)
        creatinine = np.random.normal(1.1, 0.35, samples)
        hba1c = np.random.normal(5.7, 0.9, samples)

        X = np.column_stack([alt, creatinine, hba1c])

        # Labels based on medical thresholds
        liver_labels = (alt > 60).astype(int)
        kidney_labels = (creatinine > 1.4).astype(int)
        diabetes_labels = (hba1c > 6.5).astype(int)

        # -------------------------------------
        # Feature Scaling
        # -------------------------------------
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # -------------------------------------
        # Random Forest Models
        # -------------------------------------
        self.liver_model = RandomForestClassifier(
            n_estimators=150,
            max_depth=6,
            random_state=42
        ).fit(X_scaled, liver_labels)

        self.kidney_model = RandomForestClassifier(
            n_estimators=150,
            max_depth=6,
            random_state=42
        ).fit(X_scaled, kidney_labels)

        self.diabetes_model = RandomForestClassifier(
            n_estimators=150,
            max_depth=6,
            random_state=42
        ).fit(X_scaled, diabetes_labels)

        # -------------------------------------
        # SHAP Explainability Setup
        # -------------------------------------
        self.liver_explainer = shap.TreeExplainer(self.liver_model)
        self.kidney_explainer = shap.TreeExplainer(self.kidney_model)
        self.diabetes_explainer = shap.TreeExplainer(self.diabetes_model)

        self.features = ["alt", "creatinine", "hba1c"]

    # -------------------------------------
    # Risk Prediction
    # -------------------------------------
    def predict(self, labs):
        alt = labs.get("alt", 0)
        creatinine = labs.get("creatinine", 0)
        hba1c = labs.get("hba1c", 0)

        X = np.array([[alt, creatinine, hba1c]])
        X_scaled = self.scaler.transform(X)

        return {
            "liver_risk": round(
                self.liver_model.predict_proba(X_scaled)[0][1] * 100, 2
            ),
            "kidney_risk": round(
                self.kidney_model.predict_proba(X_scaled)[0][1] * 100, 2
            ),
            "diabetes_risk": round(
                self.diabetes_model.predict_proba(X_scaled)[0][1] * 100, 2
            )
        }

    # -------------------------------------
    # Feature Importance (Model-level)
    # -------------------------------------
    def feature_contributions(self, labs):
        importance = (
            self.liver_model.feature_importances_
            + self.kidney_model.feature_importances_
            + self.diabetes_model.feature_importances_
        ) / 3

        return [
            {
                "feature": feat,
                "impact": round(float(importance[i]), 3)
            }
            for i, feat in enumerate(self.features)
        ]

    # -------------------------------------
    # Counterfactual Clinical Insights (UPDATED)
    # -------------------------------------
    def explain_prediction(self, current_labs):
        results = []
        targets = {
            "alt": {"label": "ALT", "target": 35},
            "creatinine": {"label": "Creatinine", "target": 1.0},
            "hba1c": {"label": "HbA1c", "target": 5.4}
        }

        # 1. Get original risk for "What-If" baseline
        original_pred = self.predict(current_labs)

        for key, info in targets.items():
            curr = current_labs.get(key)
            if curr is None:
                continue

            # 2. Calculate "What-If" Impact
            modified_labs = current_labs.copy()
            modified_labs[key] = info["target"]
            new_pred = self.predict(modified_labs)
            
            risk_key = "diabetes_risk" if key == "hba1c" else ("kidney_risk" if key == "creatinine" else "liver_risk")
            reduction = original_pred[risk_key] - new_pred[risk_key]
            impact_text = f"If {info['label']} is reduced to {info['target']}, predicted disease risk may decrease by ~{round(abs(reduction), 2)}%."

            # 3. Unified logic for ALT, Creatinine, HbA1c
            thresholds = {
                "ALT": 35,
                "Creatinine": 1.0,
                "HbA1c": 5.7
            }

            label = info["label"]
            ideal = thresholds.get(label, info["target"])

            if curr >= ideal:
                severity = "Risk Indicator"
                interpretation = f"The patient's {label} is {round(curr/ideal,2)}x higher than recommended."

                # ---- Severity tiers ----
                if label == "ALT":
                    if curr > 1000:
                        severity = "Critical Acute Liver Injury"
                        interpretation = "ALT >1000 strongly suggests acute hepatocellular injury (viral hepatitis, toxin exposure, or ischemic damage)."
                    elif curr > 200:
                        severity = "Severe Liver Stress"
                        interpretation = "Significant hepatocellular injury detected."
                    elif curr > 40:
                        severity = "Mild Liver Enzyme Elevation"

                if label == "Creatinine":
                    if curr >= 2:
                        severity = "Severe Renal Dysfunction"
                        interpretation = "Creatinine suggests significant kidney impairment."
                    elif curr >= 1.3:
                        severity = "Moderate Renal Stress"
                        interpretation = "Possible early renal dysfunction."
                    elif curr >= 1.0:
                        severity = "Borderline Kidney Function"

                if label == "HbA1c":
                    if curr >= 6.5:
                        severity = "Diabetes Diagnostic Level"
                        interpretation = "HbA1c ≥ 6.5% is diagnostic of diabetes mellitus."
                    elif curr >= 5.7:
                        severity = "Prediabetes Risk"
                        interpretation = "HbA1c indicates increased diabetes risk."

                results.append({
                    "title": f"{label} {severity}",
                    "explanation": f"Current {label} level ({curr}) is above the healthy clinical value of {ideal}.",
                    "clinical_interpretation": interpretation,
                    "possible_causes": CAUSES.get(label, []),
                    "impact": impact_text,
                    "recommendations": [
                        f"Reduce {label} toward ideal value ({ideal})",
                        f"Repeat {label} testing during the next clinical visit",
                        "Monitor biomarker trends across visits",
                        "Consult physician for detailed clinical evaluation"
                    ],
                    "lab": label,
                    "current": curr,
                    "modified": ideal
                })

        return results

    # -------------------------------------
    # SHAP Explainability (Patient-specific)
    # -------------------------------------
    def shap_explain(self, labs):
        alt = labs.get("alt", 0)
        creatinine = labs.get("creatinine", 0)
        hba1c = labs.get("hba1c", 0)

        X = np.array([[alt, creatinine, hba1c]])
        X_scaled = self.scaler.transform(X)

        def get_pos_shap(explainer, data):
            vals = explainer.shap_values(data)
            return vals[1][0] if isinstance(vals, list) else vals[0]

        shap_vals = (
            get_pos_shap(self.liver_explainer, X_scaled)
            + get_pos_shap(self.kidney_explainer, X_scaled)
            + get_pos_shap(self.diabetes_explainer, X_scaled)
        ) / 3

        ranges = {
            "alt": "7-56 U/L",
            "creatinine": "0.6-1.3 mg/dL",
            "hba1c": "4.0-5.6%"
        }

        contributions = []
        for i, feature in enumerate(self.features):
            impact_val = round(float(shap_vals[i] * 100), 2)
            direction = "increases" if impact_val > 0 else "reduces"
            
            contributions.append({
                "feature": feature.upper(),
                "value": float(X[0][i]),
                "range": ranges.get(feature, ""),
                "impact": impact_val,
                "interpretation": (
                    f"A level of {X[0][i]} {direction} mortality risk by "
                    f"{abs(impact_val)}% relative to clinical baselines."
                )
            })

        return contributions


# -------------------------------------
# Trend Forecasting (Clinical Trajectory)
# -------------------------------------
def forecast_trend(values, steps=3):
    values = [v for v in values if v is not None]
    if len(values) < 2:
        return []

    x = np.arange(len(values))
    slope, intercept = np.polyfit(x, values, 1)

    forecast = []
    for i in range(1, steps + 1):
        future = intercept + slope * (len(values) + i - 1)
        forecast.append(round(max(0, future), 2))

    return forecast


# -------------------------------------
# Generate Graph Data
# -------------------------------------
def generate_trend_graph(history, lab):
    dates = []
    values = []

    for record in history:
        val = record.get(lab)
        if val is not None:
            dates.append(record.get("date", "Unknown"))
            values.append(val)

    forecast = forecast_trend(values)
    forecast_dates = [
        f"Forecast {i+1}"
        for i in range(len(forecast))
    ]

    return {
        "dates": dates + forecast_dates,
        "values": values + forecast
    }