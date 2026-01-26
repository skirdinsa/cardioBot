#!/bin/bash
#
# SSL certificate renewal script for CardioBot
# Run this periodically (e.g., via cron) to keep certificates valid
#
# Cron example (run every day at 3am):
# 0 3 * * * /path/to/cardioBot/renew-ssl.sh >> /var/log/ssl-renew.log 2>&1
#

set -e

cd "$(dirname "$0")"

echo "=== SSL Certificate Renewal $(date) ==="

# Find domain from existing certificate
DOMAIN=$(ls certbot/conf/live/ 2>/dev/null | head -1)

if [ -z "$DOMAIN" ]; then
    echo "No existing certificates found. Run init-ssl.sh first."
    exit 1
fi

echo "Renewing certificate for: $DOMAIN"

# Renew certificate
docker run --rm \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    certbot/certbot renew --quiet

# Copy updated certificates
cp "certbot/conf/live/$DOMAIN/fullchain.pem" ssl/certs/
cp "certbot/conf/live/$DOMAIN/privkey.pem" ssl/private/

# Reload nginx
docker compose exec nginx nginx -s reload

echo "Certificate renewal complete."
