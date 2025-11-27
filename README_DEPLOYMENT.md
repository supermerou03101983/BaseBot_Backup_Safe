# 🚀 Déploiement BaseBot en 1 Commande

## Installation Automatique (Recommandé)

### Prérequis
- VPS Ubuntu 20.04+ / Debian 11+ / CentOS 8+ / RHEL 8+ / Fedora 35+
- Accès root (sudo)
- Connexion Internet

### Installation en 1 commande

```bash
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash
```

**C'est tout !** 🎉

Le script va automatiquement:
- ✅ Installer toutes les dépendances système
- ✅ Créer l'utilisateur `basebot`
- ✅ Cloner le repository
- ✅ Configurer l'environnement Python (venv)
- ✅ Installer tous les packages Python
- ✅ Créer la structure de fichiers
- ✅ Initialiser la base de données
- ✅ **Nettoyer les fichiers de logs (fix permissions)**
- ✅ Créer les 4 services systemd
- ✅ Configurer le pare-feu

---

## Configuration Post-Installation

### 1. Configurer le fichier .env

```bash
nano /home/basebot/trading-bot/config/.env
```

**Variables critiques à modifier:**

```bash
# Clé privée de votre wallet
PRIVATE_KEY=0xVOTRE_CLE_PRIVEE_ICI

# RPC Base Network (choisir le plus fiable)
RPC_URL=https://base.drpc.org
# OU
RPC_URL=https://mainnet.base.org
# OU
RPC_URL=https://base-rpc.publicnode.com

# Optionnel: Clés API pour meilleure fiabilité
ETHERSCAN_API_KEY=votre_cle_etherscan
COINGECKO_API_KEY=votre_cle_coingecko
```

⚠️ **IMPORTANT:**
- Utiliser un wallet **dédié au bot** (pas votre wallet principal)
- Commencer avec un **petit montant** pour tester
- Ne **jamais** partager votre clé privée
- Ne **jamais** commit le fichier .env dans git

---

### 2. Démarrer les services

```bash
# Scanner (découverte de tokens)
systemctl enable basebot-scanner
systemctl start basebot-scanner

# Filter (analyse et filtrage)
systemctl enable basebot-filter
systemctl start basebot-filter

# Trader (trading automatique)
systemctl enable basebot-trader
systemctl start basebot-trader

# Dashboard (interface web)
systemctl enable basebot-dashboard
systemctl start basebot-dashboard
```

**OU en une seule commande:**

```bash
bash /home/basebot/trading-bot/start_all_services.sh
```

---

### 3. Vérifier le bon fonctionnement

```bash
# Statut des services
systemctl status basebot-scanner
systemctl status basebot-filter
systemctl status basebot-trader
systemctl status basebot-dashboard

# Logs en temps réel
journalctl -u basebot-scanner -f

# Vérifier les tokens découverts
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT COUNT(*) FROM discovered_tokens;"

# Accéder au dashboard
# Ouvrir dans le navigateur: http://VOTRE_IP_VPS:8501
```

---

## Test de Validation Automatique

Après l'installation, exécuter le script de test :

```bash
bash /home/basebot/trading-bot/test_deploy.sh
```

Ce script vérifie:
- ✅ Structure des fichiers
- ✅ Permissions correctes
- ✅ Base de données initialisée
- ✅ Environnement Python
- ✅ Services systemd
- ✅ Configuration .env

**Résultat attendu:**
```
✅ Tous les tests sont passés !
Tests réussis: 35
Tests échoués: 0
```

---

## Troubleshooting

### Problème: Scanner ne démarre pas

**Symptôme:**
```
systemctl status basebot-scanner
# Active: failed
```

**Solution:**

```bash
# Vérifier les logs détaillés
journalctl -u basebot-scanner -n 100

# Problème courant: Permissions logs
rm -f /home/basebot/trading-bot/logs/*.log
chown -R basebot:basebot /home/basebot/trading-bot
systemctl restart basebot-scanner
```

**Guide complet:** [TROUBLESHOOTING_SCANNER.md](TROUBLESHOOTING_SCANNER.md)

---

### Problème: Aucun token découvert

**Symptôme:**
```bash
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT COUNT(*) FROM discovered_tokens;"
# Résultat: 0
```

**Solution:**

```bash
# Vérifier les logs
tail -50 /home/basebot/trading-bot/logs/scanner.log

# Problème courant: PRIVATE_KEY non configurée
nano /home/basebot/trading-bot/config/.env
# Vérifier que PRIVATE_KEY != "votre_private_key"

# Redémarrer
systemctl restart basebot-scanner
```

