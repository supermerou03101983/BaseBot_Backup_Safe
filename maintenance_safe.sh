#!/bin/bash
# =============================================================================
# Script de Maintenance Safe - BaseBot Trading
# =============================================================================
# Ce script effectue la maintenance SANS redémarrer le Trader
# → Préserve les trailing stops et les positions actives
# =============================================================================

set -e

LOG_FILE="/home/basebot/trading-bot/logs/maintenance.log"
DB_FILE="/home/basebot/trading-bot/data/trading.db"
BACKUP_DIR="/home/basebot/trading-bot/data/backups"

# Créer le répertoire de backups si nécessaire
mkdir -p "$BACKUP_DIR"

# S'assurer que les logs appartiennent à basebot (évite les problèmes de permissions)
touch "$LOG_FILE"
chown basebot:basebot "$LOG_FILE" 2>/dev/null || true

# Fonction de log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "======================================================================"
log "📊 Début de la maintenance safe (pas de redémarrage services)"
log "======================================================================"

# =============================================================================
# 1. Vérifier les positions ouvertes (info uniquement)
# =============================================================================
log "📈 Vérification des positions actives..."
OPEN_POSITIONS=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM trade_history WHERE exit_time IS NULL;" 2>/dev/null || echo "0")
log "Positions actuellement ouvertes: $OPEN_POSITIONS"

if [ "$OPEN_POSITIONS" -gt 0 ]; then
    log "⚠️  Le Trader ne sera PAS redémarré (préservation des trailing stops)"
fi

# =============================================================================
# 2. Archivage des vieux trades (> 30 jours)
# =============================================================================
log "🗄️  Archivage des trades de plus de 30 jours..."

