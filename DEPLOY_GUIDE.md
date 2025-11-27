# 🚀 GUIDE DE DÉPLOIEMENT - VPS FRAIS

## ✅ TOUT EST PRÊT SUR GITHUB!

Tous les outils de monitoring et déblocage sont maintenant intégrés au script de déploiement automatique.

---

## 📋 CE QUI SERA INSTALLÉ AUTOMATIQUEMENT

### **Composants principaux:**
- ✅ Scanner, Filter, Trader, Dashboard
- ✅ Base de données SQLite
- ✅ Services systemd avec auto-restart
- ✅ Environnement virtuel Python

### **Nouveaux outils de monitoring (NOUVEAU!):**
- ✅ **Watchdog anti-freeze** - Vérifie toutes les 15 minutes
- ✅ **Diagnostic complet** - `bot-status`
- ✅ **Dépannage rapide** - `bot-fix`
- ✅ **Fermeture d'urgence** - `bot-emergency`
- ✅ **Analyse de performance** - `bot-analyze`

### **Tâches automatiques configurées:**
- ✅ Backup quotidien (2h du matin)
- ✅ Maintenance hebdo (Dimanche 3h)
- ✅ Maintenance mensuelle (1er du mois 4h)
- ✅ **Watchdog anti-freeze (Toutes les 15 minutes)** ⬅️ NOUVEAU!

---

## 🎯 DÉPLOIEMENT EN UNE COMMANDE

### **Sur votre VPS frais (Ubuntu/Debian):**

```bash
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash
```

**Durée estimée:** 5-10 minutes

---

## ⚙️ ÉTAPES POST-INSTALLATION (OBLIGATOIRES)

### **1. Configurer vos clés API et wallet**

```bash
sudo nano /home/basebot/trading-bot/config/.env
```

**Remplissez au minimum:**
- `WALLET_ADDRESS=votre_adresse`
- `PRIVATE_KEY=votre_clé_privée_sans_0x`
- `ETHERSCAN_API_KEY=votre_clé` (optionnel mais recommandé)

**Sauvegarder:** `Ctrl+O` puis `Enter`, puis `Ctrl+X`

---

### **2. Démarrer les services**

```bash
# Activer auto-démarrage
sudo systemctl enable basebot-scanner
sudo systemctl enable basebot-filter
sudo systemctl enable basebot-trader
sudo systemctl enable basebot-dashboard

# Démarrer maintenant
sudo systemctl start basebot-scanner
sudo systemctl start basebot-filter
sudo systemctl start basebot-trader
sudo systemctl start basebot-dashboard
```

---

### **3. Vérifier que tout tourne**

```bash
# Vérifier les services
sudo systemctl status basebot-scanner
sudo systemctl status basebot-filter
sudo systemctl status basebot-trader
sudo systemctl status basebot-dashboard
```

Vous devriez voir **"active (running)"** en vert.

---

## 🛡️ OUTILS DE MONITORING (AUTOMATIQUEMENT INSTALLÉS)

Une fois connecté en tant que `basebot`, vous avez accès à ces commandes:

```bash
# Devenir l'utilisateur basebot
su - basebot
# Ou: sudo -u basebot -i

# Commandes disponibles:
bot-status      # Diagnostic complet (freeze, positions, logs)
bot-fix         # Dépannage rapide
bot-restart     # Redémarrer le trader
bot-logs        # Voir les 50 dernières lignes
bot-watch       # Suivre les logs en temps réel
bot-emergency   # Fermeture d'urgence des positions
bot-analyze     # Analyser les performances de trading
```

---

## 📊 ACCÉDER AU DASHBOARD

**URL:** `http://IP_DE_VOTRE_VPS:8501`

Pour trouver l'IP:
```bash
hostname -I | awk '{print $1}'
```

Puis ouvrez dans votre navigateur: `http://XX.XX.XX.XX:8501`

---

## 🔍 VÉRIFICATION POST-DÉPLOIEMENT (CHECKLIST)

```bash
# 1. Vérifier que les services tournent
sudo systemctl status basebot-* --no-pager

# 2. Vérifier les logs (aucune erreur critique)
sudo journalctl -u basebot-scanner -n 20 --no-pager
sudo journalctl -u basebot-filter -n 20 --no-pager
sudo journalctl -u basebot-trader -n 20 --no-pager

# 3. Vérifier la base de données
su - basebot -c 'sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT COUNT(*) FROM discovered_tokens;"'

# 4. Vérifier que le watchdog est configuré
su - basebot -c 'crontab -l | grep watchdog'
# Devrait afficher: */15 * * * * /home/basebot/trading-bot/watchdog.py

# 5. Test du diagnostic
su - basebot -c 'cd /home/basebot/trading-bot && python3 diagnose_freeze.py'
```

---

## 🚨 EN CAS DE PROBLÈME

### **Si un service ne démarre pas:**

```bash
# Voir les logs d'erreur détaillés
sudo journalctl -u basebot-trader -n 100 --no-pager

# Vérifier la config
sudo nano /home/basebot/trading-bot/config/.env

# Redémarrer après modification
sudo systemctl restart basebot-trader
```