---

### Problème: git pull échoue (repo privé)

**Symptôme:**
```
git pull
# fatal: detected dubious ownership
```

**Solution:**

```bash
# Se connecter en tant que basebot
su - basebot
cd trading-bot
git pull
```

**Guide complet:** [FIX_GIT_OWNERSHIP.md](FIX_GIT_OWNERSHIP.md)

---

## Architecture du Système

```
┌─────────────────────────────────────────────────────────┐
│                     Base Network                        │
│              (Blockchain Layer 2 d'Ethereum)            │
└────────────▲─────────────────────────▲──────────────────┘
             │                         │
             │ RPC Calls               │ DexScreener API
             │                         │
┌────────────┴─────────────────────────┴──────────────────┐
│                   Scanner Service                        │
│  - Scan nouveaux tokens (DexScreener API)               │
│  - Récupère infos on-chain (Web3)                       │
│  - Enregistre dans discovered_tokens                    │
│  - Fréquence: toutes les 30s                            │
└────────────┬─────────────────────────────────────────────┘
             │
             │ discovered_tokens
             ▼
┌─────────────────────────────────────────────────────────┐
│                    Filter Service                        │
│  - Analyse les tokens découverts                        │
│  - Applique critères de filtrage                        │
│  - Approuve ou rejette                                  │
│  - Tables: approved_tokens, rejected_tokens             │
└────────────┬─────────────────────────────────────────────┘
             │
             │ approved_tokens
             ▼
┌─────────────────────────────────────────────────────────┐
│                    Trader Service                        │
│  - Trade les tokens approuvés                           │
│  - Gestion positions (buy/sell)                         │
│  - Trailing stop multi-niveaux                          │
│  - Time-based exits                                     │
│  - Table: trade_history                                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  Dashboard Service                       │
│  - Interface web Streamlit                              │
│  - Visualisation données                                │
│  - Statistiques temps réel                              │
│  - Port: 8501                                           │
└─────────────────────────────────────────────────────────┘
```

---

## Fichiers de Configuration

### Structure des fichiers

```
/home/basebot/trading-bot/
├── config/
│   ├── .env                    # Configuration principale ⚠️
│   ├── .env.example            # Template
│   ├── trading_mode.json       # Mode trading (paper/live)
│   └── blacklist.json          # Tokens blacklistés
├── src/
│   ├── Scanner.py              # Service Scanner
│   ├── Filter.py               # Service Filter
│   ├── Trader.py               # Service Trader
│   ├── Dashboard.py            # Service Dashboard
│   ├── web3_utils.py           # Utilitaires Web3
│   └── init_database.py        # Init base de données
├── data/
│   ├── trading.db              # Base de données SQLite
│   └── backups/                # Backups DB
├── logs/
│   ├── scanner.log             # Logs Scanner
│   ├── filter.log              # Logs Filter
│   ├── trader.log              # Logs Trader
│   └── dashboard.log           # Logs Dashboard
├── venv/                       # Environnement Python
├── deploy.sh                   # Script déploiement ✅
├── test_deploy.sh              # Script test ✅
└── requirements.txt            # Dépendances Python
```

---

## Commandes Utiles

### Gestion des services

```bash
# Démarrer tous les services
bash /home/basebot/trading-bot/start_all_services.sh

# Arrêter tous les services
bash /home/basebot/trading-bot/stop_all_services.sh

# Redémarrer un service spécifique
systemctl restart basebot-scanner

# Voir les logs en temps réel
journalctl -u basebot-scanner -f
tail -f /home/basebot/trading-bot/logs/scanner.log
```

### Base de données

```bash
# Ouvrir la DB
sqlite3 /home/basebot/trading-bot/data/trading.db

# Compter les tokens découverts
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT COUNT(*) FROM discovered_tokens;"

# Voir les derniers tokens
sqlite3 /home/basebot/trading-bot/data/trading.db "
SELECT token_address, symbol, name, market_cap, created_at
FROM discovered_tokens
ORDER BY created_at DESC
LIMIT 10;
"

# Voir les tokens approuvés
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT * FROM approved_tokens;"

# Voir l'historique de trading
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT * FROM trade_history ORDER BY timestamp DESC LIMIT 10;"
```

### Mise à jour du code

```bash
# Se connecter en tant que basebot
su - basebot
cd trading-bot

# Mettre à jour
git pull

# Sortir
exit

# Redémarrer les services
systemctl restart basebot-scanner basebot-filter basebot-trader
```

