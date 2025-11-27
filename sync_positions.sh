#!/bin/bash
# =============================================================================
# Script de Synchronisation Positions JSON <-> DB
# =============================================================================
# Nettoie les positions orphelines dans la DB qui n'ont plus de fichier JSON
# =============================================================================

set -e

DB_PATH="/home/basebot/trading-bot/data/trading.db"
JSON_DIR="/home/basebot/trading-bot/data"

echo "=========================================="
echo "🔄 Synchronisation Positions JSON ↔ DB"
echo "=========================================="

# Compter les positions dans la DB
DB_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM trade_history WHERE exit_time IS NULL;")
echo "📊 Positions dans la DB: $DB_COUNT"

# Compter les fichiers JSON
JSON_COUNT=$(ls -1 "$JSON_DIR"/position_*.json 2>/dev/null | wc -l)
echo "📁 Fichiers JSON: $JSON_COUNT"

if [ "$DB_COUNT" -eq "$JSON_COUNT" ]; then
    echo "✅ Déjà synchronisé!"
    exit 0
fi

echo ""
echo "⚠️  Désynchronisation détectée!"
echo ""

# Lister les adresses dans les JSON
echo "🔍 Analyse des fichiers JSON..."
JSON_ADDRESSES=()
for json_file in "$JSON_DIR"/position_*.json; do
    if [ -f "$json_file" ]; then
        # Extraire l'adresse du nom de fichier
        addr=$(basename "$json_file" | sed 's/position_//' | sed 's/.json//')
        JSON_ADDRESSES+=("$addr")
        echo "  ✓ $addr"
    fi
done

# Lister les positions dans la DB
echo ""
echo "🔍 Positions dans la DB..."
sqlite3 "$DB_PATH" << SQL
SELECT token_address, symbol FROM trade_history WHERE exit_time IS NULL;
SQL

echo ""
echo "🧹 Nettoyage des positions orphelines..."

# Créer une liste SQL des adresses valides
if [ ${#JSON_ADDRESSES[@]} -eq 0 ]; then
    # Aucun JSON = supprimer toutes les positions ouvertes
    echo "❌ Aucun fichier JSON trouvé - Suppression de toutes les positions ouvertes"
    sqlite3 "$DB_PATH" "DELETE FROM trade_history WHERE exit_time IS NULL;"
else
    # Construire la clause WHERE
    WHERE_CLAUSE=""
    for addr in "${JSON_ADDRESSES[@]}"; do
        if [ -z "$WHERE_CLAUSE" ]; then
            WHERE_CLAUSE="token_address != '$addr'"
        else
            WHERE_CLAUSE="$WHERE_CLAUSE AND token_address != '$addr'"
        fi
    done

    # Supprimer les positions qui ne sont pas dans les JSON
    DELETED=$(sqlite3 "$DB_PATH" "DELETE FROM trade_history WHERE exit_time IS NULL AND $WHERE_CLAUSE; SELECT changes();")
    echo "🗑️  Positions supprimées: $DELETED"
fi

# Vérifier le résultat
NEW_DB_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM trade_history WHERE exit_time IS NULL;")
echo ""
echo "=========================================="
echo "✅ Synchronisation terminée!"
echo "=========================================="
echo "Avant: $DB_COUNT positions en DB"
echo "Après: $NEW_DB_COUNT positions en DB"
echo "JSON:  $JSON_COUNT fichiers"
echo ""

if [ "$NEW_DB_COUNT" -eq "$JSON_COUNT" ]; then
    echo "✅ Parfaitement synchronisé!"
else
    echo "⚠️  Toujours désynchronisé - redémarrage du Trader recommandé"
fi
