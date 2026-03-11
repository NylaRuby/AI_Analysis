from pymongo import MongoClient

# Replace with your MongoDB Atlas connection string
MONGO_URI = "mongodb+srv://naailahfirdous458_db_user:2NW4xUPAk4TCqk2Z@cluster0.f8co8gz.mongodb.net/?appName=Cluster0"

# Connect to MongoDB
client = MongoClient(MONGO_URI)

# Create / use a database
db = client["mortality_risk_db"]

# Create / use a collection
collection = db["patients_test"]

# Test insert
test_doc = {"name": "test_patient", "age": 99}
result = collection.insert_one(test_doc)

print(f"Inserted document ID: {result.inserted_id}")

# Test read
doc = collection.find_one({"name": "test_patient"})
print("Retrieved document:", doc)
