#!/usr/bin/env python3
"""
Initialisation base de données avec toutes les tables nécessaires
"""

import sqlite3
import os
import json
from pathlib import Path
from datetime import datetime

# Utiliser le chemin relatif au projet
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / 'data' / 'trading.db'

def init_database():
    """Initialise la base de données complète avec toutes les tables"""
    # Créer le dossier si nécessaire
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Activer les foreign keys
    cursor.execute('PRAGMA foreign_keys = ON')
    
    # Table scanner_state
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scanner_state (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            last_block INTEGER DEFAULT 0,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Initialiser scanner_state
    cursor.execute('''
        INSERT OR IGNORE INTO scanner_state (id, last_block)
        VALUES (1, 0)
    ''')
    
    # Table discovered_tokens (schéma aligné avec Scanner.py et Filter.py)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS discovered_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_address TEXT UNIQUE NOT NULL,
            symbol TEXT,
            name TEXT,
            decimals INTEGER,
            total_supply TEXT,
            liquidity REAL DEFAULT 0,
            market_cap REAL DEFAULT 0,
            volume_24h REAL DEFAULT 0,
            price_usd REAL DEFAULT 0,
            price_eth REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table approved_tokens (schéma aligné avec filter.py et trader.py)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS approved_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_address TEXT UNIQUE NOT NULL,
            symbol TEXT,
            name TEXT,
            reason TEXT,
            score REAL,
            analysis_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table rejected_tokens (schéma aligné avec filter.py)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rejected_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_address TEXT UNIQUE NOT NULL,
            symbol TEXT,
            name TEXT,
            reason TEXT,
            analysis_data TEXT,
            rejected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table trade_history (schéma aligné avec trader.py)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_address TEXT NOT NULL,
            symbol TEXT,
            side TEXT,
            amount_in REAL,
            amount_out REAL,
            price REAL,
            gas_used REAL,
            profit_loss REAL,
            entry_time TIMESTAMP,
            exit_time TIMESTAMP,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table trade_log (schéma aligné avec trader.py)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            level TEXT,
            message TEXT,
            token_address TEXT,
            tx_hash TEXT,
            error_details TEXT
        )
    ''')
    
    # Table trailing_level_stats (schéma aligné avec trader.py)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trailing_level_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_address TEXT NOT NULL,
            level INTEGER,
            activation_price REAL,
            stop_loss_price REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table trading_config
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trading_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Initialiser les configurations par défaut
    default_configs = [
        # Configuration du scanner
        ('MAX_BLOCKS_PER_SCAN', '100'),
        ('SCAN_INTERVAL_SECONDS', '30'),
        
        # Configuration du filter
        ('MIN_AGE_HOURS', '2'),
        ('MIN_LIQUIDITY_USD', '30000'),
        ('MAX_LIQUIDITY_USD', '10000000'),
        ('MIN_VOLUME_24H', '50000'),
        ('MIN_HOLDERS', '150'),
        ('MAX_BUY_TAX', '5'),
        ('MAX_SELL_TAX', '5'),
        ('MIN_MARKET_CAP', '25000'),
        ('MAX_MARKET_CAP', '10000000'),
        ('MAX_SLIPPAGE', '3'),
        
        # Configuration du trader
        ('POSITION_SIZE_PERCENT', '15'),
        ('MAX_POSITIONS', '2'),
        ('MAX_TRADES_PER_DAY', '3'),
        ('STOP_LOSS_PERCENT', '5'),
        ('MONITORING_INTERVAL', '1'),
        ('TRAILING_ACTIVATION_THRESHOLD', '12'),
        ('TOKEN_APPROVAL_MAX_AGE_HOURS', '12'),  # Expiration des tokens approuvés
        
        # Time exit configuration
        ('TIME_EXIT_STAGNATION_HOURS', '24'),
        ('TIME_EXIT_STAGNATION_MIN_PROFIT', '5'),
        ('TIME_EXIT_LOW_MOMENTUM_HOURS', '48'),
        ('TIME_EXIT_LOW_MOMENTUM_MIN_PROFIT', '20'),
        ('TIME_EXIT_MAXIMUM_HOURS', '72'),
        ('TIME_EXIT_EMERGENCY_HOURS', '120')
    ]
    
    for key, value in default_configs:
        cursor.execute(
            "INSERT OR IGNORE INTO trading_config (key, value) VALUES (?, ?)",
            (key, value)
        )
    
    # Index pour performance optimale
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_discovered_address ON discovered_tokens(token_address)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_discovered_created ON discovered_tokens(created_at DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_approved_address ON approved_tokens(token_address)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rejected_address ON rejected_tokens(token_address)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_history_token ON trade_history(token_address)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_history_time ON trade_history(timestamp DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_log_time ON trade_log(timestamp DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trailing_token ON trailing_level_stats(token_address)')
    
    conn.commit()
    conn.close()
    
    print(f"✅ Base de données initialisée: {DB_PATH}")
    print(f"📊 Tables créées: 8")
    print(f"📈 Stratégie: Trailing 4 niveaux (12%, 30%, 100%, 300%)")
    print(f"⚙️ Configuration: 15% position, max 2 positions, 3 trades/jour")

if __name__ == "__main__":
    init_database()
    
    # Vérifier l'installation
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print(f"\n📋 Tables installées:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  - {table[0]}: {count} enregistrements")
    
    # Afficher la configuration
    print(f"\n⚙️ Configuration initiale:")
    cursor.execute("SELECT key, value FROM trading_config ORDER BY key")
    configs = cursor.fetchall()
    for key, value in configs:
        print(f"  - {key}: {value}")
    
    conn.close()
