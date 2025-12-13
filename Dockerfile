FROM python:3.13
WORKDIR /app
# Install curl for Heroku release phase streaming logs
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Make release script executable
RUN chmod +x release-tasks.sh
EXPOSE 5000
