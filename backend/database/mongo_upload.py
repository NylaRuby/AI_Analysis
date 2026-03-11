import os
import csv
from pymongo import MongoClient, UpdateOne

# ---------------- CONFIG ----------------
MONGO_URI = "mongodb+srv://naailahfirdous458_db_user:2NW4xUPAk4TCqk2Z@cluster0.f8co8gz.mongodb.net/?appName=Cluster0"

# ---------------- PATHS ----------------
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BACKEND_DIR, "data") # folder where multiple reports are uploaded

# ---------------- HELPERS ----------------
def find_csv_files():
    """Locate all CSV files in the uploads folder."""
    if not os.path.exists(DATA_DIR):
        print(f"❌ Uploads folder not found: {DATA_DIR}")
        return []
    return [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.lower().endswith(".csv")]

# ---------------- UPLOAD FUNCTION ----------------
def upload_incremental_data():
    csv_files = find_csv_files()
    if not csv_files:
        print("❌ No CSV files found in uploads folder. Exiting.")
        return

    try:
        client = MongoClient(MONGO_URI)
        db = client["mortality_risk_db"]
        collection = db["patients"]

        # Ensure unique index exists (patient_id + visit_number)
        collection.create_index([("patient_id", 1), ("visit_number", 1)], unique=True)

        total_inserted = 0
        total_skipped = 0

        for csv_path in csv_files:
            print(f"📄 Processing CSV: {csv_path}")
            inserted = 0
            skipped = 0
            batch_ops = []

            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                # Normalize headers
                if reader.fieldnames:
                    reader.fieldnames = [h.strip().lower().replace(" ", "_") for h in reader.fieldnames]

                for row in reader:
                    clean_row = {k.strip(): (v.strip() if v else None) for k, v in row.items() if k}

                    p_id = clean_row.get("patient_id", "")
                    v_num = clean_row.get("visit_number", "")

                    if not p_id or not v_num:
                        skipped += 1
                        continue

                    clean_row["patient_id"] = p_id.upper()  # keep IDs uppercase
                    clean_row["visit_number"] = v_num

                    batch_ops.append(
                        UpdateOne(
                            {"patient_id": clean_row["patient_id"], "visit_number": v_num},
                            {"$setOnInsert": clean_row},
                            upsert=True
                        )
                    )

            if batch_ops:
                result = collection.bulk_write(batch_ops)
                inserted = result.upserted_count
                skipped = len(batch_ops) - inserted

            total_inserted += inserted
            total_skipped += skipped
            print(f"✔ {os.path.basename(csv_path)}: Inserted {inserted}, Skipped {skipped}")

        print("\n" + "="*40)
        print("✅ TOTAL UPLOAD SUMMARY")
        print(f"New records inserted:  {total_inserted}")
        print(f"Existing records skipped: {total_skipped}")
        print(f"Total records in DB:      {collection.count_documents({})}")
        print("="*40)

    except Exception as e:
        print(f"❌ Critical Error during upload: {e}")


if __name__ == "__main__":
    upload_incremental_data()
