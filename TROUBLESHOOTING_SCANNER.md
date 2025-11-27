# Troubleshooting Scanner - Aucun log affiché

## Symptôme

Le service Scanner démarre sans erreur mais ne produit aucun log dans journalctl ou dans les fichiers de logs.

## Causes possibles

### 1. Scanner attend l'intervalle de scan (SCAN_INTERVAL_SECONDS)
Le Scanner attend 30 secondes (par défaut) entre chaque scan. Si vous vérifiez les logs trop tôt, il peut sembler inactif.

### 2. Configuration .env incomplète
Si `PRIVATE_KEY` ou `RPC_URL` ne sont pas correctement configurés, le Scanner peut échouer silencieusement lors de l'initialisation.

### 3. DexScreener API ne retourne aucune paire
L'API peut temporairement ne pas retourner de résultats, et le Scanner basculera sur le fallback (base de données locale).

### 4. Buffering des logs
Python peut mettre en buffer les logs si stdout n'est pas configuré en mode non-bufferisé dans systemd.

### 5. Permissions sur les fichiers de logs
Même avec `chown -R basebot:basebot`, les fichiers de logs peuvent ne pas être accessibles en écriture.

## Diagnostic étape par étape

### Étape 1: Exécuter le script de diagnostic complet

Sur votre VPS:

```bash
bash diagnose_scanner.sh
```

Ce script vérifie:
- Statut du service systemd
- Logs systemd (journalctl)
- Logs applicatifs (scanner.log, scanner_error.log)
- Permissions des fichiers
- Configuration .env (sans exposer les secrets)
- Base de données
- Imports Python
- Connexion RPC
- Processus en cours

### Étape 2: Test manuel du Scanner

Arrêter le service et lancer le Scanner manuellement:

```bash
# Arrêter le service
systemctl stop basebot-scanner

# Se connecter en tant que basebot
su - basebot

# Activer l'environnement virtuel
cd /home/basebot/trading-bot
source venv/bin/activate

# Lancer le Scanner manuellement
python src/Scanner.py
```

**Résultat attendu:**
```
2025-11-07 10:30:00 - INFO - Scanner démarré...
2025-11-07 10:30:00 - INFO - Récupération des nouveaux tokens depuis DexScreener...
2025-11-07 10:30:02 - INFO - 20 paires trouvées sur DexScreener
2025-11-07 10:30:02 - INFO - 20 nouveaux tokens potentiels trouvés. Traitement...
2025-11-07 10:30:05 - INFO - Token découvert: SYMBOL (0x...) - MC: $...
...
```

Si aucun log n'apparaît même en mode manuel, passer à l'étape 3.

### Étape 3: Test avec le script de diagnostic Python

```bash
# Toujours en tant que basebot
cd /home/basebot/trading-bot
source venv/bin/activate
python test_scanner_simple.py
```

Ce script teste séquentiellement:
1. Environnement Python
2. Fichier .env et variables
3. Import des modules (web3, requests, sqlite3, web3_utils)
4. Connexion Web3 au RPC
5. API DexScreener
6. Base de données SQLite
7. Permissions d'écriture dans logs/
8. Initialisation du Scanner

**Interpréter les résultats:**

- ✅ = OK
- ⚠️ = Avertissement (peut être normal)
- ❌ = Erreur (doit être corrigé)

### Étape 4: Vérifier la configuration .env

```bash
cat /home/basebot/trading-bot/config/.env | grep -E "^(PRIVATE_KEY|RPC_URL|SCAN_INTERVAL)"
```

**Vérifications critiques:**

1. **PRIVATE_KEY**: Ne doit PAS être `votre_private_key` (valeur par défaut)
   ```bash
   # Si vous voyez ceci, la clé n'est pas configurée:
   PRIVATE_KEY=votre_private_key  # ❌ INVALIDE

   # Doit ressembler à ceci:
   PRIVATE_KEY=0x1234567890abcdef...  # ✅ VALIDE
   ```

