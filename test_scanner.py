#!/usr/bin/env python3
"""
Script de test pour vérifier le fonctionnement du Scanner
"""

import sys
from pathlib import Path

# Setup paths
PROJECT_DIR = Path(__file__).parent
sys.path.append(str(PROJECT_DIR / 'src'))

from dotenv import load_dotenv
from web3_utils import DexScreenerAPI

load_dotenv(PROJECT_DIR / 'config' / '.env')

def test_dexscreener():
    """Test de l'API DexScreener"""
    print("=" * 60)
    print("TEST DE L'API DEXSCREENER")
    print("=" * 60)

    dex = DexScreenerAPI()

    # Test 1: Récupérer les paires récentes sur Base
    print("\n1. Test get_recent_pairs_on_chain...")
    try:
        pairs = dex.get_recent_pairs_on_chain('base', limit=5)
        print(f"✓ Méthode existe et fonctionne")
        print(f"✓ {len(pairs)} paires récupérées")

        if pairs:
            print("\nExemple de paire:")
            pair = pairs[0]
            print(f"  Token: {pair.get('baseToken', {}).get('symbol', 'N/A')}")
            print(f"  Adresse: {pair.get('tokenAddress', 'N/A')}")
            print(f"  Prix USD: ${pair.get('price_usd', 0):.8f}")
            print(f"  Liquidité: ${pair.get('liquidity_usd', 0):,.2f}")
            print(f"  Volume 24h: ${pair.get('volume_24h', 0):,.2f}")
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return False

    # Test 2: Récupérer les infos d'un token connu (WETH sur Base)
    print("\n2. Test get_token_info (WETH)...")
    weth_address = "0x4200000000000000000000000000000000000006"
    try:
        token_info = dex.get_token_info(weth_address)
        if token_info:
            print(f"✓ Token info récupérée")
            print(f"  Prix USD: ${token_info.get('price_usd', 0):,.2f}")
            print(f"  Liquidité: ${token_info.get('liquidity_usd', 0):,.2f}")
        else:
            print(f"⚠ Aucune info trouvée pour WETH")
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ TOUS LES TESTS SONT PASSÉS")
    print("=" * 60)
    return True

def test_scanner_imports():
    """Test des imports du Scanner"""
    print("\n" + "=" * 60)
    print("TEST DES IMPORTS DU SCANNER")
    print("=" * 60)

    try:
        from Scanner import EnhancedScanner
        print("✓ Import de Scanner.py réussi")

        # Tester l'initialisation (sans lancer le scanner)
        scanner = EnhancedScanner()
        print("✓ Initialisation du Scanner réussie")

        # Vérifier que les méthodes existent
        assert hasattr(scanner, 'fetch_new_tokens'), "Méthode fetch_new_tokens manquante"
        print("✓ Méthode fetch_new_tokens existe")

        assert hasattr(scanner, 'process_token_batch'), "Méthode process_token_batch manquante"
        print("✓ Méthode process_token_batch existe")

        assert hasattr(scanner, 'run'), "Méthode run manquante"
        print("✓ Méthode run existe")

        print("✓ TOUS LES IMPORTS SONT OK")
        return True

    except Exception as e:
        print(f"✗ Erreur lors de l'import: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🔍 TESTS DU SCANNER BASEBOT\n")

    # Test 1: DexScreener API
    dex_ok = test_dexscreener()

    # Test 2: Scanner imports
    scanner_ok = test_scanner_imports()

    # Résultat final
    print("\n" + "=" * 60)
    if dex_ok and scanner_ok:
        print("✅ TOUS LES TESTS SONT PASSÉS - LE SCANNER EST PRÊT")
        sys.exit(0)
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ - VÉRIFIEZ LES ERREURS CI-DESSUS")
        sys.exit(1)
