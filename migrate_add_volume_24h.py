#!/usr/bin/env python3
"""
Migration: Ajout colonne volume_24h à la table discovered_tokens
"""

import sqlite3
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / 'data' / 'trading.db'

def migrate():
    """Ajoute la colonne volume_24h si elle n'existe pas"""
    print("🔄 Migration: Ajout colonne volume_24h...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Vérifier si la colonne existe déjà
    cursor.execute("PRAGMA table_info(discovered_tokens)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'volume_24h' in columns:
        print("✅ Colonne volume_24h existe déjà")
        conn.close()
        return

    # Ajouter la colonne
    try:
        cursor.execute("""
            ALTER TABLE discovered_tokens
            ADD COLUMN volume_24h REAL DEFAULT 0
        """)
        conn.commit()
        print("✅ Colonne volume_24h ajoutée avec succès")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        conn.rollback()
        conn.close()
        return

    # Vérifier le nouveau schéma
    cursor.execute("PRAGMA table_info(discovered_tokens)")
    columns = cursor.fetchall()

    print("\n📋 Nouveau schéma discovered_tokens:")
    for col in columns:
        col_id, name, col_type, notnull, default, pk = col
        print(f"  - {name}: {col_type} {'NOT NULL' if notnull else ''} {f'DEFAULT {default}' if default else ''}")

    conn.close()
    print("\n✅ Migration terminée")

if __name__ == "__main__":
    migrate()
