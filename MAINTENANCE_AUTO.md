# 🔧 Maintenance Automatique - BaseBot Trading

## ✅ Configuration Automatique

La maintenance est **100% automatique** dès l'installation via `deploy.sh`.

Aucune intervention manuelle n'est requise - le bot tourne 24h/24, 7j/7.

---

## 📅 Planning de Maintenance

### 1. Backup Quotidien (2h du matin)

**Fréquence:** Tous les jours à 2h00 UTC

**Actions:**
- ✅ Copie complète de `trading.db`
- ✅ Sauvegarde dans `/home/basebot/trading-bot/data/backups/`
- ✅ Format: `trading_YYYYMMDD.db`

**Durée:** ~10 secondes
**Impact:** ❌ Aucun (lecture seule de la DB)
**Redémarrage services:** ❌ Non

```bash
# Cron job:
0 2 * * * cp /home/basebot/trading-bot/data/trading.db /home/basebot/trading-bot/data/backups/trading_$(date +\%Y\%m\%d).db
```

---

### 2. Nettoyage Logs (1h du matin)

**Fréquence:** Tous les jours à 1h00 UTC

**Actions:**
- ✅ Supprime les logs > 500 MB
- ✅ Libère de l'espace disque

**Durée:** ~5 secondes
**Impact:** ❌ Aucun
**Redémarrage services:** ❌ Non

```bash
# Cron job:
0 1 * * * find /home/basebot/trading-bot/logs/ -name "*.log" -size +500M -delete
```

---

### 3. Maintenance Hebdomadaire (Dimanche 3h)

**Fréquence:** Tous les dimanches à 3h00 UTC

**Actions:**
- ✅ Archivage trades > 30 jours
- ✅ Backup base de données
- ✅ Nettoyage vieux backups (> 60 jours)
- ✅ Nettoyage discovered_tokens > 7 jours
- ✅ Optimisation DB (VACUUM, ANALYZE)
- ✅ Génération statistiques
- ✅ Vérification espace disque
- ✅ Vérification statut services

**Durée:** ~2-3 minutes
**Impact:** ❌ Minimal (DB en lecture/écriture)
**Redémarrage services:** ❌ **NON - Trailing stops préservés**

```bash
# Cron job:
0 3 * * 0 /home/basebot/trading-bot/maintenance_safe.sh
```

---

### 4. Maintenance Mensuelle (1er du mois 4h)

**Fréquence:** Le 1er de chaque mois à 4h00 UTC

**Actions:**
- ✅ **Identiques à la maintenance hebdomadaire**
- ✅ Génération rapport mensuel détaillé
- ✅ Statistiques complètes du mois
- ✅ Top 10 tokens tradés

**Durée:** ~3-5 minutes
**Impact:** ❌ Minimal
**Redémarrage services:** ❌ **NON - Trailing stops préservés**

```bash
# Cron job:
0 4 1 * * /home/basebot/trading-bot/maintenance_safe.sh
```

---

## 🛡️ Protection des Trailing Stops

### ⚠️ IMPORTANT: Aucun Redémarrage du Trader

Le script `maintenance_safe.sh` est conçu pour **NE JAMAIS redémarrer le service Trader**.

**Pourquoi?**
- Les trailing stops sont stockés **en mémoire** (Python)
- Un redémarrage les réinitialiserait
- Vous perdriez la protection gagnée (ex: stop à +15% reviendrait à -5%)

**Ce qui est préservé:**
- ✅ Positions ouvertes (dans la DB)
- ✅ Trailing stops actifs (en mémoire)
- ✅ Niveaux de trailing (1, 2, 3, 4)
- ✅ Prix max atteints

---

## 📊 Ce qui est Archivé/Nettoyé

### Archivage Automatique

| Données | Condition | Destination |
|---------|-----------|-------------|
| Trades fermés | > 30 jours | `trade_history_archive` |
| Rejected tokens | > 60 jours | Supprimés |
| Discovered tokens | > 7 jours (non tradés) | Supprimés |
| Backups DB | > 60 jours | Supprimés |
| Logs | > 500 MB | Supprimés |

### Données JAMAIS Supprimées

- ✅ Positions actuellement ouvertes (`exit_time IS NULL`)
- ✅ Tokens approuvés (`approved_tokens`)
- ✅ Backups récents (< 60 jours)
- ✅ Trades archivés (`trade_history_archive`)

---

## 📁 Fichiers et Logs

### Script Principal

```bash
/home/basebot/trading-bot/maintenance_safe.sh
```

### Logs de Maintenance

