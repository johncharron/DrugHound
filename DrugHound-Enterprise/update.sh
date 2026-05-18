#!/bin/bash
# DrugHound Enterprise - Update Script

set -e

APP_DIR="/opt/drughound"

echo "🔄 Updating DrugHound Enterprise..."

cd $APP_DIR

# Pull latest changes
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements-enterprise.txt

# Restart service
systemctl restart drughound

# Check status
sleep 3
if systemctl is-active --quiet drughound; then
    echo "✅ Update successful! Service is running."
    echo "📊 Service status:"
    systemctl status drughound --no-pager -l
else
    echo "❌ Update failed. Check logs:"
    journalctl -u drughound -n 50
    exit 1
fi
