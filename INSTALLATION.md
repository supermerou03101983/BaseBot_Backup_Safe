# Installation du Base Trading Bot

Guide complet pour déployer le bot de trading sur un VPS.

## 🚀 Installation rapide (Une seule commande)

Sur votre VPS fraîchement installé, exécutez :

```bash
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash
```

C'est tout ! Le script va :
- ✅ Installer toutes les dépendances système (Python, git, etc.)
- ✅ Créer un utilisateur dédié `basebot`
- ✅ Cloner le repository GitHub
- ✅ Configurer l'environnement virtuel Python
- ✅ Installer toutes les dépendances Python
- ✅ Créer les services systemd (Scanner, Filter, Trader, Dashboard)
- ✅ Configurer le pare-feu
- ✅ Initialiser la base de données

## 📋 Prérequis

- VPS Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+, Fedora)
- Accès root (via SSH)
- Connexion Internet

## ⚙️ Configuration post-installation

### 1. Configurer les variables d'environnement

Éditez le fichier de configuration :

```bash
nano /home/basebot/trading-bot/config/.env
```

**Variables obligatoires à remplir :**

```env
# Wallet
WALLET_ADDRESS=0xVotreAdresse
PRIVATE_KEY=VotreCléPrivéeSans0x

# APIs
ETHERSCAN_API_KEY=VotreCléEtherscan
COINGECKO_API_KEY=VotreCléCoinGecko  # Optionnel
```

### 2. Démarrer les services

Démarrez tous les services d'un coup :

```bash
sudo /home/basebot/trading-bot/start_all_services.sh
```

Ou démarrez-les individuellement :

```bash
# Scanner - Détecte les nouveaux tokens
sudo systemctl enable basebot-scanner
sudo systemctl start basebot-scanner

# Filter - Filtre les tokens détectés
sudo systemctl enable basebot-filter
sudo systemctl start basebot-filter

# Trader - Execute les trades
sudo systemctl enable basebot-trader
sudo systemctl start basebot-trader

# Dashboard - Interface web
sudo systemctl enable basebot-dashboard
sudo systemctl start basebot-dashboard
```

### 3. Vérifier que tout fonctionne

```bash
# Statut de tous les services
systemctl status basebot-*

# Logs en temps réel
journalctl -u basebot-scanner -f    # Scanner
journalctl -u basebot-filter -f     # Filter
journalctl -u basebot-trader -f     # Trader
journalctl -u basebot-dashboard -f  # Dashboard
```

### 4. Accéder au Dashboard

Le dashboard est accessible sur le port 8501 :

```
http://VOTRE_IP_VPS:8501
```

## 🏗️ Architecture des services

```
┌──────────┐     ┌────────┐     ┌────────┐     ┌───────────┐
│ Scanner  │────▶│ Filter │────▶│ Trader │────▶│ Dashboard │
└──────────┘     └────────┘     └────────┘     └───────────┘
     │                │               │               │
     └────────────────┴───────────────┴───────────────┘
                       │
                  ┌────▼─────┐
                  │ Database │
                  │ SQLite   │
                  └──────────┘
```

### Rôle de chaque service :

1. **Scanner** - Détecte les nouveaux tokens sur Base Network
2. **Filter** - Analyse et filtre les tokens selon vos critères
3. **Trader** - Execute les achats/ventes automatiquement
4. **Dashboard** - Interface de monitoring et contrôle

## 🔧 Commandes utiles

### Gestion des services

```bash
# Démarrer tous
sudo ./start_all_services.sh

# Arrêter tous
sudo ./stop_all_services.sh

# Redémarrer un service
sudo systemctl restart basebot-scanner

# Voir les logs
journalctl -u basebot-scanner -f
journalctl -u basebot-filter -f
journalctl -u basebot-trader -f
journalctl -u basebot-dashboard -f
```

### Configuration

```bash
# Éditer la config
nano /home/basebot/trading-bot/config/.env

# Vérifier le statut du bot
su - basebot -c 'cd /home/basebot/trading-bot && ./status.sh'

# Voir la base de données
sqlite3 /home/basebot/trading-bot/data/trading.db
```

