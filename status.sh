#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BOT_DIR="/home/basebot/trading-bot"

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}   Base Trading Bot  - Statut      ${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

# Statut des services
echo "📊 Services:"
services=("base-scanner" "base-filter" "base-trader" "base-dashboard")
for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        cpu=$(systemctl show "$service" --property=CPUUsageNSec --value)
        mem=$(systemctl show "$service" --property=MemoryCurrent --value)
        uptime=$(systemctl show "$service" --property=ActiveEnterTimestamp --value)
        echo -e "  $service: ${GREEN}● Actif${NC}"
        echo "    Démarré: $uptime"
        if [ "$mem" != "[not set]" ]; then
            mem_mb=$((mem / 1024 / 1024))
            echo "    Mémoire: ${mem_mb}MB"
        fi
    else
        echo -e "  $service: ${RED}● Inactif${NC}"
    fi
done

echo ""
echo "💾 Base de données:"
if [ -f "$BOT_DIR/data/trading.db" ]; then
    size=$(du -h "$BOT_DIR/data/trading.db" | cut -f1)
    echo -e "  Taille: $size"
    
    # Statistiques rapides
    if [ -f "$BOT_DIR/venv/bin/python" ]; then
        stats=$("$BOT_DIR/venv/bin/python" -c "
import sqlite3
conn = sqlite3.connect('$BOT_DIR/data/trading.db')
c = conn.cursor()
tokens = c.execute('SELECT COUNT(*) FROM discovered_tokens').fetchone()[0]
approved = c.execute('SELECT COUNT(*) FROM approved_tokens').fetchone()[0]
trades = c.execute('SELECT COUNT(*) FROM trade_history').fetchone()[0]
print(f'  Tokens découverts: {tokens}')
print(f'  Tokens approuvés: {approved}')
print(f'  Trades effectués: {trades}')
conn.close()
" 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo "$stats"
        fi
    fi
else
    echo -e "  ${RED}Base de données non trouvée${NC}"
fi

echo ""
echo "📁 Logs récents:"
if [ -d "$BOT_DIR/logs" ]; then
    for log in scanner filter trader; do
        if [ -f "$BOT_DIR/logs/${log}.log" ]; then
            lines=$(tail -1 "$BOT_DIR/logs/${log}.log" 2>/dev/null | cut -c1-60)
            if [ -n "$lines" ]; then
                echo "  ${log}: ${lines}..."
            fi
        fi
    done
else
    echo -e "  ${YELLOW}Dossier logs non trouvé${NC}"
fi

echo ""
echo "🔗 Liens utiles:"
echo "  Dashboard: http://localhost:8501"
echo "  Logs: tail -f $BOT_DIR/logs/*.log"
echo ""