```bash
# Log principal
/home/basebot/trading-bot/logs/maintenance.log

# Statistiques mensuelles
/home/basebot/trading-bot/logs/stats_YYYYMM.txt

# Exemple:
/home/basebot/trading-bot/logs/stats_202511.txt
```

### Backups

```bash
# Répertoire
/home/basebot/trading-bot/data/backups/

# Format des fichiers
trading_20251110.db           # Backup quotidien
trading_20251110_030015.db    # Backup hebdo/mensuel (avec heure)
```

---

## 🔍 Vérifier la Configuration

### 1. Voir les Cron Jobs Actifs

```bash
# Se connecter en tant que basebot
su - basebot

# Voir les cron jobs
crontab -l

# Résultat attendu:
# ============================================
# BaseBot Trading - Cron Jobs Automatiques
# ============================================
#
# Backup quotidien de la base de données (2h du matin)
# 0 2 * * * cp /home/basebot/trading-bot/data/trading.db ...
#
# Maintenance hebdomadaire safe (dimanche 3h du matin)
# 0 3 * * 0 /home/basebot/trading-bot/maintenance_safe.sh
#
# Maintenance mensuelle complète (1er du mois à 4h du matin)
# 0 4 1 * * /home/basebot/trading-bot/maintenance_safe.sh
#
# Nettoyage des logs journaliers (tous les jours à 1h du matin)
# 0 1 * * * find /home/basebot/trading-bot/logs/ -name "*.log" -size +500M -delete
```

### 2. Voir les Derniers Logs de Maintenance

```bash
# Dernières 50 lignes
tail -50 /home/basebot/trading-bot/logs/maintenance.log

# Suivre en temps réel
tail -f /home/basebot/trading-bot/logs/maintenance.log
```

### 3. Voir les Statistiques Mensuelles

```bash
# Mois actuel
cat /home/basebot/trading-bot/logs/stats_$(date +%Y%m).txt

# Mois précédent
cat /home/basebot/trading-bot/logs/stats_202510.txt
```

### 4. Vérifier les Backups

```bash
# Lister les backups (avec taille)
ls -lh /home/basebot/trading-bot/data/backups/

# Compter les backups
ls /home/basebot/trading-bot/data/backups/ | wc -l

# Trouver le backup le plus récent
ls -t /home/basebot/trading-bot/data/backups/ | head -1
```

---

## 🧪 Tester Manuellement

### Exécuter la Maintenance Maintenant

```bash
# En tant que root
sudo bash /home/basebot/trading-bot/maintenance_safe.sh

# Ou en tant que basebot
su - basebot
bash /home/basebot/trading-bot/maintenance_safe.sh
```

**Résultat attendu:**
```
======================================================================
📊 Début de la maintenance safe (pas de redémarrage services)
======================================================================
📈 Vérification des positions actives...
Positions actuellement ouvertes: 2
⚠️  Le Trader ne sera PAS redémarré (préservation des trailing stops)
🗄️  Archivage des trades de plus de 30 jours...
✅ Archivage terminé: 0 trades archivés au total
💾 Backup de la base de données...
✅ Backup créé: .../trading_20251110_150023.db (512K)
🧹 Nettoyage des vieux backups...
✅ 0 vieux backups supprimés (> 60 jours)
🧹 Nettoyage des vieux logs...
✅ Vieux logs nettoyés
📊 Génération des statistiques mensuelles...
✅ Statistiques générées: .../stats_202511.txt
💾 Vérification espace disque...
✅ Espace disque OK: 45%
🔍 Vérification des services...
✅ basebot-scanner: ACTIF
✅ basebot-filter: ACTIF
✅ basebot-trader: ACTIF
✅ basebot-dashboard: ACTIF
======================================================================
✅ Maintenance safe terminée avec succès
======================================================================
📊 Résumé:
  - Positions ouvertes: 2
  - Trades archivés: 0
  - Backup créé: 512K
  - Espace disque: 45%
  - Services: Aucun redémarrage (trailing stops préservés)
======================================================================
```

---

## ⚙️ Personnaliser la Maintenance

### Changer les Horaires

```bash
# Éditer le crontab
su - basebot
crontab -e

# Exemple: Backup à 4h au lieu de 2h
# AVANT:
0 2 * * * cp /home/basebot/trading-bot/data/trading.db ...

# APRÈS:
0 4 * * * cp /home/basebot/trading-bot/data/trading.db ...

# Sauvegarder et quitter
```

### Changer la Durée de Rétention

