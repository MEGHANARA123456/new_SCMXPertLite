#producer.py
from kafka import KafkaProducer
import json
import time
import random

import os
from kafka.errors import NoBrokersAvailable

# Bootstrap servers: use environment variable or default to the compose service name
BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')

# Create Kafka producer with a retry loop while broker is starting
producer = None
attempt = 0
while True:
    try:
        producer = KafkaProducer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print(f"Connected to Kafka brokers at {BOOTSTRAP_SERVERS}")
        break
    except NoBrokersAvailable:
        attempt += 1
        wait = min(2 * attempt, 30)
        print(f"Kafka brokers not available yet (attempt {attempt}). Retrying in {wait}s...")
        time.sleep(wait)

route = ['Newyork,USA', 'Chennai, India', 'Bengaluru, India', 'London,UK']

while True:
    routefrom = random.choice(route)
    routeto = random.choice(route)

    if routefrom != routeto:
        data = {
            "Battery_Level": round(random.uniform(2.0, 5.0), 2),
            "Device_ID": random.randint(1150, 1158),
            "First_Sensor_temperature": round(random.uniform(10, 40.0), 1),
            "Route_From": routefrom,
            "Route_To": routeto
        }

        # send to Kafka topic 'est_topic'
        producer.send('test_topic', value=data)
        producer.flush()   # optional, but good while debugging

        print(f"Sent to Kafka: {data}")
        time.sleep(10)