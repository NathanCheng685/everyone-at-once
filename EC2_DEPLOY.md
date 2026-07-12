# Deploy EveryoneAtOnce on AWS EC2

This guide is for the production web app only. It serves the Flask app and
precomputed `infer_table_*.npz` files. It does not run the LLM simulator and
does not need a GPU.

## Current app shape

- Runtime: Flask + Gunicorn
- Static UI: `web/`
- Production dependencies: `requirements-railway.txt`
- Health check: `/api/langs`
- Memory: use at least 1 GB RAM; 2 GB is safer for the current 8 tables
  (`friends`, `harry-potter`, `avengers`, `naruto` in English and Chinese).

## Recommended EC2 setup

Use the AWS Console unless you already have AWS CLI configured.

1. Open EC2 and launch an instance.
2. AMI: Ubuntu Server 24.04 LTS, x86_64.
3. Instance type: `t3.small` or larger. `t3.micro` may work, but 1 GB RAM is
   tight once Nginx, Python, and all tables are loaded.
4. Storage: 16 GB gp3 is enough for the app and logs.
5. Key pair: create/download a `.pem` key and keep it private.
6. Security group inbound rules:
   - SSH TCP 22 from your own IP only.
   - HTTP TCP 80 from anywhere.
   - HTTPS TCP 443 from anywhere.
7. Allocate an Elastic IP and associate it with the instance. Use this static
   IP for DNS records.

## Server install

SSH into the instance:

```bash
ssh -i ~/.ssh/eao-ec2.pem ubuntu@YOUR_ELASTIC_IP
```

Install OS packages:

```bash
sudo apt update
sudo apt install -y git nginx python3 python3-venv python3-pip snapd
```

Create an app user and clone the repo:

```bash
sudo useradd --system --create-home --home-dir /opt/eao --shell /usr/sbin/nologin eao
sudo mkdir -p /opt/eao
sudo chown ubuntu:ubuntu /opt/eao
git clone https://github.com/NathanCheng685/everyone-at-once.git /opt/eao/app
cd /opt/eao/app
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-railway.txt
sudo chown -R eao:eao /opt/eao/app
```

Smoke test before running it as a service:

```bash
sudo -u eao /opt/eao/app/.venv/bin/gunicorn app:app \
  --bind 127.0.0.1:8000 --workers 1 --threads 4 --timeout 120
```

In another SSH tab:

```bash
curl http://127.0.0.1:8000/api/langs
```

Stop the foreground Gunicorn process after the smoke test.

## systemd service

Copy `ops/eao.service` to the server:

```bash
sudo cp /opt/eao/app/ops/eao.service /etc/systemd/system/eao.service
sudo systemctl daemon-reload
sudo systemctl enable --now eao
sudo systemctl status eao
curl http://127.0.0.1:8000/api/langs
```

Useful service commands:

```bash
sudo journalctl -u eao -f
sudo systemctl restart eao
```

## Nginx reverse proxy

Before HTTPS, replace `YOUR_DOMAIN` in `ops/nginx-eao.conf`:

```bash
sudo cp /opt/eao/app/ops/nginx-eao.conf /etc/nginx/sites-available/eao
sudo sed -i 's/YOUR_DOMAIN/everyoneatonce.com/g' /etc/nginx/sites-available/eao
sudo ln -s /etc/nginx/sites-available/eao /etc/nginx/sites-enabled/eao
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

At this point, `http://YOUR_DOMAIN` should proxy to the app after DNS points at
the Elastic IP.

## Domain and DNS

Buy the domain from either:

- Route 53: easiest if you want AWS to manage registration and DNS together.
- Cloudflare or Namecheap: often nicer domain UX; then point DNS to the EC2
  Elastic IP.

Route 53 checklist:

1. Route 53 -> Registered domains -> Register domain.
2. Route 53 -> Hosted zones -> create a hosted zone for the domain if one was
   not created automatically.
3. In the hosted zone, create the `A` records below.
4. In Registered domains, confirm the domain's name servers match the hosted
   zone `NS` records. If they do not match, update the domain's name servers.

DNS records:

```text
A      @      YOUR_ELASTIC_IP
A      www    YOUR_ELASTIC_IP
```

If your registrar uses a full host name, use:

```text
A      everyoneatonce.com        YOUR_ELASTIC_IP
A      www.everyoneatonce.com    YOUR_ELASTIC_IP
```

Wait for DNS to resolve:

```bash
dig +short everyoneatonce.com
dig +short www.everyoneatonce.com
```

## HTTPS

After DNS resolves to the EC2 Elastic IP, install Certbot and issue a free
Let's Encrypt certificate:

```bash
sudo snap install core
sudo snap refresh core
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot
sudo certbot --nginx -d everyoneatonce.com -d www.everyoneatonce.com
sudo certbot renew --dry-run
```

## Update deployment

For future changes:

```bash
cd /opt/eao/app
sudo -u eao git pull --ff-only
sudo -u eao /opt/eao/app/.venv/bin/pip install -r requirements-railway.txt
sudo systemctl restart eao
curl http://127.0.0.1:8000/api/langs
```

## Troubleshooting

- `502 Bad Gateway`: check `sudo systemctl status eao` and
  `sudo journalctl -u eao -n 100`.
- App exits on boot: memory may be too low; move to `t3.small` or bigger.
- Domain works on HTTP but HTTPS fails: confirm DNS points to the Elastic IP
  before running Certbot.
- SSH blocked: security group SSH rule should allow your current public IP.
