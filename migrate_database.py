#!/usr/bin/env python3
"""
Script de migration de la base de données
Corrige les noms de colonnes pour harmoniser Scanner/Filter
"""

import sqlite3
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / 'data' / 'trading.db'

def migrate_database():
    """Migre la base de données vers le nouveau schéma"""

    if not DB_PATH.exists():
        print("❌ Base de données non trouvée")
        print(f"   Chemin: {DB_PATH}")
        print("   Exécutez d'abord: python src/init_database.py")
        return False

    print(f"🔄 Migration de la base de données: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Vérifier les colonnes de discovered_tokens
        cursor.execute("PRAGMA table_info(discovered_tokens)")
        columns = {col[1] for col in cursor.fetchall()}

        print(f"\n📋 Colonnes actuelles de discovered_tokens: {columns}")

        # Migration: address -> token_address
        if 'address' in columns and 'token_address' not in columns:
            print("🔄 Migration: renommage de 'address' en 'token_address' dans discovered_tokens...")

            # Créer une nouvelle table avec le bon schéma
            cursor.execute('''
                CREATE TABLE discovered_tokens_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_address TEXT UNIQUE NOT NULL,
                    symbol TEXT,
                    name TEXT,
                    decimals INTEGER,
                    total_supply TEXT,
                    liquidity REAL DEFAULT 0,
                    market_cap REAL DEFAULT 0,
                    price_usd REAL DEFAULT 0,
                    price_eth REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Copier les données
            cursor.execute('''
                INSERT INTO discovered_tokens_new
                (id, token_address, symbol, name, decimals, total_supply, liquidity, market_cap, price_usd, price_eth, created_at)
                SELECT
                    id,
                    address,
                    symbol,
                    name,
                    decimals,
                    total_supply,
                    COALESCE(liquidity_usd, 0),
                    COALESCE(market_cap, 0),
                    COALESCE(price_usd, 0),
                    COALESCE(price_eth, 0),
                    COALESCE(discovered_at, created_at, CURRENT_TIMESTAMP)
                FROM discovered_tokens
            ''')

            # Supprimer l'ancienne table
            cursor.execute('DROP TABLE discovered_tokens')

            # Renommer la nouvelle table
            cursor.execute('ALTER TABLE discovered_tokens_new RENAME TO discovered_tokens')

            print("✅ Table discovered_tokens migrée")

        # Vérifier approved_tokens
        cursor.execute("PRAGMA table_info(approved_tokens)")
        columns = {col[1] for col in cursor.fetchall()}

        if 'address' in columns and 'token_address' not in columns:
            print("🔄 Migration: renommage de 'address' en 'token_address' dans approved_tokens...")

            cursor.execute('''
                CREATE TABLE approved_tokens_new (
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

            cursor.execute('''
                INSERT INTO approved_tokens_new
                (id, token_address, symbol, name, reason, score, analysis_data, created_at)
                SELECT
                    id,
                    address,
                    symbol,
                    name,
                    '',
                    COALESCE(risk_score, 0),
                    '',
                    COALESCE(approved_at, CURRENT_TIMESTAMP)
                FROM approved_tokens
            ''')

            cursor.execute('DROP TABLE approved_tokens')
            cursor.execute('ALTER TABLE approved_tokens_new RENAME TO approved_tokens')

            print("✅ Table approved_tokens migrée")

        # Vérifier rejected_tokens
        cursor.execute("PRAGMA table_info(rejected_tokens)")
        columns = {col[1] for col in cursor.fetchall()}

        if 'address' in columns and 'token_address' not in columns:
            print("🔄 Migration: renommage de 'address' en 'token_address' dans rejected_tokens...")

            cursor.execute('''
                CREATE TABLE rejected_tokens_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_address TEXT UNIQUE NOT NULL,
                    symbol TEXT,
                    name TEXT,
                    reason TEXT,
                    analysis_data TEXT,
                    rejected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                INSERT INTO rejected_tokens_new
                (id, token_address, symbol, name, reason, analysis_data, rejected_at)
                SELECT
                    id,
                    address,
                    symbol,
                    name,
                    COALESCE(reason, ''),
                    '',
                    COALESCE(rejected_at, CURRENT_TIMESTAMP)
                FROM rejected_tokens
            ''')

            cursor.execute('DROP TABLE rejected_tokens')
            cursor.execute('ALTER TABLE rejected_tokens_new RENAME TO rejected_tokens')

            print("✅ Table rejected_tokens migrée")

        # Vérifier trade_history
        cursor.execute("PRAGMA table_info(trade_history)")
        columns = {col[1] for col in cursor.fetchall()}

        if 'exit_time' not in columns:
            print("🔄 Ajout des colonnes entry_time et exit_time dans trade_history...")

            cursor.execute('''
                CREATE TABLE trade_history_new (
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

            # Copier les données existantes
            cursor.execute('''
                INSERT INTO trade_history_new
                (id, token_address, symbol, side, amount_in, amount_out, price, gas_used, profit_loss, timestamp, entry_time, exit_time)
                SELECT
                    id,
                    token_address,
                    symbol,
                    side,
                    COALESCE(amount_in, 0),
                    COALESCE(amount_out, 0),
                    COALESCE(price, 0),
                    COALESCE(gas_used, 0),
                    COALESCE(profit_loss, 0),
                    timestamp,
                    CASE WHEN side = 'BUY' THEN timestamp ELSE NULL END,
                    CASE WHEN side = 'SELL' THEN timestamp ELSE NULL END
                FROM trade_history
            ''')

            cursor.execute('DROP TABLE trade_history')
            cursor.execute('ALTER TABLE trade_history_new RENAME TO trade_history')

            print("✅ Table trade_history migrée")

        # Recréer les index
        print("🔄 Recréation des index...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_discovered_address ON discovered_tokens(token_address)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_discovered_created ON discovered_tokens(created_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_approved_address ON approved_tokens(token_address)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rejected_address ON rejected_tokens(token_address)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_history_token ON trade_history(token_address)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_history_exit ON trade_history(exit_time)')

        conn.commit()
        print("\n✅ Migration terminée avec succès!")

        # Afficher le résumé
        print("\n📊 Résumé de la base de données:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  • {table[0]}: {count} enregistrement(s)")

        return True

    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔧 MIGRATION DE LA BASE DE DONNÉES")
    print("=" * 50)

    if migrate_database():
        print("\n✅ La base de données est prête à être utilisée")
        print("   Vous pouvez maintenant redémarrer les services:")
        print("   • systemctl restart basebot-scanner")
        print("   • systemctl restart basebot-filter")
    else:
        print("\n❌ La migration a échoué")
        print("   Vérifiez les erreurs ci-dessus")
