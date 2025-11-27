#!/bin/bash
set -e

LOG_FILE="/home/basebot/trading-bot/logs/maintenance_monthly.log"
DB_FILE="/home/basebot/trading-bot/data/trading.db"

# Fonction de log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "📧 Début de la maintenance mensuelle"

# Vérifier les services actifs avant maintenance
SERVICES_RUNNING=""
for service in basebot-scanner basebot-filter basebot-trader basebot-dashboard; do
    if systemctl is-active --quiet "$service"; then
        SERVICES_RUNNING="$SERVICES_RUNNING $service"
    fi
done

# 1. Archiver les vieux trades
log "Archivage des trades de plus de 30 jours..."
sqlite3 "$DB_FILE" << SQL 2>/dev/null || log "⚠️  Erreur lors de l'archivage"
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
    timestamp TIMESTAMP,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Archiver les trades de plus de 30 jours
INSERT INTO trade_history_archive 
SELECT *, CURRENT_TIMESTAMP FROM trade_history 
WHERE timestamp < datetime('now', '-30 days')
AND token_address || timestamp NOT IN (
    SELECT token_address || timestamp FROM trade_history_archive
);

-- Supprimer les trades archivés
DELETE FROM trade_history WHERE timestamp < datetime('now', '-30 days');

-- Nettoyer les rejected_tokens de plus de 60 jours
DELETE FROM rejected_tokens WHERE rejected_at < datetime('now', '-60 days');

-- Analyser les tables pour optimiser les performances
ANALYZE;
SQL
log "✅ Archivage terminé"

# 2. Statistiques mensuelles
log "Génération des statistiques mensuelles..."
sqlite3 "$DB_FILE" << SQL > "/home/basebot/trading-bot/logs/stats_$(date +%Y%m).txt"
.headers on
.mode column

-- Résumé du mois
SELECT 
    COUNT(*) as total_trades,
    COUNT(CASE WHEN profit_loss > 0 THEN 1 END) as winning_trades,
    ROUND(AVG(profit_loss), 2) as avg_profit,
    ROUND(MAX(profit_loss), 2) as best_trade,
    ROUND(MIN(profit_loss), 2) as worst_trade
FROM trade_history
WHERE timestamp >= datetime('now', 'start of month');

-- Tokens les plus tradés
SELECT symbol, COUNT(*) as trades, ROUND(AVG(profit_loss), 2) as avg_profit
FROM trade_history
WHERE timestamp >= datetime('now', 'start of month')
GROUP BY symbol
ORDER BY trades DESC
LIMIT 10;
SQL
log "✅ Statistiques générées"

# 3. Vérifier les mises à jour de sécurité uniquement
log "Vérification des mises à jour de sécurité..."
sudo apt update > /dev/null 2>&1
SECURITY_UPDATES=$(apt list --upgradable 2>/dev/null | grep -i security | wc -l)
if [ "$SECURITY_UPDATES" -gt 0 ]; then
    log "⚠️  $SECURITY_UPDATES mises à jour de sécurité disponibles"
    log "Exécutez: sudo apt upgrade"
else
    log "✅ Système à jour"
fi

# 4. Redémarrer les services qui étaient actifs
if [ -n "$SERVICES_RUNNING" ]; then
    log "Redémarrage des services..."
    for service in $SERVICES_RUNNING; do
        sudo systemctl restart "$service" && log "✅ $service redémarré"
        sleep 2
    done
else
    log "ℹ️  Aucun service à redémarrer"
fi

log "✅ Maintenance mensuelle terminée"
