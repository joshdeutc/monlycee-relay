#!/usr/bin/env bash
# ==============================================================================
# Script de déploiement automatique sur Ubuntu (Oracle Cloud Always Free)
# Usage: chmod +x setup_oracle.sh && sudo ./setup_oracle.sh
# ==============================================================================

set -e

echo "=== [1/6] Configuration de la mémoire Swap (2 Go) ==="
# Indispensable sur VM Micro 1 Go de RAM pour empêcher Chromium de crasher
if ! grep -q "swapfile" /etc/fstab; then
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "Swap de 2 Go activé avec succès."
else
    echo "Swap déjà configuré."
fi

echo "=== [2/6] Mise à jour du système et installation des outils ==="
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git curl ufw

echo "=== [3/6] Préparation de l'environnement virtuel Python ==="
APP_DIR="/opt/monlycee-relay"
mkdir -p "$APP_DIR"
cp server.py requirements.txt "$APP_DIR/" 2>/dev/null || true

cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [4/6] Installation de Playwright et des dépendances graphiques ==="
playwright install chromium
playwright install-deps

echo "=== [5/6] Configuration du service systemd (Démarrage automatique) ==="
cat << 'EOF' > /etc/systemd/system/monlycee-relay.service
[Unit]
Description=MonLycee Auth Relay Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/monlycee-relay
ExecStart=/opt/monlycee-relay/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable monlycee-relay
systemctl restart monlycee-relay

echo "=== [6/6] Vérification du statut du service ==="
sleep 2
systemctl status monlycee-relay --no-pager

echo ""
echo "=================================================================="
echo "  DÉPLOIEMENT TERMINÉ AVEC SUCCÈS !"
echo "  Le serveur tourne en local sur 127.0.0.1:8000"
echo "  Prochaine étape recommandée : Lancer un tunnel Cloudflare gratuit :"
echo "    curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
echo "    sudo dpkg -i cloudflared.deb"
echo "    cloudflared tunnel --url http://127.0.0.1:8000"
echo "=================================================================="
