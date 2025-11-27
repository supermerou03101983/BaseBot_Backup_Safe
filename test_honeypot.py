#!/usr/bin/env python3
"""
Script de test pour la protection honeypot
"""

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
sys.path.append(str(PROJECT_DIR / 'src'))

from honeypot_checker import check_honeypot


def test_token(token_address: str, name: str):
    """Teste un token et affiche les résultats"""
    print(f"\n{'='*70}")
    print(f"🧪 TEST: {name}")
    print(f"📍 Address: {token_address}")
    print('='*70)

    result = check_honeypot(token_address, chain_id=8453)

    # Affichage des résultats
    status_icon = "✅" if result['is_safe'] else "❌"
    honeypot_icon = "🍯" if result['is_honeypot'] else "✅"

    print(f"\n{honeypot_icon} HONEYPOT: {'OUI' if result['is_honeypot'] else 'NON'}")
    print(f"{status_icon} SAFE TO TRADE: {'OUI' if result['is_safe'] else 'NON'}")
    print(f"⚠️  RISK LEVEL: {result['risk_level']}")

    print(f"\n💰 Taxes:")
    print(f"   Buy:      {result['buy_tax']:.2f}%")
    print(f"   Sell:     {result['sell_tax']:.2f}%")
    print(f"   Transfer: {result['transfer_tax']:.2f}%")

    print(f"\n🔓 Capabilities:")
    print(f"   Can Buy:  {'✅' if result['can_buy'] else '❌'}")
    print(f"   Can Sell: {'✅' if result['can_sell'] else '❌'}")

    print(f"\n💧 Liquidity: ${result['liquidity_amount']:,.0f}")

    if result['flags']:
        print(f"\n🚩 FLAGS DETECTED:")
        for flag in result['flags']:
            print(f"   • {flag}")

    if result['error']:
        print(f"\n❌ ERROR: {result['error']}")

    print('='*70)

    # Verdict final
    if result['is_safe']:
        print("✅ VERDICT: Token OK pour trading")
    else:
        print("❌ VERDICT: NE PAS TRADER CE TOKEN")

    print('='*70)


def main():
    """Tests sur différents types de tokens"""

    print("\n" + "="*70)
    print("🍯 TEST DE LA PROTECTION HONEYPOT")
    print("="*70)

    # Test 1: Token légitime (WETH sur Base)
    test_token(
        "0x4200000000000000000000000000000000000006",
        "WETH (Token légitime)"
    )

    # Test 2: Token avec argument utilisateur
    if len(sys.argv) > 1:
        test_token(
            sys.argv[1],
            "Token fourni par l'utilisateur"
        )
    else:
        print("\n💡 Pour tester un token spécifique:")
        print(f"   python3 {sys.argv[0]} <token_address>")

    print("\n" + "="*70)
    print("✅ Tests terminés")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