sqlite3 "$DB_FILE" << 'SQL' 2>/dev/null || log "⚠️  Erreur lors de l'archivage"
-- Créer la table d'archive si elle n'existe pas
CREATE TABLE IF NOT EXISTS trade_history_archive (
    id INTEGER,
    token_address TEXT,
    symbol TEXT,
    side TEXT,
    amount_in REAL,
    amount_out REAL,
    price REAL,
    gas_used REAL,
    profit_loss REAL,
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    timestamp TIMESTAMP,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Archiver les trades de plus de 30 jours
INSERT INTO trade_history_archive
SELECT *, CURRENT_TIMESTAMP FROM trade_history
WHERE timestamp < datetime('now', '-30 days')
AND id NOT IN (SELECT id FROM trade_history_archive);

-- Supprimer les trades archivés de la table principale
DELETE FROM trade_history
WHERE timestamp < datetime('now', '-30 days')
AND exit_time IS NOT NULL;  -- Ne supprimer QUE les positions fermées

-- Nettoyer les rejected_tokens de plus de 60 jours
DELETE FROM rejected_tokens WHERE rejected_at < datetime('now', '-60 days');

-- Nettoyer les discovered_tokens de plus de 7 jours (garde les récents)
DELETE FROM discovered_tokens
WHERE created_at < datetime('now', '-7 days')
AND token_address NOT IN (SELECT token_address FROM approved_tokens)
AND token_address NOT IN (SELECT token_address FROM trade_history WHERE exit_time IS NULL);

-- Optimiser les performances
VACUUM;
ANALYZE;
SQL

ARCHIVED_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM trade_history_archive;" 2>/dev/null || echo "0")
log "✅ Archivage terminé: $ARCHIVED_COUNT trades archivés au total"

# =============================================================================
# 3. Backup de la base de données
# =============================================================================
log "💾 Backup de la base de données..."
BACKUP_FILE="$BACKUP_DIR/trading_$(date +%Y%m%d_%H%M%S).db"
cp "$DB_FILE" "$BACKUP_FILE"
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log "✅ Backup créé: $BACKUP_FILE ($BACKUP_SIZE)"

# =============================================================================
# 4. Nettoyage des vieux backups (> 60 jours)
# =============================================================================
log "🧹 Nettoyage des vieux backups..."
DELETED_BACKUPS=$(find "$BACKUP_DIR" -name "trading_*.db" -mtime +60 2>/dev/null | wc -l)
find "$BACKUP_DIR" -name "trading_*.db" -mtime +60 -delete 2>/dev/null || true
log "✅ $DELETED_BACKUPS vieux backups supprimés (> 60 jours)"

# =============================================================================
# 5. Nettoyage des vieux logs (> 30 jours)
# =============================================================================
log "🧹 Nettoyage des vieux logs..."
find /home/basebot/trading-bot/logs/ -name "*.log" -mtime +30 -size +100M -delete 2>/dev/null || true
log "✅ Vieux logs nettoyés"

# =============================================================================
# 6. Génération des statistiques mensuelles
# =============================================================================
log "📊 Génération des statistiques mensuelles..."
STATS_FILE="/home/basebot/trading-bot/logs/stats_$(date +%Y%m).txt"

# Créer le fichier et définir les bonnes permissions
touch "$STATS_FILE"
chown basebot:basebot "$STATS_FILE" 2>/dev/null || true

sqlite3 "$DB_FILE" << 'SQL' > "$STATS_FILE" 2>/dev/null || log "⚠️  Erreur statistiques"
.headers on
.mode column

-- ==========================================
-- STATISTIQUES DU MOIS EN COURS
-- ==========================================

SELECT '=== RÉSUMÉ DU MOIS ===' as '';

SELECT
    COUNT(*) as total_trades,
    COUNT(CASE WHEN profit_loss > 0 THEN 1 END) as winning_trades,
    COUNT(CASE WHEN profit_loss < 0 THEN 1 END) as losing_trades,
    ROUND(100.0 * COUNT(CASE WHEN profit_loss > 0 THEN 1 END) / COUNT(*), 1) || '%' as win_rate,
    ROUND(SUM(profit_loss), 2) as total_profit,
    ROUND(AVG(profit_loss), 2) as avg_profit,
    ROUND(MAX(profit_loss), 2) as best_trade,
    ROUND(MIN(profit_loss), 2) as worst_trade
FROM trade_history
WHERE timestamp >= datetime('now', 'start of month')
AND exit_time IS NOT NULL;

SELECT '' as '';
SELECT '=== TOP 10 TOKENS DU MOIS ===' as '';

SELECT
    symbol,
    COUNT(*) as trades,
    ROUND(AVG(profit_loss), 2) as avg_profit,
    ROUND(SUM(profit_loss), 2) as total_profit
FROM trade_history
WHERE timestamp >= datetime('now', 'start of month')
AND exit_time IS NOT NULL
GROUP BY symbol
ORDER BY total_profit DESC
LIMIT 10;

SELECT '' as '';
SELECT '=== POSITIONS ACTUELLEMENT OUVERTES ===' as '';

SELECT
    symbol,
    ROUND(amount_in, 2) as amount,
    ROUND(price, 8) as entry_price,
    strftime('%Y-%m-%d %H:%M', entry_time) as opened_at
FROM trade_history
WHERE exit_time IS NULL
ORDER BY entry_time DESC;
SQL

if [ -f "$STATS_FILE" ]; then
    log "✅ Statistiques générées: $STATS_FILE"
else
    log "⚠️  Erreur génération statistiques"
fi

# =============================================================================
# 7. Vérification espace disque
# =============================================================================
log "💾 Vérification espace disque..."
DISK_USAGE=$(df -h /home/basebot/trading-bot | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    log "⚠️  ATTENTION: Espace disque à ${DISK_USAGE}%"
else
    log "✅ Espace disque OK: ${DISK_USAGE}%"
fi

# =============================================================================
# 8. Vérification des services (sans redémarrage)
# =============================================================================
log "🔍 Vérification des services..."

for service in basebot-scanner basebot-filter basebot-trader basebot-dashboard; do
    if systemctl is-active --quiet "$service"; then
        log "✅ $service: ACTIF"
    else
        log "❌ $service: INACTIF"
    fi
done

# =============================================================================
# 9. Résumé final
# =============================================================================
log "======================================================================"
log "✅ Maintenance safe terminée avec succès"
log "======================================================================"
log "📊 Résumé:"
log "  - Positions ouvertes: $OPEN_POSITIONS"
log "  - Trades archivés: $ARCHIVED_COUNT"
log "  - Backup créé: $BACKUP_SIZE"
log "  - Espace disque: ${DISK_USAGE}%"
log "  - Services: Aucun redémarrage (trailing stops préservés)"
log "======================================================================"

exit 0
