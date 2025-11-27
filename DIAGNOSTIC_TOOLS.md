# Outils de diagnostic Scanner

Ce dossier contient plusieurs outils de diagnostic pour identifier et résoudre les problèmes du Scanner.

## 📋 Fichiers disponibles

### 1. **NEXT_STEPS.md**
Guide rapide avec les actions immédiates à effectuer.

**Quand l'utiliser:** En premier, pour savoir quoi faire maintenant.

**Contenu:**
- Actions immédiates (4 étapes)
- Scénarios probables et solutions
- Timeline de diagnostic (15 min)
- Checklist de résolution

---

### 2. **diagnose_scanner.sh**
Script Bash automatique qui teste tous les composants du système.

**Quand l'utiliser:** Pour obtenir un diagnostic complet en 1 commande.

**Comment l'utiliser:**
```bash
cd /home/basebot/trading-bot
bash diagnose_scanner.sh
```

**Ce qu'il teste:**
- ✅ Statut du service systemd
- ✅ Logs systemd (journalctl)
- ✅ Logs applicatifs (scanner.log, scanner_error.log)
- ✅ Permissions des fichiers
- ✅ Configuration .env (sans exposer les secrets)
- ✅ Base de données SQLite
- ✅ Imports Python (web3, requests, etc.)
- ✅ Connexion RPC au blockchain
- ✅ Processus en cours

**Sortie:** Rapport texte avec ✅ (OK), ⚠️ (Warning), ❌ (Erreur)

---

### 3. **test_scanner_simple.py**
Script Python qui teste chaque composant individuellement.

**Quand l'utiliser:** Quand le diagnostic Bash ne suffit pas, ou pour identifier précisément où le problème se situe.

**Comment l'utiliser:**
```bash
su - basebot
cd /home/basebot/trading-bot
source venv/bin/activate
python test_scanner_simple.py
```

**Ce qu'il teste (dans l'ordre):**
1. Environnement Python (version, paths)
2. Chargement du fichier .env
3. Import des modules Python
4. Connexion Web3 au RPC
5. API DexScreener (appel réel)
6. Base de données SQLite (tables, données)
7. Permissions d'écriture dans logs/
8. Initialisation du Scanner (sans le lancer)

**Sortie:** Rapport détaillé avec traceback des erreurs Python

---

### 4. **TROUBLESHOOTING_SCANNER.md**
Documentation exhaustive de tous les problèmes possibles et leurs solutions.

**Quand l'utiliser:** Pour comprendre en détail un problème spécifique.

**Contenu:**
- Causes possibles (6 scénarios)
- Diagnostic étape par étape (7 étapes)
- Solutions aux problèmes courants (6 solutions)
- Workflow de diagnostic complet
- Exemples de logs normaux vs anormaux

---

## 🚀 Workflow recommandé

### Option A: Diagnostic rapide (5 minutes)

```bash
# 1. Lire les prochaines étapes
cat NEXT_STEPS.md

# 2. Exécuter le diagnostic automatique
bash diagnose_scanner.sh

# 3. Identifier les ❌ et corriger
# (Suivre les instructions dans NEXT_STEPS.md)

# 4. Relancer le Scanner
systemctl restart basebot-scanner
journalctl -u basebot-scanner -f
```

---

### Option B: Diagnostic approfondi (15 minutes)

```bash
# 1. Diagnostic système complet
bash diagnose_scanner.sh > diagnostic_system.txt 2>&1

# 2. Test Python détaillé
su - basebot -c "cd /home/basebot/trading-bot && source venv/bin/activate && python test_scanner_simple.py" > diagnostic_python.txt 2>&1

# 3. Analyser les deux rapports
cat diagnostic_system.txt
cat diagnostic_python.txt

# 4. Consulter le guide de troubleshooting
cat TROUBLESHOOTING_SCANNER.md

# 5. Appliquer les corrections nécessaires

# 6. Relancer
systemctl restart basebot-scanner
journalctl -u basebot-scanner -f
```

---

### Option C: Test manuel direct (2 minutes)

Pour tester rapidement sans script:

```bash
# Arrêter le service
systemctl stop basebot-scanner

# Lancer manuellement pour voir les logs en direct
su - basebot
cd /home/basebot/trading-bot
source venv/bin/activate
python src/Scanner.py

# Observer les logs pendant 30-60 secondes
# Ctrl+C pour arrêter

# Relancer le service
exit  # Sortir de la session basebot
systemctl start basebot-scanner
```

---

## 🔍 Problèmes courants - Référence rapide