2. **RPC_URL**: Doit pointer vers Base Network
   ```bash
   RPC_URL=https://mainnet.base.org  # ✅ OK
   # OU
   RPC_URL=https://base.drpc.org  # ✅ OK
   # OU
   RPC_URL=https://base-rpc.publicnode.com  # ✅ OK
   ```

3. **SCAN_INTERVAL_SECONDS**: Contrôle la fréquence de scan
   ```bash
   SCAN_INTERVAL_SECONDS=30  # Par défaut (30 secondes)
   ```

### Étape 5: Tester la connexion RPC

```bash
su - basebot -c "cd /home/basebot/trading-bot && source venv/bin/activate && python3 -c '
from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv(\"config/.env\")
rpc_url = os.getenv(\"RPC_URL\", \"https://mainnet.base.org\")

w3 = Web3(Web3.HTTPProvider(rpc_url))
print(f\"RPC URL: {rpc_url}\")
print(f\"Connecté: {w3.is_connected()}\")
if w3.is_connected():
    print(f\"Dernier bloc: {w3.eth.block_number}\")
'"
```

**Résultat attendu:**
```
RPC URL: https://mainnet.base.org
Connecté: True
Dernier bloc: 37860123
```

Si `Connecté: False`, votre RPC_URL est invalide ou inaccessible.

### Étape 6: Vérifier les logs systemd avec plus de contexte

```bash
journalctl -u basebot-scanner -n 200 --no-pager -o verbose
```

Cela affiche les logs avec plus de détails système, y compris les erreurs de démarrage silencieuses.

### Étape 7: Vérifier si le processus tourne réellement

```bash
ps aux | grep Scanner.py
```

**Résultat attendu:**
```
basebot   1234  0.5  2.3 123456 45678 ?  Ss   10:30   0:01 /home/basebot/trading-bot/venv/bin/python /home/basebot/trading-bot/src/Scanner.py
```

Si aucun processus n'apparaît, le service ne démarre pas correctement.

## Solutions aux problèmes courants

### Problème 1: PRIVATE_KEY non configurée

**Symptôme:**
```
❌ PRIVATE_KEY n'est pas configurée (valeur par défaut)
```

**Solution:**
```bash
nano /home/basebot/trading-bot/config/.env

# Remplacer:
PRIVATE_KEY=votre_private_key

# Par votre vraie clé privée (depuis Metamask par exemple):
PRIVATE_KEY=0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
```

⚠️ **IMPORTANT**:
- Ne JAMAIS partager cette clé
- Ne JAMAIS commit ce fichier dans git
- Utiliser un wallet dédié au trading bot (pas votre wallet principal)

### Problème 2: RPC_URL inaccessible

**Symptôme:**
```
Connecté: False
```

**Solution:**

Essayer un autre RPC dans le fichier .env:

```bash
# Option 1 (recommandée)
RPC_URL=https://mainnet.base.org

# Option 2 (backup)
RPC_URL=https://base.drpc.org

# Option 3 (si les autres échouent)
RPC_URL=https://base-rpc.publicnode.com

# Option 4 (privé, nécessite compte)
RPC_URL=https://base-mainnet.infura.io/v3/VOTRE_PROJECT_ID
```

### Problème 3: Logs en buffer (pas affichés en temps réel)

**Symptôme:**
Le service tourne mais journalctl ne montre rien pendant plusieurs minutes.

**Solution:**

Modifier le service systemd pour désactiver le buffering:

```bash
nano /etc/systemd/system/basebot-scanner.service

# Ajouter cette ligne dans la section [Service]:
Environment="PYTHONUNBUFFERED=1"
```

