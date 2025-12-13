FROM python:3.10-slim

WORKDIR /app

# Install only the small runtime deps needed by the consumer
RUN pip install --no-cache-dir kafka-python pymongo python-dotenv

# Copy the consumer script and name it kafka_consumer.py inside the image
COPY consumer.py ./consumer.py

ENV PYTHONUNBUFFERED=1

CMD ["python", "consumer.py"]
