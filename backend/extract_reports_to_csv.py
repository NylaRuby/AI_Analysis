import os
import re
import csv
import PyPDF2

UPLOADS_PATH = r"C:\Users\Naseeruddin\Desktop\Naailah\mortality_risk_project\backend\uploads"
OUTPUT_CSV = r"C:\Users\Naseeruddin\Desktop\Naailah\mortality_risk_project\data\patients_data.csv"


def extract_lab_values(pdf_path):

    lab_data = {}

    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)

            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"

        lines = text.splitlines()

        for line in lines:

            line = line.strip()

            match = re.search(r"([A-Za-z /]+)\s+([-+]?\d*\.?\d+)", line)

            if match:

                name_part = match.group(1).strip().lower()
                value = float(match.group(2))

                # Map important biomarkers
                if "hemoglobin" in name_part:
                    test_name = "Hemoglobin"

                elif "creatinine" in name_part:
                    test_name = "Creatinine"

                elif "alt" in name_part or "sgpt" in name_part:
                    test_name = "ALT"

                else:
                    test_name = name_part.replace("-", "_").replace(" ", "_")

                lab_data[test_name] = value

    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")

    return lab_data


all_patients_data = []

if not os.path.exists(UPLOADS_PATH):
    print(f"Error: Uploads path does not exist: {UPLOADS_PATH}")

else:

    for patient_name in os.listdir(UPLOADS_PATH):

        patient_folder = os.path.join(UPLOADS_PATH, patient_name)

        if os.path.isdir(patient_folder):

            for report_file in sorted(os.listdir(patient_folder)):

                if report_file.lower().endswith(".pdf"):

                    visit = report_file.split("(")[0].replace("v", "").strip()

                    date_match = re.search(r"\((\d{2}/\d{2}/\d{2,4})\)", report_file)
                    date = date_match.group(1) if date_match else ""

                    pdf_path = os.path.join(patient_folder, report_file)

                    lab_values = extract_lab_values(pdf_path)

                    row = {
                        "patient_id": patient_name,
                        "visit": visit,
                        "date": date
                    }

                    row.update(lab_values)

                    all_patients_data.append(row)


columns_set = set()

for row in all_patients_data:
    columns_set.update(row.keys())

base_cols = ["patient_id", "visit", "date"]

other_cols = sorted([c for c in columns_set if c not in base_cols])

final_columns = base_cols + other_cols


os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:

    writer = csv.DictWriter(f, fieldnames=final_columns)

    writer.writeheader()

    for row in all_patients_data:
        writer.writerow(row)


print(f"✅ CSV created successfully at: {OUTPUT_CSV}")