---

### **Si le bot freeze (positions bloquées):**

```bash
# 1. Devenir basebot
su - basebot

# 2. Diagnostic
bot-status

# 3. Dépannage rapide
bot-fix

# 4. Si ça ne suffit pas, redémarrer
bot-restart

# 5. En dernier recours, fermeture d'urgence
bot-emergency
```

---

## 📁 STRUCTURE DES FICHIERS

```
/home/basebot/trading-bot/
├── src/                      # Code source
│   ├── Scanner.py
│   ├── Filter.py
│   ├── Trader.py
│   └── Dashboard.py
├── config/
│   ├── .env                  # CONFIGURATION (À REMPLIR!)
│   ├── trading_mode.json
│   └── blacklist.json
├── data/
│   ├── trading.db            # Base de données
│   └── backups/              # Backups automatiques
├── logs/                     # Logs de tous les services
│   ├── trading.log
│   ├── watchdog.log
│   └── maintenance.log
├── diagnose_freeze.py        # Diagnostic freeze
├── emergency_close_positions.py  # Fermeture urgence
├── watchdog.py               # Monitoring auto
├── quick_fix.sh              # Dépannage rapide
├── analyze_trades_simple.py  # Analyse performance
└── TROUBLESHOOTING_FREEZE.md # Guide complet
```

---

## 🔐 SÉCURITÉ

### **Fichier .env protégé:**
- Permissions: `600` (lecture/écriture propriétaire uniquement)
- Propriétaire: `basebot:basebot`
- **JAMAIS commit sur GitHub!**

### **Backup de votre clé privée:**
```bash
# Sauvegarder ailleurs (PAS sur le VPS!)
cat /home/basebot/trading-bot/config/.env | grep PRIVATE_KEY
```

Conservez cette clé dans un gestionnaire de mots de passe sécurisé!

---

## 📈 MONITORING CONTINU

### **Dashboard temps réel:**
- URL: `http://VPS_IP:8501`
- Rafraîchissement auto

### **Logs en direct:**
```bash
# Scanner
sudo journalctl -u basebot-scanner -f

# Filter
sudo journalctl -u basebot-filter -f

# Trader (le plus important!)
sudo journalctl -u basebot-trader -f

# Dashboard
sudo journalctl -u basebot-dashboard -f
```

### **Watchdog automatique:**
- Vérifie toutes les 15 minutes
- Logs: `/home/basebot/trading-bot/logs/watchdog.log`
- Alertes si freeze >30 min
- Alertes si positions bloquées >48h

---

## 🎯 COMMANDES RAPIDES (AIDE-MÉMOIRE)

```bash
# SERVICES
sudo systemctl status basebot-trader    # Statut
sudo systemctl restart basebot-trader   # Redémarrer
sudo systemctl stop basebot-trader      # Arrêter
sudo systemctl start basebot-trader     # Démarrer

# LOGS
bot-logs        # 50 dernières lignes
bot-watch       # Temps réel
bot-trader      # Logs service trader

# DIAGNOSTIC
bot-status      # Diagnostic complet
bot-fix         # Dépannage rapide

# URGENCE
bot-emergency   # Fermeture positions
bot-restart     # Redémarrage trader

# ANALYSE
bot-analyze     # Performance trading
```

---

## 📞 SUPPORT

### **Logs de déploiement:**
```bash
cat /var/log/basebot-deployment.log
```

### **Guide de dépannage freeze:**
```bash
cat /home/basebot/trading-bot/TROUBLESHOOTING_FREEZE.md
```

### **Quickstart:**
```bash
cat /home/basebot/README_QUICKSTART.txt
```

---

## ✅ CHECKLIST FINALE

Avant de laisser tourner en production:

- [ ] Config .env remplie avec vos clés
- [ ] Tous les services `active (running)`
- [ ] Dashboard accessible sur port 8501
- [ ] Scanner découvre des tokens (check logs)
- [ ] Filter approuve/rejette des tokens
- [ ] Mode `paper` activé pour tester
- [ ] Watchdog configuré (crontab -l)
- [ ] Backup quotidien configuré (crontab -l)
- [ ] Test de `bot-status` réussi
- [ ] Clé privée sauvegardée ailleurs

---

## 🎉 C'EST PARTI!

**Mode Paper:** Le bot est maintenant en simulation, zéro risque!

**Surveillance:** Le watchdog vérifie automatiquement toutes les 15 minutes.

**Prochaine étape:** Laissez tourner 24-48h en mode paper, puis analysez:
```bash
bot-analyze
```

**Passage en mode REAL:** Seulement après validation complète!

```bash
# Éditer .env
sudo nano /home/basebot/trading-bot/config/.env
# Changer: TRADING_MODE=paper → TRADING_MODE=real

# Redémarrer le trader
sudo systemctl restart basebot-trader
```

---

**Bon trading! 🚀**

*Tous les outils de monitoring et déblocage sont maintenant intégrés au déploiement automatique.*
