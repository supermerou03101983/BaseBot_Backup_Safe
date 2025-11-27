#!/bin/bash
# Script de diagnostic complet pour le Scanner
# À exécuter sur le VPS: bash diagnose_scanner.sh

echo "=========================================="
echo "🔍 Diagnostic Scanner BaseBot"
echo "=========================================="
echo ""

# 1. Statut du service
echo "1️⃣ Statut du service Scanner:"
systemctl status basebot-scanner --no-pager -l
echo ""

# 2. Logs systemd (dernières 50 lignes)
echo "2️⃣ Logs systemd (50 dernières lignes):"
journalctl -u basebot-scanner -n 50 --no-pager
echo ""

# 3. Logs applicatifs
echo "3️⃣ Logs applicatifs:"
if [ -f "/home/basebot/trading-bot/logs/scanner.log" ]; then
    echo "📄 scanner.log (50 dernières lignes):"
    tail -50 /home/basebot/trading-bot/logs/scanner.log
else
    echo "❌ Fichier scanner.log introuvable"
fi
echo ""

if [ -f "/home/basebot/trading-bot/logs/scanner_error.log" ]; then
    echo "📄 scanner_error.log (50 dernières lignes):"
    tail -50 /home/basebot/trading-bot/logs/scanner_error.log
else
    echo "⚠️ Fichier scanner_error.log introuvable"
fi
echo ""

# 4. Permissions des fichiers
echo "4️⃣ Permissions du répertoire logs:"
ls -la /home/basebot/trading-bot/logs/
echo ""

# 5. Vérifier le fichier Scanner.py
echo "5️⃣ Vérification Scanner.py existe:"
if [ -f "/home/basebot/trading-bot/src/Scanner.py" ]; then
    echo "✅ Scanner.py trouvé"
    echo "Taille: $(wc -l /home/basebot/trading-bot/src/Scanner.py | awk '{print $1}') lignes"
else
    echo "❌ Scanner.py introuvable!"
fi
echo ""

# 6. Vérifier configuration .env
echo "6️⃣ Configuration .env (sans secrets):"
if [ -f "/home/basebot/trading-bot/config/.env" ]; then
    echo "✅ .env trouvé"
    grep -E "^(RPC_URL|SCAN_INTERVAL|DATABASE_PATH)" /home/basebot/trading-bot/config/.env | head -10
    echo ""
    echo "⚠️ Vérification PRIVATE_KEY (présence uniquement):"
    if grep -q "^PRIVATE_KEY=" /home/basebot/trading-bot/config/.env; then
        KEY_VALUE=$(grep "^PRIVATE_KEY=" /home/basebot/trading-bot/config/.env | cut -d'=' -f2)
        if [ -n "$KEY_VALUE" ] && [ "$KEY_VALUE" != "votre_private_key" ]; then
            echo "✅ PRIVATE_KEY est configurée"
        else
            echo "❌ PRIVATE_KEY n'est pas configurée (valeur par défaut)"
        fi
    else
        echo "❌ PRIVATE_KEY manquante dans .env"
    fi
else
    echo "❌ Fichier .env introuvable!"
fi
echo ""

# 7. Base de données
echo "7️⃣ Vérification base de données:"
if [ -f "/home/basebot/trading-bot/data/trading.db" ]; then
    echo "✅ trading.db trouvé"
    echo "Taille: $(du -h /home/basebot/trading-bot/data/trading.db | cut -f1)"
    echo ""
    echo "Tables dans la base:"
    sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT name FROM sqlite_master WHERE type='table';"
    echo ""
    echo "Tokens découverts:"
    sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT COUNT(*) FROM discovered_tokens;" 2>/dev/null || echo "❌ Erreur requête discovered_tokens"
else
    echo "❌ Base de données introuvable!"
fi
echo ""

# 8. Test Python et imports
echo "8️⃣ Test Python et modules:"
su - basebot -c "cd /home/basebot/trading-bot && source venv/bin/activate && python3 -c '
import sys
print(f\"Python version: {sys.version}\")
try:
    from web3 import Web3
    print(\"✅ web3 importé\")
except Exception as e:
    print(f\"❌ Erreur import web3: {e}\")

try:
    import requests
    print(\"✅ requests importé\")
except Exception as e:
    print(f\"❌ Erreur import requests: {e}\")

try:
    import sqlite3
    print(\"✅ sqlite3 importé\")
except Exception as e:
    print(f\"❌ Erreur import sqlite3: {e}\")
'"
echo ""

# 9. Test connexion RPC
echo "9️⃣ Test connexion RPC:"
su - basebot -c "cd /home/basebot/trading-bot && source venv/bin/activate && python3 -c '
import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv(\"config/.env\")
rpc_url = os.getenv(\"RPC_URL\", \"https://mainnet.base.org\")

try:
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    print(f\"RPC URL: {rpc_url}\")
    print(f\"Connecté: {w3.is_connected()}\")
    if w3.is_connected():
        print(f\"Dernier bloc: {w3.eth.block_number}\")
except Exception as e:
    print(f\"❌ Erreur connexion: {e}\")
'"
echo ""

# 10. Processus en cours
echo "🔟 Processus Scanner en cours:"
ps aux | grep -E "Scanner.py|basebot" | grep -v grep
echo ""

echo "=========================================="
echo "✅ Diagnostic terminé"
echo "=========================================="
