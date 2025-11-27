#!/bin/bash

# =============================================================================
# Script pour arrêter tous les services BaseBot
# =============================================================================

# Couleurs
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${CYAN}🛑 Arrêt de tous les services BaseBot...${NC}\n"

# Vérifier si on est root
if [[ $EUID -ne 0 ]]; then
   echo -e "${YELLOW}Ce script nécessite les droits root${NC}"
   echo "Utilisez: sudo $0"
   exit 1
fi

# Arrêter tous les services
services=(
    "basebot-dashboard"
    "basebot-trader"
    "basebot-filter"
    "basebot-scanner"
)

for service in "${services[@]}"; do
    echo -e "${CYAN}▶ Arrêt de $service...${NC}"
    systemctl stop $service.service

    # Vérifier le statut
    if ! systemctl is-active --quiet $service.service; then
        echo -e "${GREEN}✓ $service est arrêté${NC}\n"
    else
        echo -e "${YELLOW}⚠ Problème pour arrêter $service${NC}\n"
    fi
done

echo -e "${GREEN}✅ Tous les services ont été arrêtés !${NC}\n"

echo -e "${CYAN}📊 Statut des services:${NC}"
systemctl status basebot-* --no-pager | grep -E "basebot-|Active:"

echo ""
echo -e "${CYAN}🔍 Pour redémarrer:${NC}"
echo "  sudo systemctl start basebot-scanner"
echo "  sudo systemctl start basebot-filter"
echo "  sudo systemctl start basebot-trader"
echo "  sudo systemctl start basebot-dashboard"
echo ""
echo "  Ou utilisez: sudo ./start_all_services.sh"
echo ""
