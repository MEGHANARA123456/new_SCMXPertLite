#!/usr/bin/env python3
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import sys

sys.path.insert(0, 'd:\\scmxpertlite')

from backend.user import pbkdf2_hash

load_dotenv()

client = MongoClient(os.getenv('MONGO_URI'))
db = client[os.getenv('MONGO_DB_APP')]
users = db['user']

# Create hash for password "Meghan@123"
password_hash = pbkdf2_hash("Meghan@123")
print(f"Password hash: {password_hash[:80]}...")

# Update all meghana users with this hash
result = users.update_many(
    {'username': 'meghana'},
    {'$set': {'password': password_hash, 'role': 'admin'}}
)
print(f"Updated {result.modified_count} meghana user(s)")

# Verify
user = users.find_one({'username': 'meghana'})
print(f"Verification - Password set: {bool(user.get('password'))}")
print(f"Role: {user.get('role', 'user')}")
