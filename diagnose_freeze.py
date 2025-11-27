#!/usr/bin/env python3
"""
Script de diagnostic pour identifier pourquoi le bot est freezé
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / 'data' / 'trading.db'

def diagnose_freeze():
    """Diagnostic complet du freeze"""

    print("=" * 80)
    print("🔍 DIAGNOSTIC DU FREEZE - BASE BOT")
    print("=" * 80)
    print(f"Timestamp: {datetime.now()}\n")

    if not DB_PATH.exists():
        print("❌ ERREUR: Base de données introuvable!")
        print(f"   Chemin attendu: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ========== VÉRIFIER LES POSITIONS OUVERTES ==========
    print("\n" + "=" * 80)
    print("📊 POSITIONS ACTUELLEMENT OUVERTES")
    print("=" * 80)

    # Chercher les positions dans trade_history sans exit_time
    cursor.execute("""
        SELECT token_address, symbol, side, price, amount_in,
               entry_time, timestamp
        FROM trade_history
        WHERE exit_time IS NULL
        ORDER BY timestamp DESC
    """)

    open_positions = cursor.fetchall()

    if open_positions:
        print(f"\n⚠️  {len(open_positions)} position(s) ouverte(s):\n")
        for pos in open_positions:
            token_addr, symbol, side, price, amount, entry_time, ts = pos
            if entry_time:
                entry_dt = datetime.fromisoformat(entry_time)
                duration = datetime.now() - entry_dt
                hours = duration.total_seconds() / 3600

                print(f"  Token: {symbol}")
                print(f"    Address: {token_addr}")
                print(f"    Side: {side}")
                print(f"    Entry Price: ${price}")
                print(f"    Amount: {amount} ETH")
                print(f"    Entry Time: {entry_time}")
                print(f"    ⏰ Durée: {hours:.1f} heures")

                if hours > 24:
                    print(f"    🚨 POSITION BLOQUÉE DEPUIS >24H!")
                print()
    else:
        print("✅ Aucune position ouverte dans la DB\n")

    # ========== VÉRIFIER LES DERNIERS TRADES ==========
    print("\n" + "=" * 80)
    print("📜 DERNIERS TRADES (10 derniers)")
    print("=" * 80)

    cursor.execute("""
        SELECT symbol, side, price, profit_loss,
               entry_time, exit_time, timestamp
        FROM trade_history
        ORDER BY timestamp DESC
        LIMIT 10
    """)

    recent_trades = cursor.fetchall()

    if recent_trades:
        print()
        for trade in recent_trades:
            symbol, side, price, pnl, entry, exit_t, ts = trade
            status = "FERMÉ" if exit_t else "OUVERT"
            pnl_str = f"{pnl:.2f}%" if pnl else "N/A"
            print(f"  {status:6s} | {symbol:10s} | {side:4s} | "
                  f"P&L: {pnl_str:8s} | {ts}")
        print()
    else:
        print("\n⚠️  Aucun trade dans l'historique!\n")

    # ========== VÉRIFIER LES LOGS D'ERREUR ==========
    print("\n" + "=" * 80)
    print("🔴 LOGS D'ERREUR (24 dernières heures)")
    print("=" * 80)

    cursor.execute("""
        SELECT timestamp, level, message, token_address, error_details
        FROM trade_log
        WHERE level IN ('ERROR', 'CRITICAL')
          AND timestamp > datetime('now', '-24 hours')
        ORDER BY timestamp DESC
        LIMIT 20
    """)

    error_logs = cursor.fetchall()

    if error_logs:
        print(f"\n⚠️  {len(error_logs)} erreur(s) détectée(s):\n")
        for log in error_logs:
            ts, level, msg, token, details = log
            print(f"  [{ts}] {level}")
            print(f"    Message: {msg}")
            if token:
                print(f"    Token: {token}")
            if details:
                print(f"    Détails: {details}")
            print()
    else:
        print("\n✅ Aucune erreur dans les logs récents\n")

    # ========== VÉRIFIER L'ACTIVITÉ RÉCENTE ==========
    print("\n" + "=" * 80)
    print("⏱️  ACTIVITÉ RÉCENTE")
    print("=" * 80)

    cursor.execute("""
        SELECT MAX(timestamp) as last_activity
        FROM trade_log
    """)

    last_activity = cursor.fetchone()[0]

    if last_activity:
        last_dt = datetime.fromisoformat(last_activity)
        time_since = datetime.now() - last_dt
        hours_since = time_since.total_seconds() / 3600

        print(f"\nDernière activité: {last_activity}")
        print(f"Il y a: {hours_since:.1f} heures")

        if hours_since > 1:
            print(f"🚨 FREEZE CONFIRMÉ: Aucune activité depuis {hours_since:.1f}h!")
        else:
            print("✅ Bot actif récemment")
    else:
        print("\n⚠️  Aucune activité détectée dans les logs")

    # ========== VÉRIFIER LA CONFIGURATION ==========
    print("\n" + "=" * 80)
    print("⚙️  CONFIGURATION ACTUELLE")
    print("=" * 80)

    cursor.execute("""
        SELECT key, value, updated_at
        FROM trading_config
        WHERE key IN ('MAX_POSITIONS', 'MAX_TRADES_PER_DAY',
                      'STOP_LOSS_PERCENT', 'MONITORING_INTERVAL',
                      'TIME_EXIT_MAXIMUM_HOURS', 'TIME_EXIT_EMERGENCY_HOURS')
        ORDER BY key
    """)

    configs = cursor.fetchall()

    if configs:
        print()
        for key, value, updated in configs:
            print(f"  {key:30s} = {value}")
        print()

    # ========== DIAGNOSTIC FINAL ==========
    print("\n" + "=" * 80)
    print("💡 DIAGNOSTIC")
    print("=" * 80)
    print()

    if open_positions:
        print("🔴 PROBLÈME IDENTIFIÉ: Positions bloquées\n")
        print("CAUSES POSSIBLES:")
        print("  1. Le bot a crashé/été tué mais les positions n'ont pas été fermées")
        print("  2. Erreur lors de la vente (slippage, gas, manque de liquidité)")
        print("  3. Boucle infinie dans le monitoring des positions")
        print("  4. Price feed API en panne (DexScreener/CoinGecko)")
        print("  5. RPC node en panne ou rate-limitée")
        print("\nSOLUTIONS:")
        print("  A. Redémarrer le bot (il devrait reprendre les positions)")
        print("  B. Fermer manuellement les positions via un script")
        print("  C. Vérifier les logs détaillés: tail -200 logs/trading.log")

        # Calculer la valeur potentielle bloquée
        total_eth_locked = sum(float(pos[4]) for pos in open_positions if pos[4])
        print(f"\n  💰 ETH bloqué: ~{total_eth_locked:.4f} ETH")

    elif last_activity and hours_since > 2:
        print("🟡 PROBLÈME: Bot inactif depuis longtemps\n")
        print("CAUSES POSSIBLES:")
        print("  1. Processus Python tué/crashé")
        print("  2. Pas de nouveaux tokens détectés (normal si marché calme)")
        print("  3. Tous les tokens rejetés par les filtres")
        print("\nSOLUTIONS:")
        print("  A. Vérifier si le processus tourne: ps aux | grep trader")
        print("  B. Vérifier les tokens découverts récemment")
        print("  C. Relancer le bot si nécessaire")

    else:
        print("✅ SYSTÈME SEMBLE NORMAL\n")
        print("Si vous pensez qu'il y a un problème:")
        print("  1. Vérifiez les logs: tail -100 logs/trading.log")
        print("  2. Vérifiez le processus: ps aux | grep python")
        print("  3. Vérifiez la connexion RPC")

    conn.close()

    print("\n" + "=" * 80)
    print("FIN DU DIAGNOSTIC")
    print("=" * 80)

if __name__ == "__main__":
    diagnose_freeze()
