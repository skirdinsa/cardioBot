FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create volume mount point for credentials
VOLUME ["/app/credentials"]

# Run the bot
CMD ["python", "bot.py"]
