#!/usr/bin/env python3
"""
Script de migration pour corriger amount_out dans trade_history
Recalcule amount_out basé sur amount_in et profit_loss
"""

import sqlite3
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / 'data' / 'trading.db'

def fix_amount_out():
    """Corrige les valeurs amount_out dans trade_history"""

    print("=" * 60)
    print("🔧 Migration: Correction de amount_out dans trade_history")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Récupérer toutes les positions fermées avec amount_out incorrect
    cursor.execute("""
        SELECT id, token_address, symbol, amount_in, amount_out, profit_loss
        FROM trade_history
        WHERE exit_time IS NOT NULL
        AND amount_in IS NOT NULL
        AND profit_loss IS NOT NULL
    """)

    rows = cursor.fetchall()

    if not rows:
        print("✅ Aucune ligne à corriger")
        conn.close()
        return

    print(f"📊 {len(rows)} trades fermés trouvés")
    print()

    corrected = 0
    unchanged = 0

    for row in rows:
        trade_id, token_address, symbol, amount_in, amount_out_old, profit_loss = row

        if amount_in is None or amount_in == 0:
            print(f"⚠️  {symbol}: amount_in invalide, ignoré")
            continue

        # Calculer le amount_out correct
        amount_out_correct = amount_in * (1 + profit_loss / 100)

        # Vérifier si la correction est nécessaire (tolérance 0.1%)
        if abs(amount_out_old - amount_out_correct) / amount_out_correct > 0.001:
            print(f"🔄 {symbol}:")
            print(f"   In:  {amount_in:.4f} ETH")
            print(f"   Out: {amount_out_old:.4f} ETH → {amount_out_correct:.4f} ETH")
            print(f"   P&L: {profit_loss:+.2f}%")

            # Mettre à jour
            cursor.execute("""
                UPDATE trade_history
                SET amount_out = ?
                WHERE id = ?
            """, (amount_out_correct, trade_id))

            corrected += 1
        else:
            unchanged += 1

    conn.commit()
    conn.close()

    print()
    print("=" * 60)
    print(f"✅ Migration terminée:")
    print(f"   • {corrected} trades corrigés")
    print(f"   • {unchanged} trades déjà corrects")
    print("=" * 60)

if __name__ == "__main__":
    fix_amount_out()
