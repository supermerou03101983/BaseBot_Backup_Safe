# 🧪 TEST DU GRACE PERIOD - GUIDE RAPIDE

## ✅ LA FEATURE EST PRÊTE!

**Branche:** `feature/grace-period-stop-loss`
**GitHub:** https://github.com/supermerou03101983/BaseBot/tree/feature/grace-period-stop-loss

---

## 🚀 DÉPLOIEMENT SUR VPS (RECOMMANDÉ)

### **Option 1: Sur votre VPS actuel (le plus simple)**

```bash
# 1. Connectez-vous à votre VPS
ssh user@votre-vps

# 2. Basculer sur l'utilisateur basebot
su - basebot

# 3. Aller dans le répertoire du bot
cd /home/basebot/trading-bot

# 4. Récupérer la nouvelle branche
git fetch origin
git checkout feature/grace-period-stop-loss

# 5. Vérifier que vous êtes sur la bonne branche
git branch
# Devrait afficher: * feature/grace-period-stop-loss

# 6. Redémarrer le trader (en tant que root)
exit  # Quitter basebot
sudo systemctl restart basebot-trader

# 7. Suivre les logs pour vérifier
journalctl -u basebot-trader -f
```

### **Option 2: Sur un nouveau VPS (test isolé)**

```bash
# Sur votre nouveau VPS
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/feature/grace-period-stop-loss/deploy.sh | sudo bash

# Ensuite configurer .env et démarrer comme d'habitude
```

---

## 📊 CE QU'IL FAUT SURVEILLER

### **1. Logs à l'ouverture de position:**

Vous devriez voir:
```
✅ Achat reussi: TOKEN_SYMBOL
🛡️ Grace period activé pour TOKEN_SYMBOL: 3 minutes avec stop loss à -35% (puis -5%)
```

### **2. Logs de monitoring (toutes les 10s):**

**Pendant le grace period (0-3 min):**
```
🛡️ Grace (2.7min) DEL: +3.2% | 0.1h | SL: -35%
🛡️ Grace (1.5min) DEL: -8.5% | 0.1h | SL: -35%  ← Noter: pas de vente malgré -8.5%!
🛡️ Grace (0.3min) DEL: +2.1% | 0.1h | SL: -35%
```

**Fin du grace period:**
```
⏰ DEL - Grace period terminé (3 min écoulées) - Stop loss activé à -5%
```

**Après le grace period:**
```
⏳ Attente DEL: +4.5% | 0.2h | SL: -5%
📈 Trailing DEL: +15.2% | 0.5h | Stop: $0.00012345
```

### **3. Logs de stop loss:**

**Si déclenché pendant grace (rare, grosse chute >35%):**
```
🛑 Stop Loss (Grace Period): -38.2% (seuil: -35%)
```

**Si déclenché après grace (normal):**
```
🛑 Stop Loss: -7.1% (seuil: -5%)
```

---

## 🎯 MÉTRIQUES À COLLECTER

**Après chaque session de trading:**

```bash
# 1. Exporter l'historique
su - basebot
cd /home/basebot/trading-bot
sqlite3 data/trading.db <<EOF
.mode csv
.output grace_period_results_$(date +%Y%m%d).csv
SELECT
    symbol,
    side,
    price,
    profit_loss,
    entry_time,
    exit_time,
    timestamp
FROM trade_history
WHERE date(timestamp) = date('now')
ORDER BY timestamp DESC;
.quit
EOF

# 2. Analyser
python3 analyze_trades_simple.py
```

**Ou via bot-analyze:**
```bash
bot-analyze
```

---

## 📋 CHECKLIST DE VALIDATION

Après **50+ trades**, vérifier:

- [ ] **Win rate:** Devrait être ≥ 65% (vs 61.5% avant)
- [ ] **Loss moyen:** Devrait être ≤ -11% (vs -12.4% avant)
- [ ] **Expectancy:** Devrait être ≥ 15% (vs 13.57% avant)
- [ ] **Catastrophic losses:** Aucun trade > -40% à cause du grace period
- [ ] **Durée moy. perdants:** Devrait augmenter vs 1.1 min avant

---

## 🔍 CAS DE TEST SPÉCIFIQUES

### **Cas 1: Token volatile qui se stabilise** ✅

**Scénario:**
- Achat @ $0.00010
- Baisse à -15% après 1 minute (slippage/volatilité)
- Remonte à +5% après 4 minutes

**Comportement attendu:**
- ✅ Position CONSERVÉE pendant grace (SL -35%)
- ✅ Grace period terminé après 3 min
- ✅ SL normal (-5%) activé
- ✅ Position reste ouverte (actuellement +5%)

**Résultat:** TRADE SAUVÉ ✅

---

### **Cas 2: Vraie chute catastrophique** 🚨

**Scénario:**
- Achat @ $0.00010
- Chute brutale à -40% en 2 minutes (rug pull)