### Logs

```bash
# Logs des services
tail -f /home/basebot/trading-bot/logs/scanner.log
tail -f /home/basebot/trading-bot/logs/filter.log
tail -f /home/basebot/trading-bot/logs/trader.log
tail -f /home/basebot/trading-bot/logs/dashboard.log

# Logs d'erreur
tail -f /home/basebot/trading-bot/logs/scanner_error.log
tail -f /home/basebot/trading-bot/logs/filter_error.log
tail -f /home/basebot/trading-bot/logs/trader_error.log
tail -f /home/basebot/trading-bot/logs/dashboard_error.log
```

## 🔒 Sécurité

- ✅ Le bot tourne sous un utilisateur dédié `basebot` (non-root)
- ✅ Le fichier `.env` a les permissions 600 (lecture seule par le propriétaire)
- ✅ Les services redémarrent automatiquement en cas de crash
- ✅ Les clés privées ne sont jamais loggées

**⚠️ IMPORTANT :**
- Ne commitez JAMAIS votre fichier `.env`
- Sauvegardez votre clé privée en lieu sûr
- Commencez en mode `paper` (simulation) pour tester
- Utilisez un wallet dédié au bot avec des montants limités

## 📊 Monitoring

### Dashboard web

Accédez à `http://VOTRE_IP:8501` pour :
- Voir les performances en temps réel
- Monitorer les positions actives
- Consulter l'historique des trades
- Ajuster les paramètres

### Ligne de commande

```bash
# Voir le statut rapide
su - basebot -c 'cd /home/basebot/trading-bot && ./status.sh'

# Statistiques de la base de données
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT COUNT(*) FROM scanned_tokens"
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT COUNT(*) FROM approved_tokens"
```

## 🛠️ Maintenance

### Sauvegarde

```bash
# Sauvegarder la base de données
cp /home/basebot/trading-bot/data/trading.db /home/basebot/trading-bot/backups/trading_$(date +%Y%m%d).db

# Sauvegarder la config
cp /home/basebot/trading-bot/config/.env /home/basebot/trading-bot/backups/.env_$(date +%Y%m%d)
```

### Mise à jour du bot

```bash
# Arrêter les services
sudo systemctl stop basebot-*

# Mettre à jour le code
su - basebot -c "cd /home/basebot/trading-bot && git pull"

# Mettre à jour les dépendances si nécessaire
su - basebot -c "source /home/basebot/trading-bot/venv/bin/activate && pip install -r /home/basebot/trading-bot/requirements.txt --upgrade"

# Redémarrer les services
sudo systemctl start basebot-*
```

### Nettoyage des logs

```bash
# Nettoyer les vieux logs (garder 30 derniers jours)
find /home/basebot/trading-bot/logs -name "*.log" -type f -mtime +30 -delete
```

## 🐛 Troubleshooting

### Un service ne démarre pas

```bash
# Voir les erreurs détaillées
journalctl -u basebot-scanner -n 100 --no-pager

# Vérifier la config
python3 /home/basebot/trading-bot/src/config_manager.py

# Vérifier les permissions
ls -la /home/basebot/trading-bot/config/.env
```

### Le dashboard n'est pas accessible

```bash
# Vérifier que le service tourne
systemctl status basebot-dashboard

# Vérifier le port
netstat -tlnp | grep 8501

# Vérifier le pare-feu
sudo ufw status
```

### Problèmes de connexion RPC

```bash
# Tester la connexion
curl -X POST https://mainnet.base.org \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

## 📞 Support

- GitHub Issues : https://github.com/supermerou03101983/BaseBot/issues
- Documentation complète : Voir le README.md dans le repo

## 📜 Licence

Consultez le fichier LICENSE dans le repository.

---

**⚠️ Disclaimer:** Ce bot est fourni à titre éducatif. Le trading de cryptomonnaies comporte des risques. Utilisez-le à vos propres risques.