Service complet:
```ini
[Unit]
Description=BaseBot Trading Scanner
After=network.target

[Service]
Type=simple
User=basebot
WorkingDirectory=/home/basebot/trading-bot
Environment="PATH=/home/basebot/trading-bot/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/basebot/trading-bot/venv/bin/python /home/basebot/trading-bot/src/Scanner.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Puis:
```bash
systemctl daemon-reload
systemctl restart basebot-scanner
journalctl -u basebot-scanner -f
```

### Problème 4: DexScreener API ne retourne rien

**Symptôme:**
```
WARNING - Aucune nouvelle paire trouvée sur DexScreener
```

**Explication:**
C'est **normal** si DexScreener n'a pas de nouvelles paires au moment du scan. Le Scanner va:
1. Logger un warning
2. Basculer sur le mode fallback (relire les tokens existants en DB)
3. Attendre 30 secondes avant de réessayer

**Ce n'est PAS une erreur**. Le Scanner va continuer à vérifier toutes les 30 secondes.

### Problème 5: Base de données verrouillée

**Symptôme:**
```
ERROR - database is locked
```

**Cause:**
Plusieurs processus (Scanner, Filter, Trader) accèdent à la DB SQLite simultanément.

**Solution:**
SQLite supporte les accès concurrents en lecture, mais pas en écriture. Ajouter des retries:

C'est déjà géré dans le code, mais si le problème persiste:

```bash
# Vérifier qu'aucun autre processus n'écrit dans la DB
lsof /home/basebot/trading-bot/data/trading.db
```

### Problème 6: Permissions logs/ incorrectes

**Symptôme:**
```
PermissionError: [Errno 13] Permission denied: '/home/basebot/trading-bot/logs/scanner.log'
```

**Solution:**
```bash
# Corriger les permissions
chown -R basebot:basebot /home/basebot/trading-bot
chmod -R 755 /home/basebot/trading-bot/logs

# Vérifier
ls -la /home/basebot/trading-bot/logs/

# Relancer
systemctl restart basebot-scanner
```

## Workflow de diagnostic complet

```bash
# 1. Diagnostic automatique
bash diagnose_scanner.sh > diagnostic_output.txt 2>&1

# 2. Test manuel
systemctl stop basebot-scanner
su - basebot -c "cd /home/basebot/trading-bot && source venv/bin/activate && timeout 60 python src/Scanner.py"

# 3. Si aucun log après 60 secondes:
su - basebot -c "cd /home/basebot/trading-bot && source venv/bin/activate && python test_scanner_simple.py"

# 4. Vérifier .env
grep -E "^(PRIVATE_KEY|RPC_URL)" /home/basebot/trading-bot/config/.env

# 5. Corriger si nécessaire et relancer
systemctl start basebot-scanner
journalctl -u basebot-scanner -f
```

## Ce qui doit apparaître dans les logs (normal)

### Démarrage réussi:
```
INFO - Scanner démarré...
INFO - Récupération des nouveaux tokens depuis DexScreener...
INFO - 20 paires trouvées sur DexScreener
INFO - 20 nouveaux tokens potentiels trouvés. Traitement...
INFO - Token découvert: WETH (0x4200...) - MC: $1234567.89
INFO - Token découvert: USDC (0x833...) - MC: $987654.32
...
```

### Aucune nouvelle paire (normal):
```
INFO - Scanner démarré...
INFO - Récupération des nouveaux tokens depuis DexScreener...
WARNING - Aucune nouvelle paire trouvée sur DexScreener
INFO - 10 nouveaux tokens potentiels trouvés. Traitement...
```

### Attente entre les scans (normal):
```
INFO - Scanner démarré...
INFO - Récupération des nouveaux tokens depuis DexScreener...
INFO - 5 paires trouvées sur DexScreener
INFO - 5 nouveaux tokens potentiels trouvés. Traitement...
INFO - Token découvert: TOKEN1 (0x...) - MC: $50000.00
# [30 secondes de silence - NORMAL]
INFO - Récupération des nouveaux tokens depuis DexScreener...
```

## Support

Si après avoir suivi tous ces diagnostics le Scanner ne fonctionne toujours pas:

1. Collecter les informations:
   ```bash
   bash diagnose_scanner.sh > diagnostic_complet.txt 2>&1
   python test_scanner_simple.py > test_python.txt 2>&1
   journalctl -u basebot-scanner -n 200 > logs_systemd.txt 2>&1
   ```

2. Vérifier les fichiers générés:
   - `diagnostic_complet.txt`
   - `test_python.txt`
   - `logs_systemd.txt`

3. Partager ces fichiers pour diagnostic approfondi

---

**Dernière mise à jour**: 2025-11-07
**Version du guide**: 1.0
