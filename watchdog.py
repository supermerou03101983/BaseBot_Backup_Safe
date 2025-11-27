#!/usr/bin/env python3
"""
Watchdog pour détecter et résoudre automatiquement les freezes du bot
À exécuter en parallèle du trader (cron job toutes les 15 minutes)
"""

import sqlite3
import os
import signal
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / 'data' / 'trading.db'
LOG_PATH = PROJECT_DIR / 'logs' / 'watchdog.log'

# Configuration
MAX_INACTIVITY_MINUTES = 30  # Alerte si pas d'activité pendant 30 min
MAX_POSITION_HOURS = 48      # Alerte si position ouverte >48h
EMERGENCY_POSITION_HOURS = 120  # Force close si position >120h

def log_message(message, level="INFO"):
    """Log dans le fichier watchdog"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {level:8s} - {message}\n"

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, 'a') as f:
        f.write(log_line)

    print(log_line.strip())

def check_bot_activity():
    """Vérifie si le bot est actif"""
    if not DB_PATH.exists():
        log_message("Base de données introuvable", "ERROR")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Dernière activité
    cursor.execute("SELECT MAX(timestamp) FROM trade_log")
    last_activity = cursor.fetchone()[0]

    conn.close()

    if not last_activity:
        log_message("Aucune activité détectée dans les logs", "WARNING")
        return False

    last_dt = datetime.fromisoformat(last_activity)
    time_since = datetime.now() - last_dt
    minutes_since = time_since.total_seconds() / 60

    if minutes_since > MAX_INACTIVITY_MINUTES:
        log_message(f"Bot inactif depuis {minutes_since:.1f} minutes", "WARNING")
        return False

    log_message(f"Bot actif (dernière activité: {minutes_since:.1f}m)", "INFO")
    return True

def check_stuck_positions():
    """Vérifie les positions bloquées"""
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, token_address, symbol, price, amount_in, entry_time
        FROM trade_history
        WHERE exit_time IS NULL
    """)

    positions = cursor.fetchall()
    conn.close()

    stuck_positions = []

    for pos in positions:
        pos_id, token_addr, symbol, price, amount, entry_time = pos

        if not entry_time:
            continue

        entry_dt = datetime.fromisoformat(entry_time)
        duration = datetime.now() - entry_dt
        hours = duration.total_seconds() / 3600

        if hours > MAX_POSITION_HOURS:
            stuck_positions.append({
                'id': pos_id,
                'symbol': symbol,
                'hours': hours,
                'amount': amount
            })

            if hours > EMERGENCY_POSITION_HOURS:
                log_message(
                    f"Position CRITIQUE bloquée: {symbol} depuis {hours:.1f}h",
                    "CRITICAL"
                )
            else:
                log_message(
                    f"Position bloquée: {symbol} depuis {hours:.1f}h",
                    "WARNING"
                )

    return stuck_positions

def check_process_running():
    """Vérifie si le processus trader tourne"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'Trader.py'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            log_message(f"Processus trader actif (PID: {', '.join(pids)})", "INFO")
            return True
        else:
            log_message("Processus trader non trouvé", "WARNING")
            return False
    except Exception as e:
        log_message(f"Erreur vérification processus: {e}", "ERROR")
        return False

def send_alert(message):
    """Envoie une alerte (à personnaliser: email, Telegram, etc.)"""
    log_message(f"ALERTE: {message}", "ALERT")
    # TODO: Implémenter notification (Telegram, email, etc.)

def main():
    """Watchdog principal"""
    log_message("=" * 60)
    log_message("Watchdog démarré")

    # Vérifier si le processus tourne
    process_running = check_process_running()

    # Vérifier l'activité
    bot_active = check_bot_activity()

    # Vérifier les positions bloquées
    stuck_positions = check_stuck_positions()

    # Décisions
    if not process_running:
        send_alert("Processus trader non actif!")
        log_message("ACTION RECOMMANDÉE: Redémarrer le bot", "WARNING")

    if not bot_active and process_running:
        send_alert("Bot freeze détecté: processus actif mais aucune activité")
        log_message("ACTION RECOMMANDÉE: Kill et redémarrer le bot", "WARNING")

    if stuck_positions:
        total_stuck = len(stuck_positions)
        critical_stuck = [p for p in stuck_positions if p['hours'] > EMERGENCY_POSITION_HOURS]

        if critical_stuck:
            send_alert(f"{len(critical_stuck)} position(s) critique(s) bloquée(s) >120h")
            log_message(
                "ACTION RECOMMANDÉE: Exécuter emergency_close_positions.py",
                "CRITICAL"
            )

        send_alert(f"{total_stuck} position(s) bloquée(s) depuis >48h")

    # Résumé
    if process_running and bot_active and not stuck_positions:
        log_message("✅ Système sain", "INFO")
    else:
        log_message("⚠️  Problèmes détectés, vérifier les logs", "WARNING")

    log_message("Watchdog terminé")
    log_message("=" * 60)

if __name__ == "__main__":
    main()
