#!/bin/bash
# DrugHound Enterprise - Complete Deployment Script

set -e

echo "=========================================="
echo "🐕 DrugHound Enterprise Deployment"
echo "=========================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# Variables
APP_DIR="/opt/drughound"
DOMAIN="${1:-localhost}"

echo "📦 Installing system dependencies..."
apt update
apt install -y python3-pip python3-venv nginx git curl

echo "🐍 Setting up Python environment..."
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-enterprise.txt
pip install gunicorn uvicorn

echo "📁 Creating directories..."
mkdir -p data logs static

echo "⚙️ Setting up systemd service..."
cat > /etc/systemd/system/drughound.service << 'SERVICEFILE'
[Unit]
Description=DrugHound Enterprise Drug Discovery Platform
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/drughound
Environment="PATH=/opt/drughound/venv/bin"
Environment="ENVIRONMENT=production"
ExecStart=/opt/drughound/venv/bin/gunicorn app_production:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000 --timeout 120
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEFILE

systemctl daemon-reload
systemctl enable drughound
systemctl start drughound

echo "🌐 Configuring Nginx..."
cat > /etc/nginx/sites-available/drughound << 'NGINX'
server {
    listen 80;
    server_name _;
    
    client_max_body_size 10M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/drughound /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo "✅ Deployment Complete!"
echo "=========================================="
echo "🌐 Access your DrugHound instance at:"
echo "   http://$DOMAIN/dashboard"
echo "   http://$DOMAIN/knowledge-graph"
echo ""
echo "📊 Service management:"
echo "   systemctl status drughound"
echo "   systemctl restart drughound"
echo "   journalctl -u drughound -f"
echo "=========================================="
