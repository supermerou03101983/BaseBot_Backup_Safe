#!/bin/bash
set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
TEMP_CRON="/tmp/cron_setup_$$_$(date +%s).tmp"
BOT_DIR="/home/basebot/trading-bot"

echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Configuration Complète des Tâches Planifiées    ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""

# Vérifier l'existence des scripts requis
MISSING_SCRIPTS=()

[[ ! -f "$BOT_DIR/maintenance_weekly.sh" ]] && MISSING_SCRIPTS+=("maintenance_weekly.sh")
[[ ! -f "$BOT_DIR/maintenance_monthly.sh" ]] && MISSING_SCRIPTS+=("maintenance_monthly.sh")
[[ ! -f "$BOT_DIR/daily_report_telegram.sh" ]] && MISSING_SCRIPTS+=("daily_report_telegram.sh")

if [ ${#MISSING_SCRIPTS[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Scripts manquants détectés:${NC}"
    for script in "${MISSING_SCRIPTS[@]}"; do
        echo "    - $script"
    done
    echo -e "${YELLOW}Ces scripts doivent être créés avant de continuer.${NC}"
    read -p "Continuer quand même? (y/n): " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
fi

# Sauvegarder le crontab actuel
echo "📁 Sauvegarde du crontab existant..."
if crontab -l > "$TEMP_CRON" 2>/dev/null; then
    echo -e "${GREEN}✓ Crontab actuel sauvegardé${NC}"
    # Créer une copie de sauvegarde datée
    cp "$TEMP_CRON" "$BOT_DIR/logs/crontab_backup_$(date +%Y%m%d_%H%M%S).txt"
else
    touch "$TEMP_CRON"
    echo -e "${YELLOW}○ Pas de crontab existant, création d'un nouveau${NC}"
fi

# Fonction pour ajouter une tâche cron
add_cron_job() {
    local schedule="$1"
    local command="$2"
    local description="$3"
    local category="$4"
    
    # Extraire le nom du script pour la détection de doublons
    local script_name=$(basename "$command" | cut -d' ' -f1)
    
    # Supprimer toutes les anciennes entrées pour ce script
    if grep -q "$script_name" "$TEMP_CRON"; then
        echo -e "${YELLOW}  ↻ Mise à jour: $description${NC}"
        grep -v "$script_name" "$TEMP_CRON" > "${TEMP_CRON}.new"
        mv "${TEMP_CRON}.new" "$TEMP_CRON"
    fi
    
    # Ajouter la nouvelle tâche
    echo "$schedule $command" >> "$TEMP_CRON"
    echo -e "${GREEN}  ✓ $description${NC}"
}

echo ""
echo "🔧 Configuration des tâches de maintenance"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Maintenance hebdomadaire - Dimanche à 2h00
add_cron_job \
    "0 2 * * 0" \
    /home/basebot/trading-bot/maintenance_weekly.sh >> /home/basebot/trading-bot/logs/cron.log 2>&1 \
    "Maintenance hebdomadaire (Dimanche 2h00)" \
    "maintenance"

# Maintenance mensuelle - Premier jour du mois à 3h00
add_cron_job \
    "0 3 1 * *" \
    /home/basebot/trading-bot/maintenance_monthly.sh >> /home/basebot/trading-bot/logs/cron.log 2>&1
 \
    "Maintenance mensuelle (1er du mois 3h00)" \
    "maintenance"

echo ""
echo "📊 Configuration des rapports Telegram"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Rapport du matin (8h00)
add_cron_job \
    "0 8 * * *" \
    /home/basebot/trading-bot/daily_report_telegram.sh morning >> /home/basebot/trading-bot/logs/reports.log 2>&1 \
    "Rapport du matin (8h00)" \
    "report"

# Rapport du midi (12h00)
add_cron_job \
    "0 12 * * *" \
    /home/basebot/trading-bot/daily_report_telegram.sh midday >> /home/basebot/trading-bot/logs/reports.log 2>&1 \
    "Rapport de midi (12h00)" \
    "report"

# Rapport du soir (20h00)
add_cron_job \
    "0 20 * * *" \
    /home/basebot/trading-bot/daily_report_telegram.sh evening >> /home/basebot/trading-bot/logs/reports.log 2>&1
 \
    "Rapport du soir (20h00)" \
    "report"

# Rapport hebdomadaire (Lundi 9h00)
add_cron_job \
    "0 9 * * 1" \
    /home/basebot/trading-bot/daily_report_telegram.sh weekly >> /home/basebot/trading-bot/logs/reports.log 2>&1
 \
    "Rapport hebdomadaire (Lundi 9h00)" \
    "report"

echo ""
echo "🔍 Validation et installation..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Valider et installer le nouveau crontab
if crontab "$TEMP_CRON" 2>/dev/null; then
    echo -e "${GREEN}✅ Toutes les tâches cron ont été installées avec succès!${NC}"
    rm -f "$TEMP_CRON"
    
    echo ""
    echo "📅 RÉSUMÉ DES TÂCHES PLANIFIÉES"
    echo "════════════════════════════════"
    echo ""
    echo "🔧 MAINTENANCE:"
    echo "  • Dimanche 02h00 : Maintenance hebdomadaire (logs, backups)"
    echo "  • 1er du mois 03h00 : Maintenance mensuelle (archivage, stats)"
    echo ""
    echo "📊 RAPPORTS TELEGRAM:"
    echo "  • Tous les jours 08h00 : Rapport du matin"
    echo "  • Tous les jours 12h00 : Rapport de midi"
    echo "  • Tous les jours 20h00 : Rapport du soir"
    echo "  • Lundi 09h00 : Rapport hebdomadaire détaillé"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📝 Tâches installées dans le crontab:"
    echo ""
    crontab -l | grep trading-bot | while read -r line; do
        echo "  $line"
    done
    echo ""
    echo "🛠️ COMMANDES UTILES:"
    echo "  Voir toutes les tâches :  crontab -l"
    echo "  Éditer les tâches :       crontab -e"
    echo "  Supprimer les tâches :    crontab -r"
    echo "  Logs de maintenance :     tail -f $BOT_DIR/logs/cron.log"
    echo "  Logs des rapports :       tail -f $BOT_DIR/logs/reports.log"
    echo ""
    echo "💡 CONSEIL: Pour tester un rapport manuellement:"
    echo "  $BOT_DIR/daily_report_telegram.sh morning"
    
else
    echo -e "${RED}❌ Erreur lors de l'installation du crontab${NC}"
    echo "Le fichier temporaire a été conservé : $TEMP_CRON"
    echo ""
    echo "Débogage:"
    echo "1. Vérifiez la syntaxe : crontab $TEMP_CRON"
    echo "2. Consultez les erreurs : tail /var/log/syslog | grep cron"
    exit 1
fi
