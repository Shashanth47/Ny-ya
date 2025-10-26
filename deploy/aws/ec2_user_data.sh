#!/bin/bash
set -euxo pipefail

# Tested on Ubuntu 22.04 LTS (Free Tier t3.micro/t2.micro)
# If using Amazon Linux 2023, replace apt commands with yum/dnf and set User=ec2-user in gunicorn.service.

# 1) Base packages
apt-get update -y
apt-get install -y python3 python3-venv python3-pip nginx git build-essential

# 2) App directory
APP_HOME=/opt/legal-ai-chatbot
mkdir -p "$APP_HOME"

# 3) Pull your repo code
# Replace REPO_URL with your Git URL, or copy files to the instance manually.
REPO_URL="REPLACE_WITH_YOUR_GIT_REPO_URL"
if [ "$REPO_URL" != "REPLACE_WITH_YOUR_GIT_REPO_URL" ]; then
  git clone "$REPO_URL" "$APP_HOME"
fi

# If you uploaded a zip via S3/EC2-Instance-Connect, ensure contents live in $APP_HOME
# and include requirements.txt, scripts/app.py, templates/chat.html, embeddings/ etc.

# 4) Python env + dependencies
python3 -m venv "$APP_HOME/.venv"
"$APP_HOME/.venv/bin/pip" install --upgrade pip
if [ -f "$APP_HOME/requirements.txt" ]; then
  "$APP_HOME/.venv/bin/pip" install -r "$APP_HOME/requirements.txt"
fi

# 5) Environment secrets (.env)
cat > "$APP_HOME/.env" <<'EOF'
TOGETHER_API_KEY=REPLACE_ME
EOF

# 6) Gunicorn start script
cat > "$APP_HOME/gunicorn_start.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
APP_HOME=/opt/legal-ai-chatbot
VENV=$APP_HOME/.venv
if [ -f "$APP_HOME/.env" ]; then
  set -a
  . "$APP_HOME/.env"
  set +a
fi
cd "$APP_HOME"
exec "$VENV/bin/gunicorn" \
  --workers 1 \
  --threads 2 \
  --bind 127.0.0.1:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  scripts.app:app
EOF
chmod +x "$APP_HOME/gunicorn_start.sh"

# 7) Systemd unit
cat > /etc/systemd/system/gunicorn.service <<'EOF'
[Unit]
Description=Legal AI Chatbot Gunicorn
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/legal-ai-chatbot
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/legal-ai-chatbot/gunicorn_start.sh
Restart=always
RestartSec=3
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

# 8) Nginx reverse proxy
cat > /etc/nginx/sites-available/legal-ai-chatbot <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120;
        proxy_connect_timeout 60;
    }
}
EOF
ln -sf /etc/nginx/sites-available/legal-ai-chatbot /etc/nginx/sites-enabled/legal-ai-chatbot
rm -f /etc/nginx/sites-enabled/default

# 9) Start services
systemctl daemon-reload
systemctl enable gunicorn
systemctl restart gunicorn
systemctl restart nginx

# 10) Optional: UFW (firewall) allow HTTP
if command -v ufw >/dev/null; then
  ufw allow 80 || true
fi