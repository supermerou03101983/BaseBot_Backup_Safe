# 🚨 GUIDE DE DÉPANNAGE - BOT FREEZÉ

## SITUATION ACTUELLE
- **Symptôme**: 2 positions ouvertes depuis >24h, aucune activité
- **Cause probable**: Le bot est bloqué dans la boucle `update_positions()`

---

## 🔍 CAUSES POSSIBLES IDENTIFIÉES

### 1. **API DexScreener en panne ou rate-limitée** (Très probable)
**Ligne 1039-1047 dans Trader.py:**
```python
dex_data = self.dexscreener.get_token_info(address)
```

**Problème:**
- Si DexScreener ne répond pas, le bot fait 3 tentatives avec 2s de pause
- Pour 2 positions: 3 tentatives × 2s × 2 positions = 12 secondes de blocage
- Si l'API est complètement HS, cela se répète en boucle infinie

**Solution immédiate:** Vérifier les logs DexScreener

---

### 2. **Timeout sur `wait_for_transaction_receipt`** (Probable)
**Ligne 998-1000 dans Trader.py:**
```python
swap_receipt = self.web3_manager.w3.eth.wait_for_transaction_receipt(
    swap_hash, timeout=120
)
```

**Problème:**
- Si une transaction de vente est bloquée sur le réseau, attend 120 secondes
- Si le RPC node ne répond plus, peut bloquer indéfiniment

---

### 3. **Prix aberrant ignoré en boucle** (Possible)
**Ligne 1055-1061 dans Trader.py:**
```python
if price_change_ratio > 1000 or price_change_ratio < 0.001:
    # Prix ignoré mais position jamais fermée
```

**Problème:**
- Si le prix est aberrant en continu, la position n'est jamais mise à jour
- Aucun exit n'est déclenché car le prix reste sur l'ancienne valeur

---

### 4. **RPC Node défaillant** (Possible)
**Problème:**
- Si le RPC node (mainnet.base.org) est lent ou ne répond plus
- Toutes les requêtes Web3 timeout

---

## 🛠️ PROCÉDURE DE DÉPANNAGE

### **ÉTAPE 1: Diagnostic sur le VPS**

Connectez-vous à votre VPS:

```bash
ssh user@votre-vps
cd /chemin/vers/BaseBot

# 1. Vérifier si le processus tourne
ps aux | grep -i trader
# Notez le PID si présent

# 2. Lancer le diagnostic
python3 diagnose_freeze.py

# 3. Vérifier les logs récents
tail -100 logs/trading.log

# 4. Chercher les erreurs spécifiques
grep -i "error" logs/trading.log | tail -20
grep -i "dexscreener" logs/trading.log | tail -20
grep -i "timeout" logs/trading.log | tail -20
```

---

### **ÉTAPE 2: Identifier la cause**

Analysez la sortie de `diagnose_freeze.py`:

**Si vous voyez:**
- ❌ `Impossible de recuperer le prix apres 3 tentatives` → **Problème API DexScreener**
- ❌ `Timeout waiting for transaction` → **Problème RPC ou transaction bloquée**
- ❌ `Prix aberrant` répété → **Problème de price feed**
- ❌ Aucune erreur mais inactif → **Processus freezé/crashé**

---

### **ÉTAPE 3: Débloquer les positions**

**Option A: Redémarrer le bot (Préférable si mode PAPER)**

```bash
# 1. Tuer le processus actuel
pkill -f Trader.py

# Ou avec le PID:
kill -9 <PID>

# 2. Attendre 5 secondes
sleep 5

# 3. Relancer le bot
nohup python3 src/Trader.py > logs/trader_output.log 2>&1 &

# 4. Vérifier qu'il redémarre
tail -f logs/trading.log
```

Le bot devrait:
- Charger les positions de la DB
- Tenter de vendre selon les conditions (stop loss, trailing stop, etc.)

---

**Option B: Fermeture d'urgence (Si redémarrage ne fonctionne pas)**

```bash
# 1. Arrêter le bot
pkill -f Trader.py

# 2. Fermer manuellement les positions dans la DB
python3 emergency_close_positions.py

# Tapez "OUI" pour confirmer

# 3. Redémarrer le bot
python3 src/Trader.py
```

⚠️ **ATTENTION MODE REAL:** Les tokens restent dans votre wallet, vendez-les manuellement!

---

## 🔧 CORRECTIONS À APPLIQUER

### **FIX 1: Ajouter des timeouts stricts sur les API calls**

Dans `web3_utils.py` (DexScreenerAPI):

```python
def get_token_info(self, token_address: str, timeout=10):
    try:
        response = requests.get(url, timeout=timeout)  # Timeout strict
        # ...
    except requests.Timeout:
        self.logger.error(f"DexScreener timeout pour {token_address}")
        return None
```

---