```bash
# Éditer le script
nano /home/basebot/trading-bot/maintenance_safe.sh

# Ligne 42: Changer 30 jours
WHERE timestamp < datetime('now', '-30 days')
# Exemple: garder 60 jours
WHERE timestamp < datetime('now', '-60 days')

# Ligne 48: Changer 60 jours pour rejected_tokens
WHERE rejected_at < datetime('now', '-60 days')
# Exemple: garder 90 jours
WHERE rejected_at < datetime('now', '-90 days')

# Ligne 52: Changer 7 jours pour discovered_tokens
WHERE created_at < datetime('now', '-7 days')
# Exemple: garder 14 jours
WHERE created_at < datetime('now', '-14 days')
```

### Désactiver une Tâche

```bash
# Éditer le crontab
su - basebot
crontab -e

# Commenter une ligne avec #
# Exemple: désactiver le backup quotidien
# 0 2 * * * cp /home/basebot/trading-bot/data/trading.db ...

# Sauvegarder et quitter
```

---

## 🚨 En Cas de Problème

### Maintenance Échoue

```bash
# 1. Voir les logs d'erreur
tail -100 /home/basebot/trading-bot/logs/maintenance.log | grep -E "ERROR|Erreur"

# 2. Vérifier les permissions
ls -la /home/basebot/trading-bot/data/
ls -la /home/basebot/trading-bot/logs/

# 3. Vérifier que le script est exécutable
ls -la /home/basebot/trading-bot/maintenance_safe.sh
# Doit afficher: -rwxr-xr-x

# 4. Exécuter manuellement pour voir l'erreur
sudo bash /home/basebot/trading-bot/maintenance_safe.sh
```

### Backups Manquants

```bash
# 1. Vérifier le cron job
su - basebot
crontab -l | grep backup

# 2. Vérifier le répertoire
ls -la /home/basebot/trading-bot/data/backups/

# 3. Créer un backup manuel
cp /home/basebot/trading-bot/data/trading.db \
   /home/basebot/trading-bot/data/backups/trading_manual_$(date +%Y%m%d).db
```

### Espace Disque Plein

```bash
# 1. Vérifier l'espace
df -h /home/basebot/trading-bot

# 2. Trouver les gros fichiers
du -sh /home/basebot/trading-bot/* | sort -h

# 3. Nettoyer manuellement
# Supprimer vieux backups
find /home/basebot/trading-bot/data/backups/ -name "*.db" -mtime +30 -delete

# Supprimer gros logs
find /home/basebot/trading-bot/logs/ -name "*.log" -size +100M -delete
```

---

## 📊 Statistiques Disponibles

### Rapport Mensuel

Fichier: `/home/basebot/trading-bot/logs/stats_YYYYMM.txt`

**Contenu:**
```
=== RÉSUMÉ DU MOIS ===
total_trades  winning_trades  losing_trades  win_rate  total_profit  avg_profit  best_trade  worst_trade
------------  --------------  -------------  --------  ------------  ----------  ----------  -----------
45            34              11             75.6%     1234.56       27.43       567.89      -89.12

=== TOP 10 TOKENS DU MOIS ===
symbol  trades  avg_profit  total_profit
------  ------  ----------  ------------
AVNT    12      45.67       548.04
BASE    8       32.10       256.80
MONK    6       15.23       91.38

=== POSITIONS ACTUELLEMENT OUVERTES ===
symbol   amount   entry_price  opened_at
-------  -------  -----------  ------------------
TikTok   1000.00  0.00000827   2025-11-10 21:31
AVNT     500.00   0.00001225   2025-11-10 21:31
```

---

## ✅ Checklist Post-Installation

- [ ] Vérifier cron jobs: `su - basebot && crontab -l`
- [ ] Vérifier script existe: `ls -la /home/basebot/trading-bot/maintenance_safe.sh`
- [ ] Tester manuellement: `sudo bash /home/basebot/trading-bot/maintenance_safe.sh`
- [ ] Vérifier backup créé: `ls -la /home/basebot/trading-bot/data/backups/`
- [ ] Vérifier logs: `tail -50 /home/basebot/trading-bot/logs/maintenance.log`

---

## 📚 Fichiers Importants

| Fichier | Description |
|---------|-------------|
| `maintenance_safe.sh` | Script de maintenance sans redémarrage |
| `maintenance_monthly.sh` | Script legacy (avec redémarrage, non utilisé) |
| `logs/maintenance.log` | Log de toutes les maintenances |
| `logs/stats_YYYYMM.txt` | Statistiques mensuelles |
| `data/backups/` | Répertoire des backups |

---

**Date de création:** 2025-11-10
**Version:** 1.0
**Statut:** ✅ Automatique - Aucune intervention requise

**Le bot tourne 24/7 sans interruption des trailing stops!** 🚀
