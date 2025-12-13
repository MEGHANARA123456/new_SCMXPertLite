'''import os
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Load .env file
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_APP")

if not MONGO_URI:
    raise Exception("ERROR: MONGO_URI not found in .env")

if not DB_NAME:
    raise Exception("ERROR: MONGO_DB_APP not found in .env")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

collections = ["admin_requests", "admin_replies"]  # collections to fix

print("Converting ObjectIds to string IDs...\n")

for col_name in collections:
    col = db[col_name]
    docs = list(col.find({}))

    print(f"Processing collection: {col_name}  ({len(docs)} documents)")

    for doc in docs:
        old_id = doc["_id"]

        # Only convert if it is ObjectId
        if isinstance(old_id, ObjectId):
            new_id = str(old_id)

            # Delete old doc and insert new one
            doc["_id"] = new_id
            col.delete_one({"_id": old_id})
            col.insert_one(doc)

            print(f"✔ Converted {old_id} → {new_id}")

print("\nDONE! All ObjectIds converted to string IDs.")'''
