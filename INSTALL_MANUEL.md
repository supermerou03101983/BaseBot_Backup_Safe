# Installation manuelle du Base Trading Bot

Si le repository GitHub est privé, utilisez cette méthode d'installation manuelle.

## Sur votre VPS

### Étape 1 : Connectez-vous en tant que root

```bash
ssh root@votre-vps
```

### Étape 2 : Téléchargez le script de déploiement

Copiez le contenu du fichier `deploy.sh` et créez-le sur le VPS :

```bash
# Créer le fichier
nano /tmp/deploy.sh

# Collez tout le contenu de deploy.sh
# Sauvegardez avec Ctrl+X, puis Y, puis Enter
```

### Étape 3 : Rendez-le exécutable et lancez-le

```bash
chmod +x /tmp/deploy.sh
bash /tmp/deploy.sh
```

---

## Alternative : Installation via Git Clone direct

Si vous avez configuré une clé SSH ou un token GitHub :

### Avec SSH (si configuré)

```bash
# En tant que root
sudo su

# Installation des dépendances de base
apt-get update && apt-get install -y git python3 python3-pip python3-venv

# Créer l'utilisateur
useradd -m -s /bin/bash basebot

# Cloner le repo (remplacez par votre méthode d'auth)
su - basebot -c "git clone git@github.com:supermerou03101983/BaseBot.git /home/basebot/trading-bot"

# Ensuite suivre les étapes manuelles
cd /home/basebot/trading-bot
su - basebot -c "python3 -m venv venv"
su - basebot -c "source venv/bin/activate && pip install -r requirements.txt"
su - basebot -c "source venv/bin/activate && python src/init_database.py"

# Configurer le .env
nano config/.env
# Remplir vos clés

# Créer les services systemd manuellement...
```

### Avec Token GitHub

```bash
# Cloner avec token
git clone https://TOKEN@github.com/supermerou03101983/BaseBot.git /home/basebot/trading-bot

# Puis suivre les étapes ci-dessus
```

---

## Script d'installation simplifié (sans curl)

Créez ce fichier sur votre VPS :

```bash
cat > /tmp/quick_install.sh << 'EOFSCRIPT'
#!/bin/bash
set -e

echo "🚀 Installation rapide BaseBot..."

# Vérifier root
if [[ $EUID -ne 0 ]]; then
   echo "Ce script doit être exécuté en tant que root"
   exit 1
fi

# Mettre à jour et installer dépendances
echo "📦 Installation des dépendances..."
apt-get update -qq
apt-get install -y -qq git python3 python3-pip python3-venv python3-dev \
    build-essential libssl-dev libffi-dev sqlite3 curl wget

# Créer l'utilisateur
echo "👤 Création de l'utilisateur basebot..."
useradd -m -s /bin/bash basebot 2>/dev/null || echo "Utilisateur existe déjà"

# Demander la méthode de clonage
echo ""
echo "Comment voulez-vous cloner le repository ?"
echo "1) SSH (si configuré)"
echo "2) HTTPS avec token"
echo "3) Téléchargement manuel (déjà fait)"
read -p "Choix [1-3]: " choice

case $choice in
    1)
        read -p "URL SSH (git@github.com:user/repo.git): " repo_url
        su - basebot -c "git clone $repo_url /home/basebot/trading-bot"
        ;;
    2)
        read -p "Entrez votre token GitHub: " token
        su - basebot -c "git clone https://$token@github.com/supermerou03101983/BaseBot.git /home/basebot/trading-bot"
        ;;
    3)
        if [ ! -d "/home/basebot/trading-bot" ]; then
            echo "❌ Erreur: Le répertoire /home/basebot/trading-bot n'existe pas"
            echo "Uploadez d'abord les fichiers sur le VPS"
            exit 1
        fi
        chown -R basebot:basebot /home/basebot/trading-bot
        ;;
    *)
        echo "Choix invalide"
        exit 1
        ;;
esac

BOT_DIR="/home/basebot/trading-bot"
cd $BOT_DIR

# Créer les répertoires
echo "📁 Création des répertoires..."
su - basebot -c "mkdir -p $BOT_DIR/{logs,data,data/backups,backups,config}"

# Environnement virtuel
echo "🐍 Configuration Python..."
su - basebot -c "python3 -m venv $BOT_DIR/venv"
su - basebot -c "source $BOT_DIR/venv/bin/activate && pip install --upgrade pip setuptools wheel"
su - basebot -c "source $BOT_DIR/venv/bin/activate && pip install -r $BOT_DIR/requirements.txt"

# Base de données
echo "🗄️ Initialisation de la base de données..."
su - basebot -c "source $BOT_DIR/venv/bin/activate && python $BOT_DIR/src/init_database.py"

# Services
echo "⚙️ Création des services systemd..."

# Scanner
cat > /etc/systemd/system/basebot-scanner.service << EOF
[Unit]
Description=BaseBot Trading Scanner
After=network.target

[Service]
Type=simple
User=basebot
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$BOT_DIR/venv/bin/python $BOT_DIR/src/Scanner.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Filter
cat > /etc/systemd/system/basebot-filter.service << EOF
[Unit]
Description=BaseBot Trading Filter
After=network.target

[Service]
Type=simple
User=basebot
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$BOT_DIR/venv/bin/python $BOT_DIR/src/Filter.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Trader
cat > /etc/systemd/system/basebot-trader.service << EOF
[Unit]
Description=BaseBot Trading Trader
After=network.target

[Service]
Type=simple
User=basebot
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$BOT_DIR/venv/bin/python $BOT_DIR/src/Trader.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Dashboard
cat > /etc/systemd/system/basebot-dashboard.service << EOF
[Unit]
Description=BaseBot Trading Dashboard
After=network.target

[Service]
Type=simple
User=basebot
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$BOT_DIR/venv/bin/streamlit run $BOT_DIR/src/Dashboard.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

echo ""
echo "✅ Installation terminée !"
echo ""
echo "📝 Étapes suivantes :"
echo "1. Configurez le fichier .env : nano $BOT_DIR/config/.env"
echo "2. Démarrez les services :"
echo "   systemctl enable basebot-scanner"
echo "   systemctl start basebot-scanner"
echo "   systemctl enable basebot-filter"
echo "   systemctl start basebot-filter"
echo "   systemctl enable basebot-trader"
echo "   systemctl start basebot-trader"
echo "   systemctl enable basebot-dashboard"
echo "   systemctl start basebot-dashboard"
echo ""
echo "3. Vérifiez les logs :"
echo "   journalctl -u basebot-scanner -f"
echo ""
EOFSCRIPT

chmod +x /tmp/quick_install.sh
bash /tmp/quick_install.sh
```

---

## Vérification après installation

```bash
# Vérifier les services
systemctl status basebot-scanner
systemctl status basebot-filter
systemctl status basebot-trader
systemctl status basebot-dashboard

# Vérifier les logs
journalctl -u basebot-scanner -n 50
journalctl -u basebot-filter -n 50
journalctl -u basebot-trader -n 50

# Accéder au dashboard
# http://VOTRE_IP_VPS:8501
```

---

## ⚠️ Important

Une fois le repository rendu public, vous pourrez utiliser la commande originale :

```bash
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash
```

C'est la méthode recommandée et la plus simple !
