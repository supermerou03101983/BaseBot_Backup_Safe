#!/usr/bin/env python3
"""
Test simple et direct du Scanner pour identifier le problème
À exécuter sur le VPS: python3 test_scanner_simple.py
"""

import sys
import os
from pathlib import Path

# Setup paths
PROJECT_DIR = Path(__file__).parent
sys.path.append(str(PROJECT_DIR / 'src'))

print("=" * 60)
print("Test Scanner - Diagnostic détaillé")
print("=" * 60)

# Test 1: Vérifier l'environnement
print("\n1️⃣ Vérification de l'environnement:")
print(f"   Python version: {sys.version}")
print(f"   Working directory: {os.getcwd()}")
print(f"   Project directory: {PROJECT_DIR}")

# Test 2: Charger .env
print("\n2️⃣ Chargement du fichier .env:")
try:
    from dotenv import load_dotenv
    env_path = PROJECT_DIR / 'config' / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"   ✅ .env chargé depuis: {env_path}")
        rpc_url = os.getenv('RPC_URL')
        private_key = os.getenv('PRIVATE_KEY')
        print(f"   RPC_URL: {rpc_url[:50] if rpc_url else 'NON DÉFINI'}...")
        print(f"   PRIVATE_KEY: {'✅ Défini' if private_key and private_key != 'votre_private_key' else '❌ NON DÉFINI'}")
    else:
        print(f"   ❌ Fichier .env introuvable: {env_path}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

# Test 3: Importer les modules
print("\n3️⃣ Import des modules:")
try:
    from web3 import Web3
    print("   ✅ web3")
except Exception as e:
    print(f"   ❌ web3: {e}")

try:
    import requests
    print("   ✅ requests")
except Exception as e:
    print(f"   ❌ requests: {e}")

try:
    import sqlite3
    print("   ✅ sqlite3")
except Exception as e:
    print(f"   ❌ sqlite3: {e}")

try:
    from web3_utils import BaseWeb3Manager, DexScreenerAPI
    print("   ✅ web3_utils (BaseWeb3Manager, DexScreenerAPI)")
except Exception as e:
    print(f"   ❌ web3_utils: {e}")

# Test 4: Connexion Web3
print("\n4️⃣ Test connexion Web3:")
try:
    from web3_utils import BaseWeb3Manager
    rpc_url = os.getenv('RPC_URL', 'https://mainnet.base.org')
    private_key = os.getenv('PRIVATE_KEY')

    web3_manager = BaseWeb3Manager(rpc_url=rpc_url, private_key=private_key)
    is_connected = web3_manager.w3.is_connected()

    print(f"   RPC URL: {rpc_url}")
    print(f"   Connecté: {'✅' if is_connected else '❌'} {is_connected}")

    if is_connected:
        block = web3_manager.w3.eth.block_number
        print(f"   Dernier bloc: {block}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

# Test 5: DexScreener API
print("\n5️⃣ Test DexScreener API:")
try:
    from web3_utils import DexScreenerAPI
    dex = DexScreenerAPI()
    print("   DexScreener API initialisée")

    # Test de la méthode get_recent_pairs_on_chain
    print("   Appel get_recent_pairs_on_chain('base', limit=5)...")
    pairs = dex.get_recent_pairs_on_chain('base', limit=5)

    if pairs:
        print(f"   ✅ {len(pairs)} paires récupérées")
        for i, pair in enumerate(pairs[:3], 1):
            token_addr = pair.get('tokenAddress', 'N/A')
            symbol = pair.get('baseToken', {}).get('symbol', 'N/A')
            print(f"      {i}. {symbol} - {token_addr[:10]}...")
    else:
        print("   ⚠️ Aucune paire récupérée (peut être normal)")

except Exception as e:
    print(f"   ❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Base de données
print("\n6️⃣ Test base de données:")
try:
    import sqlite3
    db_path = PROJECT_DIR / 'data' / 'trading.db'

    if db_path.exists():
        print(f"   ✅ Base trouvée: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Lister les tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"   Tables: {', '.join(tables)}")

        # Compter les tokens découverts
        if 'discovered_tokens' in tables:
            cursor.execute("SELECT COUNT(*) FROM discovered_tokens")
            count = cursor.fetchone()[0]
            print(f"   Tokens découverts: {count}")

        conn.close()
    else:
        print(f"   ⚠️ Base non trouvée: {db_path}")
        print("   (Sera créée au premier lancement du Scanner)")

except Exception as e:
    print(f"   ❌ Erreur: {e}")

# Test 7: Permissions logs
print("\n7️⃣ Test permissions logs:")
try:
    logs_dir = PROJECT_DIR / 'logs'
    if logs_dir.exists():
        print(f"   ✅ Répertoire logs existe: {logs_dir}")

        # Essayer d'écrire un fichier test
        test_file = logs_dir / 'test_write.txt'
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print("   ✅ Écriture dans logs/ possible")
        except Exception as e:
            print(f"   ❌ Impossible d'écrire dans logs/: {e}")
    else:
        print(f"   ⚠️ Répertoire logs n'existe pas: {logs_dir}")
        print("   (Sera créé au premier lancement du Scanner)")

except Exception as e:
    print(f"   ❌ Erreur: {e}")

# Test 8: Initialisation du Scanner (sans le lancer)
print("\n8️⃣ Test initialisation Scanner:")
try:
    from Scanner import EnhancedScanner
    print("   Création de l'instance Scanner...")
    scanner = EnhancedScanner()
    print("   ✅ Scanner initialisé avec succès")
    print(f"   Scan delay: {scanner.scan_delay} secondes")
    print(f"   Batch size: {scanner.batch_size}")
    print(f"   DB path: {scanner.db_path}")
    print(f"   Logger configuré: {'✅' if scanner.logger else '❌'}")

except Exception as e:
    print(f"   ❌ Erreur lors de l'initialisation: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test terminé")
print("=" * 60)