### **FIX 2: Ajouter un fallback si API DexScreener fail**

Si DexScreener échoue 3 fois, utiliser un exit d'urgence:

```python
if not dex_data:
    self.logger.error(f"Impossible de récupérer prix pour {position.symbol}")

    # Si position ouverte depuis >72h ET pas de prix, emergency close
    position_age_hours = (datetime.now() - position.entry_time).total_seconds() / 3600
    if position_age_hours > 72:
        self.logger.warning(f"Emergency close: position trop vieille sans prix")
        self.execute_sell(position, "EMERGENCY_NO_PRICE")
    continue
```

---

### **FIX 3: Watchdog automatique (Recommandé)**

Configurer un cron job qui vérifie le bot toutes les 15 minutes:

```bash
# Éditer crontab
crontab -e

# Ajouter cette ligne:
*/15 * * * * cd /chemin/vers/BaseBot && python3 watchdog.py >> logs/watchdog.log 2>&1
```

Le watchdog:
- Détecte l'inactivité
- Alerte si positions bloquées >48h
- Force close si positions >120h

---

### **FIX 4: Ajouter un heartbeat dans les logs**

Ajouter dans la boucle principale:

```python
# Toutes les 60 secondes, log un heartbeat
if time.time() - last_heartbeat > 60:
    self.logger.info(f"❤️ Heartbeat: {len(self.positions)} positions, monitoring actif")
    last_heartbeat = time.time()
```

Permet de confirmer que le bot tourne (même sans trades).

---

## 📊 COMMANDES UTILES SUR LE VPS

```bash
# Vérifier l'état du bot
ps aux | grep Trader

# Logs en temps réel
tail -f logs/trading.log

# Dernières 50 lignes
tail -50 logs/trading.log

# Chercher erreurs
grep -i error logs/trading.log | tail -20

# Vérifier la mémoire/CPU
top -p <PID>

# Espace disque
df -h

# État de la DB
sqlite3 data/trading.db "SELECT COUNT(*) FROM trade_history WHERE exit_time IS NULL;"

# Redémarrer proprement
pkill -f Trader.py && sleep 5 && nohup python3 src/Trader.py &

# Diagnostic complet
python3 diagnose_freeze.py

# Watchdog manuel
python3 watchdog.py
```

---

## 🚀 PLAN D'ACTION IMMÉDIAT

### **Maintenant (5 minutes):**

1. ✅ SSH vers votre VPS
2. ✅ `python3 diagnose_freeze.py` → Identifier la cause
3. ✅ `tail -100 logs/trading.log` → Vérifier derniers logs
4. ✅ Redémarrer le bot: `pkill -f Trader.py && sleep 5 && python3 src/Trader.py`

### **Aujourd'hui (1 heure):**

5. ✅ Uploader les scripts sur le VPS:
   - `diagnose_freeze.py`
   - `emergency_close_positions.py`
   - `watchdog.py`

6. ✅ Configurer le cron watchdog

7. ✅ Tester que le bot se relance correctement

### **Cette semaine:**

8. ✅ Implémenter les FIX 1-4 ci-dessus
9. ✅ Ajouter des timeouts stricts partout
10. ✅ Tester le watchdog pendant 48h

---

## 📞 MONITORING CONTINU

**Créer un alias pour check rapide:**

```bash
# Ajoutez dans ~/.bashrc ou ~/.zshrc
alias bot-status='cd /chemin/vers/BaseBot && python3 diagnose_freeze.py'
alias bot-restart='pkill -f Trader.py && sleep 5 && cd /chemin/vers/BaseBot && nohup python3 src/Trader.py > logs/trader_output.log 2>&1 &'
alias bot-logs='tail -50 /chemin/vers/BaseBot/logs/trading.log'
```

Ensuite, juste taper:
- `bot-status` → Diagnostic
- `bot-restart` → Redémarrage propre
- `bot-logs` → Logs récents

---

## ⚠️ CHECKLIST AVANT DE RELANCER

- [ ] Positions fermées ou bot prêt à les gérer
- [ ] Logs vérifiés pour identifier la cause
- [ ] Watchdog configuré
- [ ] RPC node fonctionnel (tester: curl https://mainnet.base.org)
- [ ] API keys valides (DexScreener, CoinGecko)
- [ ] Mode trading correct (paper vs real)
- [ ] Limite quotidienne réinitialisée si nécessaire

---

## 🆘 EN CAS D'URGENCE

**Si positions en mode REAL et bot bloqué:**

1. **NE PAS PANIQUER**
2. Vendre manuellement via:
   - Uniswap Interface
   - DEX Aggregator (1inch, Matcha)
3. Puis cleanup DB: `python3 emergency_close_positions.py`

**Numéros de secours:**
- Support Base: https://base.org
- Uniswap: https://app.uniswap.org

---

**Date de création:** 2025-11-14
**Version:** 1.0
