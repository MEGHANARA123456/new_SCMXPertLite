#!/usr/bin/env python3
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import sys

sys.path.insert(0, 'd:\\scmxpertlite')
from backend.user import pbkdf2_verify, verify_and_migrate_password

load_dotenv()

client = MongoClient(os.getenv('MONGO_URI'))
db = client[os.getenv('MONGO_DB_APP')]
users = db['user']

user = users.find_one({'username': 'meghana'})
if user:
    pwd_hash = user.get('password', '')
    print(f'Password hash exists: {bool(pwd_hash)}')
    print(f'Hash preview: {pwd_hash[:60] if pwd_hash else "EMPTY"}')
    print(f'Hash starts with pbkdf2: {pwd_hash.startswith("pbkdf2") if pwd_hash else "N/A"}')
    
    # Test password verification
    test_pwd = 'Meghan@123'
    result = verify_and_migrate_password(user, test_pwd)
    print(f'Password verification for "{test_pwd}": {result}')
    
    # Also test direct pbkdf2 verification
    if pwd_hash.startswith('pbkdf2'):
        direct_result = pbkdf2_verify(pwd_hash, test_pwd)
        print(f'Direct pbkdf2 verification: {direct_result}')
else:
    print('User not found')
