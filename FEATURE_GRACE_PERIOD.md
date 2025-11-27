# 🛡️ GRACE PERIOD STOP LOSS

## 📋 Vue d'ensemble

**Branche:** `feature/grace-period-stop-loss`
**Statut:** En test
**Objectif:** Réduire les sorties prématurées dues au slippage/volatilité initiale

---

## 🎯 Problème identifié

**Analyse des 26 trades du 14 novembre:**
- Trades perdants sortent en moyenne après **1.1 minute**
- Trades gagnants restent en moyenne **5 minutes**
- Loss moyen: **-12.4%** (trop élevé)

**Cause probable:**
Les 3 premières minutes après l'achat sont très volatiles:
- Slippage important
- Bots arbitrage
- Price discovery
- Faux mouvements baissiers

Le stop loss à -5% se déclenche trop vite sur du bruit, pas sur une vraie baisse.

---

## 💡 Solution: Grace Period

### **Mécanique:**

1. **0-3 minutes après l'achat:** Grace Period actif
   - Stop loss élargi à **-35%**
   - Laisse le token se stabiliser
   - Évite les sorties sur slippage/volatilité normale

2. **Après 3 minutes:** Stop loss normal
   - Stop loss réduit à **-5%**
   - Protection normale activée
   - Trailing stop peut s'activer normalement

### **Schéma:**

```
Temps    0min ━━━━━━━━━━ 3min ━━━━━━━━━━━━━━━━━━━━━→
         │               │
         │ Grace Period  │    Mode Normal
         │  SL: -35%     │    SL: -5%
         │               │
Achat ━━━┘               └━━━ Grace Period terminé
```

---

## 📊 Impact attendu

**Basé sur l'analyse des 26 trades:**

### **Trades qui auraient été sauvés:**
- DEL trade #11: -15.8% → Aurait survécu au grace period
- DEL trade #19: -8.36% → Aurait survécu
- DEL trade #20: -5.41% → Aurait survécu
- DEL trade #23: -5.02% → Aurait survécu

**Estimation:** **4 trades perdants évités sur 10 = 40% de réduction**

### **Métriques projetées:**

**Avant (26 trades):**
- Win rate: 61.5%
- Loss moyen: -12.4%
- Expectancy: +13.57%

**Après (estimé):**
- Win rate: **~70%** (+8.5 points)
- Loss moyen: **-10%** (amélioration -2.4 points)
- Expectancy: **~17-18%** (+4 points)

---

## 🔧 Implémentation

### **Modifications apportées:**

**1. Classe Position ([Trader.py:50-73](src/Trader.py:50-73))**
```python
# Nouveaux attributs
self.grace_period_minutes = 3
self.grace_period_stop_loss_percent = 35  # -35%
self.normal_stop_loss_percent = 5  # -5%
self.grace_period_active = True

# Nouvelles méthodes
def get_active_stop_loss_percent()  # Retourne SL actif
def is_in_grace_period()            # Check si encore en grace
```

**2. Logique stop loss ([Trader.py:1108-1129](src/Trader.py:1108-1129))**
```python
# Stop loss dynamique
active_stop_loss = position.get_active_stop_loss_percent()

# Log transition
if grace_period terminé:
    log("Grace period terminé - Stop loss activé à -5%")

# Check avec SL actif
if profit_percent <= -active_stop_loss:
    execute_sell()
```

**3. Logging amélioré ([Trader.py:1321-1338](src/Trader.py:1321-1338))**
```python
# Monitoring toutes les 10 secondes affiche:
if in_grace_period:
    "🛡️ Grace (2.3min) DEL: +5.2% | 0.1h | SL: -35%"
else:
    "⏳ Attente DEL: +5.2% | 0.5h | SL: -5%"
```

---

## 📝 Logs générés

### **À l'ouverture de position:**
```
✅ Achat reussi: DEL
🛡️ Grace period activé pour DEL: 3 minutes avec stop loss à -35% (puis -5%)
```

### **Pendant le grace period (toutes les 10s):**
```
🛡️ Grace (2.5min) DEL: +3.2% | 0.1h | SL: -35%
🛡️ Grace (1.8min) DEL: -8.5% | 0.1h | SL: -35%
🛡️ Grace (0.5min) DEL: +2.1% | 0.1h | SL: -35%
```

### **Fin du grace period:**
```
⏰ DEL - Grace period terminé (3 min écoulées) - Stop loss activé à -5%
⏳ Attente DEL: +4.5% | 0.1h | SL: -5%
```

### **Si stop loss déclenché pendant grace:**
```
🛑 Stop Loss (Grace Period): -38.2% (seuil: -35%)
```