**Comportement attendu:**
- ✅ Stop loss grace period déclenché à -35%
- ✅ Sortie avec "Stop Loss (Grace Period): -37%"
- ✅ Perte limitée à ~-35%

**Résultat:** PROTECTION ACTIVÉE ✅

---

### **Cas 3: Baisse progressive après stabilisation** 📉

**Scénario:**
- Achat @ $0.00010
- Stable +2% pendant 3 minutes
- Baisse à -6% après 5 minutes

**Comportement attendu:**
- ✅ Grace period terminé sans incident
- ✅ SL normal (-5%) activé
- ✅ Sortie à -6% avec "Stop Loss: -6.2% (seuil: -5%)"

**Résultat:** PROTECTION NORMALE ✅

---

## 📊 COMPARAISON AVANT/APRÈS

| Métrique | Main | Grace Period | Amélioration |
|----------|------|--------------|--------------|
| Win Rate | 61.5% | ? | Objectif: +8.5% |
| Avg Loss | -12.4% | ? | Objectif: +2.4% |
| Expectancy | +13.57% | ? | Objectif: +3.5% |
| Trades sauvés | 0 | ? | Objectif: 40% |

**Remplir avec vos résultats après 50 trades!**

---

## ⚙️ AJUSTER LES PARAMÈTRES (si besoin)

Si les résultats ne sont pas satisfaisants, ajuster dans [src/Trader.py:50-54](src/Trader.py:50-54):

```python
# Paramètres actuels
self.grace_period_minutes = 3           # Durée du grace
self.grace_period_stop_loss_percent = 35  # SL pendant grace
self.normal_stop_loss_percent = 5       # SL après grace
```

**Variantes possibles:**

| Profil | Grace (min) | SL Grace | SL Normal | Usage |
|--------|-------------|----------|-----------|-------|
| **Conservateur** | 2 | -25% | -5% | Moins de risque |
| **Standard** | 3 | -35% | -5% | Configuration actuelle |
| **Agressif** | 5 | -40% | -5% | Plus de tokens sauvés |

---

## 🔄 RETOUR À LA VERSION STABLE

Si problèmes ou résultats décevants:

```bash
# Sur VPS
su - basebot
cd /home/basebot/trading-bot
git checkout main

# Redémarrer
exit
sudo systemctl restart basebot-trader
```

---

## 📈 PLAN DE TEST COMPLET

### **Semaine 1 (15-22 Nov):**
- ✅ Déployer en mode PAPER
- ✅ Surveiller les logs quotidiennement
- ✅ Collecter minimum 30 trades
- ✅ Noter les cas intéressants

### **Semaine 2 (22-29 Nov):**
- ✅ Analyser les résultats (bot-analyze)
- ✅ Comparer avec les objectifs
- ✅ Ajuster paramètres si nécessaire
- ✅ Collecter 20+ trades supplémentaires

### **Semaine 3 (29 Nov+):**
- ✅ Décision finale: MERGE ou ABANDON
- ✅ Si merge: Test progressif en mode REAL
- ✅ Si abandon: Retour à main

---

## 🚨 CRITÈRES D'ABANDON

Abandonner la feature SI:
- ❌ Win rate < 60% (pire qu'avant)
- ❌ Loss moyen > -13% (pire qu'avant)
- ❌ Catastrophic loss > -40% récurrent
- ❌ Expectancy < 12% (pire qu'avant)

---

## ✅ CRITÈRES DE MERGE

Merger dans main SI (sur 50+ trades):
- ✅ Win rate ≥ 65%
- ✅ Loss moyen ≤ -11%
- ✅ Expectancy ≥ 15%
- ✅ Pas de loss catastrophique >-40%
- ✅ Amélioration confirmée vs baseline

---

## 📞 COMMANDES UTILES

```bash
# Vérifier la branche active
git branch

# Voir les logs grace period
journalctl -u basebot-trader -f | grep -E "Grace|Stop Loss"

# Analyser les performances
bot-analyze

# Voir les positions actuelles
bot-status

# Logs en temps réel
bot-watch

# Statistiques rapides
sqlite3 /home/basebot/trading-bot/data/trading.db \
  "SELECT
     COUNT(*) as total,
     SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as wins,
     AVG(profit_loss) as avg_pnl
   FROM trade_history
   WHERE date(timestamp) >= date('now', '-7 days');"
```

---

## 📝 JOURNAL DE TEST (Template)

**Date:** ___________
**Trades du jour:** ___________
**Win rate:** ___________
**Meilleur trade:** ___________
**Pire trade:** ___________
**Trades sauvés par grace period:** ___________
**Notes:**
```
_________________________________________________
_________________________________________________
_________________________________________________
```

---

## 🎉 C'EST PARTI!

**Branche déployée:** feature/grace-period-stop-loss
**Mode recommandé:** PAPER
**Durée test:** 2-3 semaines
**Objectif:** Valider amélioration de 40% sur trades perdants

**Bon test! 🚀**

---

*Guide créé le: 2025-11-15*
*Branche: feature/grace-period-stop-loss*