---

## Mode Trading

### Mode Paper (Simulation) - Par défaut

Le bot démarre en mode **paper** (simulation) :
- ✅ Aucun trade réel
- ✅ Test de la stratégie sans risque
- ✅ Enregistrement des trades simulés

```bash
# Vérifier le mode
cat /home/basebot/trading-bot/config/trading_mode.json
# {"mode": "paper"}
```

### Mode Live (Production)

⚠️ **ATTENTION:** Ne passer en mode live qu'après validation complète en paper !

```bash
# Passer en mode live
echo '{"mode": "live"}' > /home/basebot/trading-bot/config/trading_mode.json

# Redémarrer le Trader
systemctl restart basebot-trader
```

---

## Monitoring

### Dashboard Web

Accéder au dashboard :
```
http://VOTRE_IP_VPS:8501
```

Le dashboard affiche :
- 📊 Tokens découverts
- ✅ Tokens approuvés
- ❌ Tokens rejetés
- 💰 Historique de trading
- 📈 Statistiques

### Logs

```bash
# Tous les logs en temps réel
journalctl -u basebot-* -f

# Logs d'un service spécifique
journalctl -u basebot-scanner -f

# Logs applicatifs
tail -f /home/basebot/trading-bot/logs/scanner.log
tail -f /home/basebot/trading-bot/logs/trader.log
```

---

## Sécurité

### ✅ Bonnes pratiques

- ✅ Utiliser un wallet dédié au bot
- ✅ Commencer en mode **paper** (simulation)
- ✅ Tester avec un **petit montant** d'abord
- ✅ Configurer des **alertes** (Telegram optionnel)
- ✅ **Sauvegarder** régulièrement la base de données
- ✅ **Surveiller** les logs quotidiennement
- ✅ **Mettre à jour** le code régulièrement

### ❌ À ne jamais faire

- ❌ Partager votre PRIVATE_KEY
- ❌ Commit le fichier .env dans git
- ❌ Utiliser votre wallet principal
- ❌ Passer en mode live sans tests
- ❌ Ignorer les erreurs dans les logs

---

## Support et Documentation

### Documentation disponible

| Fichier | Contenu |
|---------|---------|
| [FIXES_APPLIED.md](FIXES_APPLIED.md) | Liste complète des correctifs |
| [TROUBLESHOOTING_SCANNER.md](TROUBLESHOOTING_SCANNER.md) | Guide troubleshooting |
| [NEXT_STEPS.md](NEXT_STEPS.md) | Actions immédiates |
| [DIAGNOSTIC_TOOLS.md](DIAGNOSTIC_TOOLS.md) | Outils de diagnostic |
| [INSTALL_MANUEL.md](INSTALL_MANUEL.md) | Installation manuelle |

### Scripts de diagnostic

```bash
# Diagnostic complet Scanner
bash /home/basebot/trading-bot/diagnose_scanner.sh

# Test Python détaillé
python /home/basebot/trading-bot/test_scanner_simple.py

# Test déploiement complet
bash /home/basebot/trading-bot/test_deploy.sh
```

---

## Changelog

### Version 1.1.0 (2025-11-07)

✅ **Correctifs appliqués:**
- Fix #1: Scanner - Correction appel get_token_info()
- Fix #2: Permissions fichiers de logs (deploy.sh)
- Fix #3: Schéma DB harmonisé (token_address, exit_time)
- Fix #4: DexScreener API - Ajout get_recent_pairs_on_chain()

✅ **Nouveautés:**
- Script de test automatique (test_deploy.sh)
- Documentation complète des fixes
- Outils de diagnostic
- Guide troubleshooting

✅ **Statut:** Production Ready

---

## Exemple de Session Complète

```bash
# 1. Installation (1 commande)
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash

# 2. Configuration
nano /home/basebot/trading-bot/config/.env
# Modifier PRIVATE_KEY et RPC_URL

# 3. Test
bash /home/basebot/trading-bot/test_deploy.sh

# 4. Démarrage
bash /home/basebot/trading-bot/start_all_services.sh

# 5. Monitoring
journalctl -u basebot-scanner -f

# 6. Vérification tokens
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT COUNT(*) FROM discovered_tokens;"

# 7. Dashboard
# Ouvrir: http://VOTRE_IP_VPS:8501
```

---

**Dernière mise à jour:** 2025-11-07
**Version:** 1.1.0
**Statut:** ✅ Production Ready
**Installation:** ⚡ 1 commande
