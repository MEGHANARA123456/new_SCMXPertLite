#consumer.py
from kafka import KafkaConsumer
from pymongo import MongoClient
import json
import os
from dotenv import load_dotenv
import time
load_dotenv()


import os
from kafka.errors import NoBrokersAvailable

# Bootstrap servers: use environment variable or default to the compose service name
BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')

# Create Kafka consumer with retry loop while broker starts
consumer = None
attempt = 0
while True:
    try:
        consumer = KafkaConsumer(
            'test_topic',
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        print(f"Connected to Kafka brokers at {BOOTSTRAP_SERVERS}")
        break
    except NoBrokersAvailable:
        attempt += 1
        wait = min(2 * attempt, 30)
        print(f"Kafka brokers not available yet (attempt {attempt}). Retrying in {wait}s...")
        time.sleep(wait)

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.iot_data
collection = db.sensor_readings
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB_IOT")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

# Main IoT collection
device_data_collection = db["sensor_readings"]

print("Kafka consumer started. Waiting for messages...")

for message in consumer:
    data = message.value
    device_data_collection.insert_one(data)
    collection.insert_one(data)
    print(f"Inserted into MongoDB: {data}")