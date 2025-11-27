#!/bin/bash
# =============================================================================
# Script de test du déploiement BaseBot
# =============================================================================
# À exécuter APRÈS le déploiement pour valider l'installation
# Usage: bash test_deploy.sh
# =============================================================================

set -e

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BOT_DIR="/home/basebot/trading-bot"
TESTS_PASSED=0
TESTS_FAILED=0

echo "=========================================="
echo "🧪 Tests de validation déploiement BaseBot"
echo "=========================================="
echo ""

# Fonction de test
test_check() {
    local test_name="$1"
    local command="$2"

    echo -n "Test: $test_name ... "
    if eval "$command" &>/dev/null; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

# =============================================================================
# Tests de structure
# =============================================================================

echo "📁 Tests de structure des fichiers"
echo "-----------------------------------"

test_check "Répertoire principal existe" "[ -d '$BOT_DIR' ]"
test_check "Répertoire logs existe" "[ -d '$BOT_DIR/logs' ]"
test_check "Répertoire data existe" "[ -d '$BOT_DIR/data' ]"
test_check "Répertoire config existe" "[ -d '$BOT_DIR/config' ]"
test_check "Répertoire venv existe" "[ -d '$BOT_DIR/venv' ]"
test_check "Répertoire src existe" "[ -d '$BOT_DIR/src' ]"

echo ""

# =============================================================================
# Tests de permissions
# =============================================================================

echo "🔐 Tests de permissions"
echo "-----------------------"

test_check "Répertoire appartient à basebot" "[ \$(stat -c '%U' '$BOT_DIR') = 'basebot' ]"
test_check "Logs appartient à basebot" "[ \$(stat -c '%U' '$BOT_DIR/logs') = 'basebot' ]"
test_check "Data appartient à basebot" "[ \$(stat -c '%U' '$BOT_DIR/data') = 'basebot' ]"
test_check "Logs est accessible en écriture" "su - basebot -c 'touch $BOT_DIR/logs/test.txt && rm $BOT_DIR/logs/test.txt'"

echo ""

# =============================================================================
# Tests des fichiers critiques
# =============================================================================

echo "📄 Tests des fichiers critiques"
echo "--------------------------------"

test_check "Scanner.py existe" "[ -f '$BOT_DIR/src/Scanner.py' ]"
test_check "Filter.py existe" "[ -f '$BOT_DIR/src/Filter.py' ]"
test_check "Trader.py existe" "[ -f '$BOT_DIR/src/Trader.py' ]"
test_check "Dashboard.py existe" "[ -f '$BOT_DIR/src/Dashboard.py' ]"
test_check "web3_utils.py existe" "[ -f '$BOT_DIR/src/web3_utils.py' ]"
test_check "init_database.py existe" "[ -f '$BOT_DIR/src/init_database.py' ]"
test_check ".env existe" "[ -f '$BOT_DIR/config/.env' ]"
test_check "requirements.txt existe" "[ -f '$BOT_DIR/requirements.txt' ]"

echo ""

# =============================================================================
# Tests de la base de données
# =============================================================================

echo "🗄️  Tests de la base de données"
echo "-------------------------------"

test_check "Base de données existe" "[ -f '$BOT_DIR/data/trading.db' ]"

if [ -f "$BOT_DIR/data/trading.db" ]; then
    test_check "Table discovered_tokens existe" "sqlite3 '$BOT_DIR/data/trading.db' 'SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"discovered_tokens\"' | grep -q discovered_tokens"
    test_check "Table approved_tokens existe" "sqlite3 '$BOT_DIR/data/trading.db' 'SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"approved_tokens\"' | grep -q approved_tokens"
    test_check "Table rejected_tokens existe" "sqlite3 '$BOT_DIR/data/trading.db' 'SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"rejected_tokens\"' | grep -q rejected_tokens"
    test_check "Table trade_history existe" "sqlite3 '$BOT_DIR/data/trading.db' 'SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"trade_history\"' | grep -q trade_history"
    test_check "Colonne token_address existe (discovered)" "sqlite3 '$BOT_DIR/data/trading.db' 'PRAGMA table_info(discovered_tokens)' | grep -q token_address"
    test_check "Colonne exit_time existe (trade_history)" "sqlite3 '$BOT_DIR/data/trading.db' 'PRAGMA table_info(trade_history)' | grep -q exit_time"
fi

echo ""

# =============================================================================
# Tests environnement Python
# =============================================================================

echo "🐍 Tests environnement Python"
echo "------------------------------"

test_check "Python venv activable" "su - basebot -c 'source $BOT_DIR/venv/bin/activate && python --version'"
test_check "Module web3 installé" "su - basebot -c 'source $BOT_DIR/venv/bin/activate && python -c \"import web3\"'"
test_check "Module requests installé" "su - basebot -c 'source $BOT_DIR/venv/bin/activate && python -c \"import requests\"'"
test_check "Module pandas installé" "su - basebot -c 'source $BOT_DIR/venv/bin/activate && python -c \"import pandas\"'"
test_check "Module streamlit installé" "su - basebot -c 'source $BOT_DIR/venv/bin/activate && python -c \"import streamlit\"'"

echo ""

# =============================================================================
# Tests services systemd
# =============================================================================

echo "⚙️  Tests services systemd"
echo "--------------------------"

test_check "Service scanner existe" "[ -f '/etc/systemd/system/basebot-scanner.service' ]"
test_check "Service filter existe" "[ -f '/etc/systemd/system/basebot-filter.service' ]"
test_check "Service trader existe" "[ -f '/etc/systemd/system/basebot-trader.service' ]"
test_check "Service dashboard existe" "[ -f '/etc/systemd/system/basebot-dashboard.service' ]"

echo ""

# =============================================================================
# Tests fonctionnels (si services démarrés)
# =============================================================================

echo "🔧 Tests fonctionnels (optionnels)"
echo "-----------------------------------"

if systemctl is-active --quiet basebot-scanner; then
    test_check "Service scanner actif" "systemctl is-active basebot-scanner"
    test_check "Logs scanner accessibles" "[ -f '$BOT_DIR/logs/scanner.log' ]"

    # Vérifier que le scanner a découvert des tokens (après quelques minutes)
    TOKEN_COUNT=$(sqlite3 "$BOT_DIR/data/trading.db" "SELECT COUNT(*) FROM discovered_tokens" 2>/dev/null || echo "0")
    if [ "$TOKEN_COUNT" -gt 0 ]; then
        echo -e "Test: Tokens découverts ($TOKEN_COUNT) ... ${GREEN}✅ PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "Test: Tokens découverts ($TOKEN_COUNT) ... ${YELLOW}⚠️  WARN (attendre quelques minutes)${NC}"
    fi
else
    echo -e "Test: Service scanner actif ... ${YELLOW}⚠️  NON DÉMARRÉ${NC}"
fi

if systemctl is-active --quiet basebot-filter; then
    test_check "Service filter actif" "systemctl is-active basebot-filter"
else
    echo -e "Test: Service filter actif ... ${YELLOW}⚠️  NON DÉMARRÉ${NC}"
fi

if systemctl is-active --quiet basebot-trader; then
    test_check "Service trader actif" "systemctl is-active basebot-trader"
else
    echo -e "Test: Service trader actif ... ${YELLOW}⚠️  NON DÉMARRÉ${NC}"
fi

if systemctl is-active --quiet basebot-dashboard; then
    test_check "Service dashboard actif" "systemctl is-active basebot-dashboard"
    test_check "Port 8501 ouvert" "netstat -tuln | grep -q ':8501'"
else
    echo -e "Test: Service dashboard actif ... ${YELLOW}⚠️  NON DÉMARRÉ${NC}"
fi

echo ""

# =============================================================================
# Tests de configuration
# =============================================================================

echo "⚙️  Tests de configuration"
echo "-------------------------"

if [ -f "$BOT_DIR/config/.env" ]; then
    # Vérifier que PRIVATE_KEY est configurée (pas la valeur par défaut)
    PRIVATE_KEY=$(grep "^PRIVATE_KEY=" "$BOT_DIR/config/.env" | cut -d'=' -f2)
    if [ -n "$PRIVATE_KEY" ] && [ "$PRIVATE_KEY" != "votre_private_key" ]; then
        echo -e "Test: PRIVATE_KEY configurée ... ${GREEN}✅ PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "Test: PRIVATE_KEY configurée ... ${RED}❌ FAIL (valeur par défaut)${NC}"
        ((TESTS_FAILED++))
    fi

    # Vérifier RPC_URL
    test_check "RPC_URL configurée" "grep -q '^RPC_URL=' '$BOT_DIR/config/.env'"
fi

echo ""

# =============================================================================
# Résumé
# =============================================================================

echo "=========================================="
echo "📊 Résumé des tests"
echo "=========================================="
echo ""
echo -e "${GREEN}Tests réussis: $TESTS_PASSED${NC}"
echo -e "${RED}Tests échoués: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Tous les tests sont passés !${NC}"
    echo ""
    echo "Prochaines étapes:"
    echo "1. Configurer le fichier .env si ce n'est pas fait"
    echo "2. Démarrer les services:"
    echo "   systemctl start basebot-scanner"
    echo "   systemctl start basebot-filter"
    echo "   systemctl start basebot-trader"
    echo "   systemctl start basebot-dashboard"
    echo "3. Vérifier les logs:"
    echo "   journalctl -u basebot-scanner -f"
    echo "4. Accéder au dashboard:"
    echo "   http://$(hostname -I | awk '{print $1}'):8501"
    exit 0
else
    echo -e "${RED}❌ Certains tests ont échoué${NC}"
    echo ""
    echo "Consultez la documentation:"
    echo "- TROUBLESHOOTING_SCANNER.md"
    echo "- FIXES_APPLIED.md"
    echo "- NEXT_STEPS.md"
    exit 1
fi
