from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime, date, timezone
import os 
from dotenv import load_dotenv  

 # from motor.motor_asyncio import AsyncIOMotorClient
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_APP")
 
client:MongoClient = None # type: ignore
db = None

async def connect_db():
    global client, db
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        
        # 👇 This actually tests the connection
        client.admin.command("ping")
        
        db = client[DB_NAME]  # type: ignore
        print("  MongoDB Connection Confirmed!")
        
    except ServerSelectionTimeoutError:
        print("  Connection FAILED: Could not reach MongoDB server (timeout).")
        raise
    except ConnectionFailure as e:
        print(f"  Connection FAILED: {e}")
        raise


async def close_db():
    global client
    if client:
        client.close()
        print(" MongoDB connection closed.")


def get_db():
    if db is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return db