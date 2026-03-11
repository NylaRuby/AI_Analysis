import os
import time
import pandas as pd
from pymongo import MongoClient
from extract_reports_to_csv import extract_lab_values as extract_pdf_to_dict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WATCH_FOLDER = os.path.join(BASE_DIR, "patient_submissions")
os.makedirs(WATCH_FOLDER, exist_ok=True)

CSV_FILE = r"C:\Users\Naseeruddin\Desktop\Naailah\mortality_risk_project\data\patients_data.csv"

MONGO_URI = "mongodb+srv://naailahfirdous458_db_user:2NW4xUPAk4TCqk2Z@cluster0.f8co8gz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(MONGO_URI)

db = client["mortality_risk_db"]

patients_col = db["patients"]


def process_new_files():

    print("Background Processor started...")

    processed_files = set()

    while True:

        for patient_name in os.listdir(WATCH_FOLDER):

            patient_path = os.path.join(WATCH_FOLDER, patient_name)

            if not os.path.isdir(patient_path):
                continue

            for filename in os.listdir(patient_path):

                file_path = os.path.join(patient_path, filename)

                if file_path in processed_files:
                    continue

                print(f"Processing {filename}")

                try:

                    pdf_data = extract_pdf_to_dict(file_path)

                    visit_data = {
                        "date": pdf_data.get("test_date"),
                        "ALT": pdf_data.get("ALT"),
                        "Creatinine": pdf_data.get("Creatinine"),
                        "Hemoglobin": pdf_data.get("hemoglobin")
                    }

                    patients_col.update_one(
                        {"patient_id": patient_name},
                        {
                            "$set": {"patient_name": pdf_data.get("patient_name")},
                            "$push": {"history": visit_data}
                        },
                        upsert=True
                    )

                    df = pd.read_csv(CSV_FILE) if os.path.exists(CSV_FILE) else pd.DataFrame()

                    new_df = pd.DataFrame([pdf_data])

                    df = pd.concat([df, new_df], ignore_index=True)

                    df.to_csv(CSV_FILE, index=False)

                    processed_files.add(file_path)

                    print("Saved to MongoDB + CSV")

                except Exception as e:

                    print("Error:", e)

        time.sleep(5)


if __name__ == "__main__":
    process_new_files()
