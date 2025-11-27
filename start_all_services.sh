#!/bin/bash

# =============================================================================
# Script pour démarrer tous les services BaseBot
# =============================================================================

# Couleurs
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}🚀 Démarrage de tous les services BaseBot...${NC}\n"

# Vérifier si on est root
if [[ $EUID -ne 0 ]]; then
   echo -e "${YELLOW}Ce script nécessite les droits root${NC}"
   echo "Utilisez: sudo $0"
   exit 1
fi

# Activer et démarrer tous les services
services=(
    "basebot-scanner"
    "basebot-filter"
    "basebot-trader"
    "basebot-dashboard"
)

for service in "${services[@]}"; do
    echo -e "${CYAN}▶ Activation de $service...${NC}"
    systemctl enable $service.service

    echo -e "${CYAN}▶ Démarrage de $service...${NC}"
    systemctl start $service.service

    # Vérifier le statut
    if systemctl is-active --quiet $service.service; then
        echo -e "${GREEN}✓ $service est actif${NC}\n"
    else
        echo -e "${YELLOW}⚠ Problème avec $service${NC}"
        echo "Voir les logs: journalctl -u $service -n 50"
        echo ""
    fi
done

echo -e "${GREEN}✅ Tous les services ont été démarrés !${NC}\n"

echo -e "${CYAN}📊 Statut des services:${NC}"
systemctl status basebot-scanner --no-pager -l | head -3
systemctl status basebot-filter --no-pager -l | head -3
systemctl status basebot-trader --no-pager -l | head -3
systemctl status basebot-dashboard --no-pager -l | head -3

echo ""
echo -e "${CYAN}🔍 Commandes utiles:${NC}"
echo "  Voir tous les statuts:  systemctl status basebot-*"
echo "  Arrêter tous:           systemctl stop basebot-*"
echo "  Logs Scanner:           journalctl -u basebot-scanner -f"
echo "  Logs Filter:            journalctl -u basebot-filter -f"
echo "  Logs Trader:            journalctl -u basebot-trader -f"
echo "  Logs Dashboard:         journalctl -u basebot-dashboard -f"
echo ""