### **Si stop loss déclenché après grace:**
```
🛑 Stop Loss: -7.1% (seuil: -5%)
```

---

## 🧪 Tests à effectuer

### **1. Test en mode PAPER (recommandé):**
```bash
# Sur VPS ou local
cd /home/basebot/trading-bot
git checkout feature/grace-period-stop-loss
systemctl restart basebot-trader

# Suivre les logs
journalctl -u basebot-trader -f
```

### **2. Cas à observer:**

**Cas 1: Token volatile qui se stabilise**
- Devrait: Survivre au grace period malgré -10% initial
- Résultat attendu: Position active après 3 min avec SL -5%

**Cas 2: Vraie chute >35%**
- Devrait: Stop loss déclenché même en grace period
- Résultat attendu: Sortie avec "Stop Loss (Grace Period)"

**Cas 3: Token stable puis baisse**
- Devrait: Grace period termine sans souci, puis SL -5% actif
- Résultat attendu: Sortie si baisse >5% après 3 min

### **3. Métriques à surveiller:**
- Nombre de positions survivant au grace period
- Durée moyenne des positions (devrait augmenter)
- Win rate (devrait augmenter vers 70%)
- Loss moyen (devrait diminuer vers -10%)

---

## 📊 Tableau comparatif

| Métrique | Avant | Après (estimé) | Delta |
|----------|-------|----------------|-------|
| Win Rate | 61.5% | ~70% | +8.5% |
| Loss moyen | -12.4% | ~-10% | +2.4% |
| Expectancy | +13.57% | ~+17% | +3.5% |
| Durée moy. perdants | 1.1 min | ~3.5 min | +2.4 min |
| Trades sauvés | 0 | ~4/10 | +40% |

---

## ⚠️ Risques potentiels

**1. Catastrophic losses (-35%)**
- **Probabilité:** Très faible (vu votre pire loss = -45% en 1 trade sur 26)
- **Mitigation:** Honeypot checker actif, filtre liquidité/holders

**2. Hausse du capital à risque**
- **Impact:** Position reste ouverte plus longtemps si baisse légère
- **Mitigation:** Time exit toujours actif (72h max)

**3. Slippage extrême sur certains tokens**
- **Probabilité:** Faible avec filtre MAX_SLIPPAGE=3%
- **Mitigation:** Check avant achat

---

## 🎯 Critères de validation

**La feature sera validée si (sur 50+ trades):**
- ✅ Win rate ≥ 65%
- ✅ Loss moyen ≤ -11%
- ✅ Expectancy ≥ 15%
- ✅ Aucun loss catastrophique >-40% dû au grace period

**Si validé:** Merge dans main
**Si échec:** Ajuster paramètres ou abandon

---

## 🔧 Paramètres ajustables

Si besoin de tuning:

```python
# Dans Position.__init__()
self.grace_period_minutes = 3           # Durée du grace
self.grace_period_stop_loss_percent = 35  # SL pendant grace
self.normal_stop_loss_percent = 5       # SL après grace
```

**Variations possibles:**
- Grace 2 min / SL -25% → Plus conservateur
- Grace 5 min / SL -40% → Plus agressif
- Grace 3 min / SL -30% → Équilibré alternatif

---

## 📅 Planning de test

**Semaine 1 (Nov 15-22):**
- Déploiement en mode PAPER
- Surveillance des logs
- Collecte de 30+ trades

**Semaine 2 (Nov 22-29):**
- Analyse des résultats
- Ajustement si nécessaire
- Collecte de 20+ trades supplémentaires

**Semaine 3 (Nov 29+):**
- Décision: Merge ou abandon
- Si merge: Déploiement progressif en mode REAL

---

## 🚀 Commandes de déploiement

### **Test sur VPS:**
```bash
# Checkout de la branche
cd /home/basebot/trading-bot
git fetch origin
git checkout feature/grace-period-stop-loss

# Redémarrer le trader
sudo systemctl restart basebot-trader

# Suivre les logs
journalctl -u basebot-trader -f | grep -E "Grace|Stop Loss"
```

### **Retour à main si problème:**
```bash
git checkout main
sudo systemctl restart basebot-trader
```

---

## 📈 Suivi des résultats

**Fichier CSV à créer après chaque batch:**
`results/grace_period_test_YYYYMMDD.csv`

Colonnes:
- timestamp
- symbol
- entry_price
- exit_price
- pnl_percent
- duration_minutes
- grace_period_triggered (oui/non)
- stop_loss_type (grace/normal/trailing)

**Analyse après 50 trades:**
```bash
cd /home/basebot/trading-bot
python3 analyze_trades_simple.py
```

---

**Créé:** 2025-11-15
**Branche:** `feature/grace-period-stop-loss`
**Auteur:** Claude Code
