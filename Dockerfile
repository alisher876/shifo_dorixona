FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY main.py .

# Set environment variables (optional: you can set them in Koyeb or VPS instead)
ENV BOT_TOKEN=""
ENV ADMIN_ID=""

# Run bot
CMD ["python", "main.py"]