| Symptôme | Cause probable | Solution rapide |
|----------|----------------|-----------------|
| Service démarre mais aucun log | Logs en buffer | Ajouter `PYTHONUNBUFFERED=1` au service |
| "PRIVATE_KEY not configured" | .env non configuré | Éditer `/home/basebot/trading-bot/config/.env` |
| "Connection refused" | RPC inaccessible | Changer `RPC_URL` dans .env |
| "Permission denied" sur logs/ | Ownership incorrect | `chown -R basebot:basebot /home/basebot/trading-bot` |
| "no such table: discovered_tokens" | DB non initialisée | `python src/init_database.py` |
| "database is locked" | Accès concurrent | Normal, réessaie automatique |
| Silence pendant 30s+ | Attente entre scans | Normal, attendre ou réduire `SCAN_INTERVAL_SECONDS` |

---

## 📊 Commandes de monitoring

### Logs en temps réel:
```bash
journalctl -u basebot-scanner -f
```

### Logs applicatifs:
```bash
tail -f /home/basebot/trading-bot/logs/scanner.log
```

### Statut du service:
```bash
systemctl status basebot-scanner
```

### Processus en cours:
```bash
ps aux | grep Scanner.py
```

### Dernières lignes de la DB:
```bash
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT token_address, symbol, created_at FROM discovered_tokens ORDER BY created_at DESC LIMIT 10;"
```

---

## 🛠️ Corrections fréquentes

### Fix 1: Désactiver le buffering des logs

```bash
nano /etc/systemd/system/basebot-scanner.service

# Ajouter dans [Service]:
Environment="PYTHONUNBUFFERED=1"

# Recharger:
systemctl daemon-reload
systemctl restart basebot-scanner
```

---

### Fix 2: Corriger PRIVATE_KEY

```bash
nano /home/basebot/trading-bot/config/.env

# Remplacer:
PRIVATE_KEY=votre_private_key

# Par votre vraie clé (depuis Metamask):
PRIVATE_KEY=0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef

# Sauvegarder et relancer:
systemctl restart basebot-scanner
```

---

### Fix 3: Changer RPC_URL

```bash
nano /home/basebot/trading-bot/config/.env

# Essayer ces RPC dans l'ordre:
RPC_URL=https://mainnet.base.org
# OU
RPC_URL=https://base.drpc.org
# OU
RPC_URL=https://base-rpc.publicnode.com

# Sauvegarder et relancer:
systemctl restart basebot-scanner
```

---

### Fix 4: Réinitialiser la base de données

```bash
su - basebot
cd /home/basebot/trading-bot
source venv/bin/activate

# Backup de l'ancienne DB
cp data/trading.db data/trading.db.backup

# Réinitialiser
python src/init_database.py

# Relancer le Scanner
exit
systemctl restart basebot-scanner
```

---

### Fix 5: Corriger les permissions

```bash
# En tant que root:
chown -R basebot:basebot /home/basebot/trading-bot
chmod -R 755 /home/basebot/trading-bot/logs
chmod 600 /home/basebot/trading-bot/config/.env

# Relancer:
systemctl restart basebot-scanner
```

---

## 📞 Collecte d'informations pour support

Si aucune solution ne fonctionne, collecter ces informations:

```bash
# Diagnostic complet
cd /home/basebot/trading-bot
bash diagnose_scanner.sh > /tmp/diagnostic_complet.txt 2>&1

# Test Python
su - basebot -c "cd /home/basebot/trading-bot && source venv/bin/activate && python test_scanner_simple.py" > /tmp/diagnostic_python.txt 2>&1

# Logs systemd
journalctl -u basebot-scanner -n 200 --no-pager > /tmp/logs_systemd.txt 2>&1

# Configuration (sans secrets)
grep -Ev "PRIVATE_KEY|API_KEY" /home/basebot/trading-bot/config/.env > /tmp/config_safe.txt 2>&1

# Fichiers à partager:
ls -lh /tmp/diagnostic_*.txt /tmp/logs_systemd.txt /tmp/config_safe.txt
```

---

## ✅ Checklist finale

Avant de demander de l'aide, vérifier:

- [ ] Exécuté `diagnose_scanner.sh`
- [ ] Exécuté `test_scanner_simple.py`
- [ ] Lu `TROUBLESHOOTING_SCANNER.md`
- [ ] Vérifié que `PRIVATE_KEY` est configurée
- [ ] Testé plusieurs `RPC_URL`
- [ ] Corrigé les permissions (`chown -R basebot:basebot`)
- [ ] Ajouté `PYTHONUNBUFFERED=1` au service
- [ ] Testé en mode manuel (`python src/Scanner.py`)
- [ ] Attendu au moins 60 secondes pour les logs
- [ ] Vérifié que la base de données existe

---

**Dernière mise à jour:** 2025-11-07
**Version:** 1.0
