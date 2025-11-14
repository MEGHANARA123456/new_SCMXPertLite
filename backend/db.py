"""Database configuration and collection helpers."""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

if not MONGO_URI or not MONGO_DB:
    raise RuntimeError("MONGO_URI and MONGO_DB must be set in .env file")

# Create a shared client for the application
try:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
except Exception as e:
    raise RuntimeError(f"Failed to connect to MongoDB: {e}")


def get_collections():
    """Return a dict of common collections."""
    return {
        "shipments": db["shipments"],
        "device_data": db["device_data"],
        "users": db["users"],
    }
