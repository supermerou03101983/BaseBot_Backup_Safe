#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire de configuration pour Base Trading Bot
"""

import json
import sys
import sqlite3
import os
from datetime import datetime
from pathlib import Path
import shutil

PROJECT_DIR = Path("/home/basebot/trading-bot")
CONFIG_DIR = PROJECT_DIR / 'config'
DB_PATH = PROJECT_DIR / 'data' / 'trading.db'
BACKUP_DIR = PROJECT_DIR / 'backups'

def check_services_running():
    """Vérifie si des services sont en cours d'exécution"""
    services = ['base-scanner', 'base-filter', 'base-trader']
    running = []
    for service in services:
        result = os.system(f"systemctl is-active --quiet {service}")
        if result == 0:
            running.append(service)
    return running

def backup_configuration():
    """Sauvegarde la configuration actuelle"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Backup de la DB
    if DB_PATH.exists():
        backup_db = BACKUP_DIR / f'trading_config_backup_{timestamp}.db'
        shutil.copy2(DB_PATH, backup_db)
        print(f"✅ Backup créé: {backup_db}")
        return backup_db
    return None

def init_config_if_missing(conn):
    """Initialise les clés de configuration si elles n'existent pas"""
    cursor = conn.cursor()
    
    # Vérifier si la table existe
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='trading_config'
    """)
    
    if not cursor.fetchone():
        print("❌ Table trading_config non trouvée. Exécutez d'abord init_database.py")
        sys.exit(1)
    
    # Clés par défaut
    default_configs = {
        'POSITION_SIZE_PERCENT': '15',
        'MAX_POSITIONS': '2',
        'MAX_TRADES_PER_DAY': '3',
        'STOP_LOSS_PERCENT': '5',
        'TRAILING_ACTIVATION_THRESHOLD': '12'
    }
    
    for key, default_value in default_configs.items():
        cursor.execute("INSERT OR IGNORE INTO trading_config (key, value) VALUES (?, ?)",
                      (key, default_value))
    conn.commit()

def update_trading_mode():
    """Met à jour le mode de trading (paper/real)"""
    mode_file = CONFIG_DIR / 'trading_mode.json'
    
    current_mode = 'paper'
    if mode_file.exists():
        with open(mode_file, 'r') as f:
            data = json.load(f)
            current_mode = data.get('mode', 'paper')
    
    print(f"\nMode de trading actuel: {current_mode.upper()}")
    print("1. Paper (Simulation)")
    print("2. Real (Production)")
    
    choice = input("\nChoisir le mode (1 ou 2, Entrée pour garder actuel): ").strip()
    
    if choice == '1':
        new_mode = 'paper'
    elif choice == '2':
        print("⚠️  ATTENTION: Le mode REAL utilisera de vrais fonds!")
        confirm = input("Êtes-vous sûr? (tapez 'CONFIRMER'): ")
        if confirm == 'CONFIRMER':
            new_mode = 'real'
        else:
            print("Mode Real annulé")
            return current_mode
    else:
        return current_mode
    
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(mode_file, 'w') as f:
        json.dump({
            'mode': new_mode,
            'updated_at': datetime.now().isoformat(),
            'updated_by': 'config_manager'
        }, f, indent=2)
    
    print(f"✅ Mode changé en: {new_mode.upper()}")
    return new_mode

def update_trading_params():
    """Met à jour les paramètres de trading dans la base de données"""
    
    print("\n" + "="*50)
    print("   Configuration Base Trading Bot")
    print("="*50)
    
    # Vérifier les services
    running_services = check_services_running()
    if running_services:
        print(f"\n⚠️  Services actifs détectés: {', '.join(running_services)}")
        confirm = input("Continuer quand même? (y/n): ")
        if confirm.lower() != 'y':
            print("Configuration annulée")
            return
    
    try:
        # Backup avant modification
        backup_path = backup_configuration()
        
        # Connexion DB
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Initialiser les configs si nécessaire
        init_config_if_missing(conn)
        
        # Récupérer la configuration actuelle
        cursor.execute("""
            SELECT key, value FROM trading_config 
            WHERE key IN (?, ?, ?, ?, ?)
        """, ('POSITION_SIZE_PERCENT', 'MAX_POSITIONS', 'MAX_TRADES_PER_DAY', 
              'STOP_LOSS_PERCENT', 'TRAILING_ACTIVATION_THRESHOLD'))
        
        current_config = dict(cursor.fetchall())
        
        print("\n📊 Configuration actuelle:")
        print("-" * 40)
        print(f"Taille position: {current_config.get('POSITION_SIZE_PERCENT', '15')}%")
        print(f"Positions max: {current_config.get('MAX_POSITIONS', '2')}")
        print(f"Trades/jour: {current_config.get('MAX_TRADES_PER_DAY', '3')}")
        print(f"Stop loss: {current_config.get('STOP_LOSS_PERCENT', '5')}%")
        print(f"Trailing activation: {current_config.get('TRAILING_ACTIVATION_THRESHOLD', '12')}%")
        
        # Changer le mode de trading
        new_mode = update_trading_mode()
        
        print("\n📝 Nouvelle configuration:")
        print("-" * 40)
        print("(Appuyez Entrée pour garder la valeur actuelle)")
        
        # Demander les nouvelles valeurs avec validation
        new_config = {}
        
        # Position size
        val = input(f"Taille position (%) [1-20] ({current_config.get('POSITION_SIZE_PERCENT', '15')}): ").strip()
        if val:
            try:
                val_int = int(val)
                if 1 <= val_int <= 20:
                    new_config['POSITION_SIZE_PERCENT'] = str(val_int)
                else:
                    print("⚠️  Valeur hors limites, valeur actuelle conservée")
            except ValueError:
                print("⚠️  Valeur invalide, valeur actuelle conservée")
        
        # Max positions
        val = input(f"Positions max [1-5] ({current_config.get('MAX_POSITIONS', '2')}): ").strip()
        if val:
            try:
                val_int = int(val)
                if 1 <= val_int <= 5:
                    new_config['MAX_POSITIONS'] = str(val_int)
                else:
                    print("⚠️  Valeur hors limites, valeur actuelle conservée")
            except ValueError:
                print("⚠️  Valeur invalide, valeur actuelle conservée")
        
        # Max trades per day
        val = input(f"Trades/jour [1-10] ({current_config.get('MAX_TRADES_PER_DAY', '3')}): ").strip()
        if val:
            try:
                val_int = int(val)
                if 1 <= val_int <= 10:
                    new_config['MAX_TRADES_PER_DAY'] = str(val_int)
                else:
                    print("⚠️  Valeur hors limites, valeur actuelle conservée")
            except ValueError:
                print("⚠️  Valeur invalide, valeur actuelle conservée")
        
        # Stop loss
        val = input(f"Stop loss (%) [3-50] ({current_config.get('STOP_LOSS_PERCENT', '5')}): ").strip()
        if val:
            try:
                val_int = int(val)
                if 3 <= val_int <= 50:
                    new_config['STOP_LOSS_PERCENT'] = str(val_int)
                else:
                    print("⚠️  Valeur hors limites, valeur actuelle conservée")
            except ValueError:
                print("⚠️  Valeur invalide, valeur actuelle conservée")
        
        # Trailing activation
        val = input(f"Trailing activation (%) [5-30] ({current_config.get('TRAILING_ACTIVATION_THRESHOLD', '12')}): ").strip()
        if val:
            try:
                val_int = int(val)
                if 5 <= val_int <= 30:
                    new_config['TRAILING_ACTIVATION_THRESHOLD'] = str(val_int)
                else:
                    print("⚠️  Valeur hors limites, valeur actuelle conservée")
            except ValueError:
                print("⚠️  Valeur invalide, valeur actuelle conservée")
        
        # Appliquer les changements
        if new_config:
            for key, value in new_config.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO trading_config (key, value, updated_at) 
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, value))
            
            conn.commit()
            print("\n✅ Configuration sauvegardée")
            
            # Logger les changements
            cursor.execute("""
                INSERT INTO trade_log (timestamp, level, message, token_address, tx_hash, error_details)
                VALUES (CURRENT_TIMESTAMP, 'INFO', ?, '', '', ?)
            """, (f"Configuration mise à jour", json.dumps(new_config)))
            conn.commit()
        else:
            print("\n✅ Aucun changement effectué")
        
        conn.close()
        
        if running_services:
            print("\n⚠️  Pour appliquer les changements, redémarrez les services:")
            for service in running_services:
                print(f"   sudo systemctl restart {service}")
        
    except KeyboardInterrupt:
        print("\n\n❌ Configuration annulée par l'utilisateur")
        if 'backup_path' in locals() and backup_path:
            print(f"Backup disponible: {backup_path}")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        if 'backup_path' in locals() and backup_path:
            print(f"Restaurer depuis: {backup_path}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        update_trading_params()
    except KeyboardInterrupt:
        print("\n\nConfiguration annulée")
        sys.exit(0)
