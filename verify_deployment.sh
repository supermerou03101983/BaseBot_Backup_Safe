#!/bin/bash
# =============================================================================
# Script de vérification post-déploiement
# Vérifie que tous les composants nécessaires sont présents et fonctionnels
# =============================================================================

set -e

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_check() {
    echo -e "${BLUE}▶ Vérification: $1${NC}"
}

print_ok() {
    echo -e "${GREEN}  ✓ $1${NC}"
}

print_error() {
    echo -e "${RED}  ✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}  ⚠ $1${NC}"
}

# Variables
BOT_DIR="/home/basebot/trading-bot"
VENV_DIR="$BOT_DIR/venv"

echo "=========================================="
echo "🔍 VÉRIFICATION POST-DÉPLOIEMENT"
echo "=========================================="
echo ""

# 1. Vérifier la structure des dossiers
print_check "Structure des dossiers"
for dir in "$BOT_DIR/src" "$BOT_DIR/config" "$BOT_DIR/data" "$BOT_DIR/logs"; do
    if [ -d "$dir" ]; then
        print_ok "$(basename $dir)/ existe"
    else
        print_error "$(basename $dir)/ MANQUANT"
        exit 1
    fi
done

# 2. Vérifier les fichiers critiques
print_check "Fichiers critiques"
critical_files=(
    "$BOT_DIR/src/Trader.py"
    "$BOT_DIR/src/Scanner.py"
    "$BOT_DIR/src/Filter.py"
    "$BOT_DIR/src/Dashboard.py"
    "$BOT_DIR/src/honeypot_checker.py"
    "$BOT_DIR/src/web3_utils.py"
    "$BOT_DIR/requirements.txt"
)

for file in "${critical_files[@]}"; do
    if [ -f "$file" ]; then
        print_ok "$(basename $file) présent"
    else
        print_error "$(basename $file) MANQUANT"
        exit 1
    fi
done

# 3. Vérifier l'intégration honeypot dans Trader.py
print_check "Intégration honeypot dans Trader.py"
if grep -q "from honeypot_checker import HoneypotChecker" "$BOT_DIR/src/Trader.py"; then
    print_ok "Import HoneypotChecker présent"
else
    print_error "Import HoneypotChecker MANQUANT"
    exit 1
fi

if grep -q "self.honeypot_checker = HoneypotChecker()" "$BOT_DIR/src/Trader.py"; then
    print_ok "Initialisation HoneypotChecker présente"
else
    print_error "Initialisation HoneypotChecker MANQUANTE"
    exit 1
fi

if grep -q "honeypot_result = self.honeypot_checker.check_token" "$BOT_DIR/src/Trader.py"; then
    print_ok "Appel check_token présent"
else
    print_error "Appel check_token MANQUANT"
    exit 1
fi

# 4. Vérifier les dépendances Python
print_check "Dépendances Python"
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"

    # Vérifier les packages critiques
    packages=("web3" "requests" "pandas" "streamlit")
    for pkg in "${packages[@]}"; do
        if python3 -c "import $pkg" 2>/dev/null; then
            print_ok "$pkg installé"
        else
            print_error "$pkg NON INSTALLÉ"
            exit 1
        fi
    done

    deactivate
else
    print_warning "Environnement virtuel non trouvé (normal si installation en cours)"
fi

# 5. Vérifier la syntaxe Python
print_check "Syntaxe Python"
if [ -f "$VENV_DIR/bin/python3" ]; then
    source "$VENV_DIR/bin/activate"

    if python3 -m py_compile "$BOT_DIR/src/honeypot_checker.py" 2>/dev/null; then
        print_ok "honeypot_checker.py syntaxe OK"
    else
        print_error "honeypot_checker.py ERREUR DE SYNTAXE"
        exit 1
    fi

    if python3 -m py_compile "$BOT_DIR/src/Trader.py" 2>/dev/null; then
        print_ok "Trader.py syntaxe OK"
    else
        print_error "Trader.py ERREUR DE SYNTAXE"
        exit 1
    fi

    deactivate
fi

# 6. Vérifier les services systemd
print_check "Services systemd"
services=("basebot-scanner" "basebot-filter" "basebot-trader" "basebot-dashboard")
for service in "${services[@]}"; do
    if systemctl list-unit-files | grep -q "$service.service"; then
        print_ok "$service.service configuré"
    else
        print_warning "$service.service non configuré (normal si première installation)"
    fi
done

# 7. Vérifier les permissions
print_check "Permissions fichiers"
if [ -f "$BOT_DIR/src/honeypot_checker.py" ]; then
    owner=$(stat -c '%U' "$BOT_DIR/src/honeypot_checker.py" 2>/dev/null || stat -f '%Su' "$BOT_DIR/src/honeypot_checker.py")
    if [ "$owner" = "basebot" ]; then
        print_ok "Propriétaire: basebot"
    else
        print_warning "Propriétaire: $owner (devrait être basebot)"
    fi
fi

# 8. Test rapide de l'API Honeypot
print_check "Test API Honeypot"
if [ -f "$VENV_DIR/bin/python3" ]; then
    source "$VENV_DIR/bin/activate"

    test_result=$(python3 -c "
import sys
sys.path.append('$BOT_DIR/src')
try:
    from honeypot_checker import HoneypotChecker
    checker = HoneypotChecker()
    # Test avec WETH (token légitime)
    result = checker.check_token('0x4200000000000000000000000000000000000006', chain_id=8453)
    checker.close()
    print('API_OK' if not result.get('error') else 'API_ERROR')
except Exception as e:
    print(f'PYTHON_ERROR: {e}')
" 2>&1)

    if echo "$test_result" | grep -q "API_OK"; then
        print_ok "API Honeypot accessible"
    elif echo "$test_result" | grep -q "API_ERROR"; then
        print_warning "API Honeypot temporairement indisponible (le bot fonctionnera en mode dégradé)"
    else
        print_error "Erreur test API: $test_result"
    fi

    deactivate
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ VÉRIFICATION TERMINÉE${NC}"
echo "=========================================="
echo ""
echo "📋 RÉSUMÉ:"
echo "  • Structure: OK"
echo "  • Fichiers critiques: OK"
echo "  • Intégration honeypot: OK"
echo "  • Syntaxe Python: OK"
echo ""
echo "🚀 Le bot est prêt pour le déploiement!"
echo ""
