FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
COPY consumer.py .

CMD ["python", "consumer.py"]
