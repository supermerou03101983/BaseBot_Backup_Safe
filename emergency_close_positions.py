#!/usr/bin/env python3
"""
Script d'urgence pour fermer manuellement les positions bloquées
ATTENTION: À utiliser seulement si le bot est freezé
"""

import sqlite3
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from decimal import Decimal

PROJECT_DIR = Path(__file__).parent
sys.path.append(str(PROJECT_DIR))

from web3 import Web3
from dotenv import load_dotenv

load_dotenv(PROJECT_DIR / 'config' / '.env')

DB_PATH = PROJECT_DIR / 'data' / 'trading.db'

def get_open_positions():
    """Récupère les positions ouvertes de la DB"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, token_address, symbol, price, amount_in, entry_time
        FROM trade_history
        WHERE exit_time IS NULL
        ORDER BY timestamp DESC
    """)

    positions = cursor.fetchall()
    conn.close()
    return positions

def close_position_in_db(position_id, reason="MANUAL_EMERGENCY_CLOSE"):
    """Ferme une position dans la DB (mode paper uniquement)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE trade_history
        SET exit_time = ?,
            profit_loss = 0,
            amount_out = amount_in
        WHERE id = ?
    """, (datetime.now().isoformat(), position_id))

    # Log l'action
    cursor.execute("""
        INSERT INTO trade_log (timestamp, level, message, token_address)
        VALUES (?, 'WARNING', ?, '')
    """, (datetime.now().isoformat(), f"Position {position_id} fermée manuellement: {reason}"))

    conn.commit()
    conn.close()

def emergency_close_all():
    """Ferme toutes les positions ouvertes en mode d'urgence"""

    print("=" * 80)
    print("🚨 FERMETURE D'URGENCE DES POSITIONS")
    print("=" * 80)
    print()

    if not DB_PATH.exists():
        print("❌ ERREUR: Base de données introuvable!")
        return

    positions = get_open_positions()

    if not positions:
        print("✅ Aucune position ouverte à fermer\n")
        return

    print(f"⚠️  {len(positions)} position(s) ouverte(s) détectée(s):\n")

    for pos in positions:
        pos_id, token_addr, symbol, price, amount, entry_time = pos
        entry_dt = datetime.fromisoformat(entry_time) if entry_time else None
        duration = (datetime.now() - entry_dt).total_seconds() / 3600 if entry_dt else 0

        print(f"  [{pos_id}] {symbol}")
        print(f"      Token: {token_addr}")
        print(f"      Amount: {amount} ETH")
        print(f"      Entry: {entry_time}")
        print(f"      Durée: {duration:.1f}h")
        print()

    print("=" * 80)
    print("⚠️  ATTENTION: Cette action va:")
    print("   1. Marquer toutes les positions comme FERMÉES dans la DB")
    print("   2. Enregistrer P&L = 0% (neutre)")
    print("   3. Permettre au bot de repartir sur de nouvelles positions")
    print()
    print("IMPORTANT:")
    print("   - En mode PAPER: Pas de risque, juste cleanup de la DB")
    print("   - En mode REAL: Les tokens restent dans votre wallet!")
    print("     Vous devrez les vendre manuellement si besoin")
    print("=" * 80)
    print()

    response = input("Voulez-vous continuer? (tapez 'OUI' en majuscules): ")

    if response != "OUI":
        print("\n❌ Opération annulée")
        return

    print("\n🔧 Fermeture des positions en cours...\n")

    for pos in positions:
        pos_id, token_addr, symbol, price, amount, entry_time = pos

        try:
            close_position_in_db(pos_id, "EMERGENCY_CLOSE_FREEZE")
            print(f"  ✅ Position {pos_id} ({symbol}) fermée")
        except Exception as e:
            print(f"  ❌ Erreur lors de la fermeture de {symbol}: {e}")

    print("\n✅ Fermeture d'urgence terminée!")
    print("\nPROCHAINES ÉTAPES:")
    print("  1. Vérifier: python3 diagnose_freeze.py")
    print("  2. Redémarrer le bot normalement")
    print("  3. Si mode REAL: Vendre manuellement les tokens depuis votre wallet")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    emergency_close_all()
