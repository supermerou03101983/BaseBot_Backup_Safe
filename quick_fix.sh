#!/bin/bash
# Script de dépannage rapide pour débloquer le bot

echo "=========================================="
echo "🔧 DÉPANNAGE RAPIDE - BASE BOT"
echo "=========================================="
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Vérifier si le processus tourne
echo "📊 Vérification du processus..."
PID=$(pgrep -f "Trader.py")

if [ -z "$PID" ]; then
    echo -e "${RED}❌ Processus Trader.py non trouvé${NC}"
    echo ""
    echo "Le bot n'est pas actif. Options:"
    echo "  1. Lancer le diagnostic: python3 diagnose_freeze.py"
    echo "  2. Démarrer le bot: python3 src/Trader.py"
else
    echo -e "${GREEN}✅ Processus actif (PID: $PID)${NC}"
    echo ""

    # Vérifier depuis combien de temps
    RUNNING_TIME=$(ps -p $PID -o etime= | tr -d ' ')
    echo "⏱️  Temps d'exécution: $RUNNING_TIME"

    # Vérifier CPU/RAM
    CPU=$(ps -p $PID -o %cpu= | tr -d ' ')
    MEM=$(ps -p $PID -o %mem= | tr -d ' ')
    echo "💻 CPU: ${CPU}% | RAM: ${MEM}%"

    if (( $(echo "$CPU < 1" | bc -l) )); then
        echo -e "${YELLOW}⚠️  CPU très faible - bot possiblement bloqué${NC}"
    fi
fi

echo ""
echo "=========================================="

# 2. Vérifier les derniers logs
echo "📜 Dernières lignes de logs:"
echo ""
if [ -f "logs/trading.log" ]; then
    tail -10 logs/trading.log
    echo ""

    # Dernière activité
    LAST_LOG=$(tail -1 logs/trading.log | cut -d' ' -f1-2)
    echo "🕐 Dernière activité: $LAST_LOG"
else
    echo -e "${RED}❌ Fichier logs/trading.log introuvable${NC}"
fi

echo ""
echo "=========================================="

# 3. Vérifier les positions ouvertes
echo "💼 Positions ouvertes:"
echo ""
if [ -f "data/trading.db" ]; then
    OPEN_POS=$(sqlite3 data/trading.db "SELECT COUNT(*) FROM trade_history WHERE exit_time IS NULL;")
    echo "Positions ouvertes: $OPEN_POS"

    if [ "$OPEN_POS" -gt 0 ]; then
        echo ""
        echo "Détails:"
        sqlite3 -header -column data/trading.db "SELECT symbol, entry_time, amount_in FROM trade_history WHERE exit_time IS NULL;"
    fi
else
    echo -e "${RED}❌ Base de données introuvable${NC}"
fi

echo ""
echo "=========================================="
echo "💡 ACTIONS RECOMMANDÉES:"
echo "=========================================="

if [ ! -z "$PID" ] && (( $(echo "$CPU < 1" | bc -l) )); then
    echo ""
    echo -e "${YELLOW}Le bot semble freezé (processus actif mais CPU faible)${NC}"
    echo ""
    echo "1. Diagnostic complet:"
    echo "   python3 diagnose_freeze.py"
    echo ""
    echo "2. Redémarrer le bot:"
    echo "   pkill -f Trader.py && sleep 5 && python3 src/Trader.py"
    echo ""
    echo "3. Si problème persiste, fermeture d'urgence:"
    echo "   python3 emergency_close_positions.py"
elif [ -z "$PID" ]; then
    echo ""
    echo "1. Lancer le diagnostic:"
    echo "   python3 diagnose_freeze.py"
    echo ""
    echo "2. Redémarrer le bot:"
    echo "   python3 src/Trader.py"
else
    echo ""
    echo -e "${GREEN}Le bot semble fonctionner normalement${NC}"
    echo ""
    echo "Pour monitoring détaillé:"
    echo "   tail -f logs/trading.log"
fi

echo ""
echo "=========================================="
