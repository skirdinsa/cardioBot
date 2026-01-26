#!/bin/bash
#
# SSL certificate initialization script for CardioBot
# Uses Let's Encrypt with certbot
#
# Usage: ./init-ssl.sh your-domain.com your-email@example.com
#

set -e

DOMAIN=$1
EMAIL=$2

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "Usage: $0 <domain> <email>"
    echo "Example: $0 cardio.example.com admin@example.com"
    exit 1
fi

echo "=== SSL Certificate Setup for $DOMAIN ==="

# Create directories
mkdir -p ssl/certs ssl/private certbot/www certbot/conf

# Check if certificates already exist
if [ -f "ssl/certs/fullchain.pem" ] && [ -f "ssl/private/privkey.pem" ]; then
    echo "Certificates already exist. To renew, delete ssl/ directory first."
    exit 0
fi

# Generate self-signed certificate for initial nginx startup
echo "Generating temporary self-signed certificate..."
openssl req -x509 -nodes -newkey rsa:2048 \
    -days 1 \
    -keyout ssl/private/privkey.pem \
    -out ssl/certs/fullchain.pem \
    -subj "/CN=$DOMAIN"

echo "Starting nginx with temporary certificate..."
docker compose up -d nginx

# Wait for nginx to start
sleep 5

# Get Let's Encrypt certificate
echo "Obtaining Let's Encrypt certificate..."
docker run --rm \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

# Copy certificates to ssl directory
echo "Installing certificates..."
cp "certbot/conf/live/$DOMAIN/fullchain.pem" ssl/certs/
cp "certbot/conf/live/$DOMAIN/privkey.pem" ssl/private/

# Restart nginx with real certificates
echo "Restarting nginx with Let's Encrypt certificate..."
docker compose restart nginx

echo ""
echo "=== SSL Setup Complete ==="
echo "Your Mini App is now available at: https://$DOMAIN"
echo ""
echo "Don't forget to:"
echo "1. Set WEBAPP_URL=https://$DOMAIN in your .env file"
echo "2. Configure this URL in BotFather for your Mini App"
echo ""
echo "To renew certificates, run: ./renew-ssl.sh"
