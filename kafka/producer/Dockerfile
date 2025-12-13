FROM python:3.10-slim

WORKDIR /app

# Install only the small runtime deps needed by the producer
RUN pip install --no-cache-dir kafka-python python-dotenv

# Copy the producer script and name it kafka_producer.py inside the image
COPY producer.py ./producer.py

ENV PYTHONUNBUFFERED=1

CMD ["python", "producer.py"]
