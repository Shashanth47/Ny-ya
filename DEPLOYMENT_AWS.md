# Deploying legal-ai-chatbot on AWS Free Tier (EC2 + Nginx + Gunicorn)

This guide shows how to deploy your Flask app within the AWS Free Tier using a single EC2 instance, Nginx, and Gunicorn. No load balancer or managed services are required.

## Prerequisites
- AWS account with Free Tier eligibility.
- Together API key (billing via Together, not AWS). Put it in `.env`.
- Your project files, including `embeddings/` directory and `requirements.txt`.
- Optional: a public Git repo or a zip archive to upload to EC2.

## Architecture
- `EC2` (Ubuntu t3.micro/t2.micro) hosting the app.
- `Gunicorn` runs Flask (`scripts.app:app`) on `127.0.0.1:8000`.
- `Nginx` reverse proxies port `80` → `127.0.0.1:8000`.
- `.env` holds `TOGETHER_API_KEY` loaded by the app at runtime.

## Security Group
- Inbound: allow `HTTP (80)` from `0.0.0.0/0`.
- Inbound: allow `SSH (22)` only from your IP (recommended).
- Optional: allow `HTTPS (443)` if you later enable TLS.

## Launch EC2
1. Open `EC2 → Instances → Launch Instance`.
2. Name: `legal-ai-chatbot`.
3. AMI: `Ubuntu Server 22.04 LTS`.
4. Instance type: `t3.micro` (Free Tier) or `t2.micro`.
5. Key pair: create/select one.
6. Network: attach the security group above.
7. Storage: `20–30 GB` `gp3` EBS.
8. User data: paste the script in `deploy/aws/ec2_user_data.sh` and edit `REPO_URL`.

> Note: The user-data script assumes your repo is accessible by Git. If it isn’t, you can upload the files manually after the instance boots.

## Prepare the App on EC2
Option A — via Git (easiest):
- Set `REPO_URL` in `deploy/aws/ec2_user_data.sh` to your Git URL before launch.
- Ensure repo contains `requirements.txt`, `scripts/app.py`, `templates/chat.html`, and `embeddings/`.

Option B — manual upload:
- Launch the instance.
- Use `EC2 Instance Connect` or `scp` to copy the project into `/opt/legal-ai-chatbot`.
- Create venv and install deps:
  - `python3 -m venv /opt/legal-ai-chatbot/.venv`
  - `/opt/legal-ai-chatbot/.venv/bin/pip install -r /opt/legal-ai-chatbot/requirements.txt`
- Put your secrets in `/opt/legal-ai-chatbot/.env`:
  - `TOGETHER_API_KEY=YOUR_KEY`
- Install service and proxy:
  - Copy `deploy/aws/gunicorn_start.sh` to `/opt/legal-ai-chatbot/` and `chmod +x` it.
  - Copy `deploy/aws/gunicorn.service` to `/etc/systemd/system/` and run:
    - `sudo systemctl daemon-reload`
    - `sudo systemctl enable gunicorn`
    - `sudo systemctl restart gunicorn`
  - Copy `deploy/aws/nginx.conf` to `/etc/nginx/sites-available/legal-ai-chatbot`, then:
    - `sudo ln -sf /etc/nginx/sites-available/legal-ai-chatbot /etc/nginx/sites-enabled/legal-ai-chatbot`
    - `sudo rm -f /etc/nginx/sites-enabled/default`
    - `sudo nginx -t && sudo systemctl restart nginx`

## Validating
- Visit `http://<EC2_PUBLIC_IP>/` in your browser. You should see Nyāya’s chat UI.
- Test `/ask` with a JSON POST to confirm structured output and citations.
- Logs:
  - App: `sudo journalctl -u gunicorn -f`
  - Nginx: `sudo tail -f /var/log/nginx/error.log`

## Embeddings & Performance
- Keep `embeddings/` prebuilt locally and include it in the repo to avoid heavy compute on EC2.
- Use `all-MiniLM-L6-v2` for query embedding; it runs CPU-only and fits micro instances.
- Gunicorn:
  - `--workers 1`, `--threads 2`, `--timeout 120` — suitable for Free Tier.

## HTTPS (Optional)
- Point a domain to the EC2 public IP using your DNS provider (or Route 53).
- Install certs using `certbot` for Nginx if you need HTTPS.

## Cost Notes
- EC2 Free Tier provides 750 hours/month for 12 months.
- EBS: keep disk small (20–30 GB) and clean old artifacts.
- Together API usage is billed by Together; monitor per their dashboard.

## Troubleshooting
- 502/504 from Nginx: check `gunicorn` is running: `systemctl status gunicorn`.
- 401 from Together: ensure `TOGETHER_API_KEY` is set in `.env` and readable.
- Empty citations: ensure `embeddings/` files exist and `faiss_index.index` was built.

## Files Provided
- `deploy/aws/ec2_user_data.sh` — bootstrap script for Ubuntu EC2.
- `deploy/aws/gunicorn_start.sh` — starts Gunicorn for the app.
- `deploy/aws/gunicorn.service` — systemd unit to manage the app.
- `deploy/aws/nginx.conf` — reverse proxy config.
- `.env.sample` — template for secrets.