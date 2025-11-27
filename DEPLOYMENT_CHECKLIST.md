# 🚀 CHECKLIST DE DÉPLOIEMENT - BASE TRADING BOT

## ✅ PRÉ-DÉPLOIEMENT (Local)

### 1. Vérifications de Code
- [x] `src/honeypot_checker.py` créé et testé
- [x] `src/Trader.py` intègre HoneypotChecker
- [x] `test_honeypot.py` créé pour tests
- [x] Syntaxe Python validée (tous les fichiers compilent)
- [x] Import HoneypotChecker dans Trader.py
- [x] Initialisation dans `__init__` du Trader
- [x] Appel dans `validate_token_before_buy()`
- [x] Cleanup dans `cleanup()`

### 2. Dépendances
- [x] `requests==2.31.0` dans requirements.txt
- [x] Toutes les dépendances listées dans requirements.txt

### 3. Fichiers à Déployer
```
BaseBot/
├── src/
│   ├── honeypot_checker.py          ✅ NOUVEAU - Protection honeypot
│   ├── Trader.py                    ✅ MODIFIÉ - Intègre honeypot check
│   ├── Scanner.py                   ✓ Existant
│   ├── Filter.py                    ✓ Existant
│   ├── Dashboard.py                 ✓ Existant
│   ├── web3_utils.py                ✓ Existant
│   └── config_manager.py            ✓ Existant
├── config/
│   ├── .env.example                 ✓ Existant
│   └── trading_mode.json            ✓ Existant
├── test_honeypot.py                 ✅ NOUVEAU - Script de test
├── verify_deployment.sh             ✅ NOUVEAU - Vérification post-déploiement
├── requirements.txt                 ✓ Existant
├── deploy.sh                        ✓ Existant
└── README.md                        ✓ Existant
```

---

## 📦 DÉPLOIEMENT SUR VPS

### Étape 1: Commit & Push sur GitHub
```bash
cd /Users/vincentdoms/Documents/BaseBot

# Vérifier les changements
git status

# Ajouter les nouveaux fichiers
git add src/honeypot_checker.py
git add test_honeypot.py
git add verify_deployment.sh
git add DEPLOYMENT_CHECKLIST.md

# Ajouter les fichiers modifiés
git add src/Trader.py

# Commit
git commit -m "🍯 Add honeypot protection + mode real fixes

- Add honeypot_checker.py module with Honeypot.is API integration
- Integrate honeypot check in Trader.py validate_token_before_buy()
- Fix min_amount calculation bug in execute_buy (mode real)
- Add MAX_GAS_PRICE check before transactions
- Use .env variables for gas limits and slippage
- Add verify_deployment.sh script
- Add test_honeypot.py for testing

Protection honeypot:
- Checks: is_honeypot, can_sell, buy/sell taxes
- Risk levels: LOW, MEDIUM, HIGH, CRITICAL
- Degraded mode if API unavailable
- ~2-5 seconds per check, only before buy (1-3/day)

Mode real fixes:
- Correct expected_tokens calculation using USD prices
- Gas price check before buy/sell (max 50 Gwei)
- Configurable slippage and gas limits from .env
- Detailed logging for all transactions"

# Push
git push origin main
```

### Étape 2: Déploiement sur VPS
```bash
# Se connecter au VPS
ssh root@YOUR_VPS_IP

# Lancer le déploiement
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash
```

### Étape 3: Vérification Post-Déploiement
```bash
# Sur le VPS, exécuter le script de vérification
cd /home/basebot/trading-bot
sudo bash verify_deployment.sh
```

**Sortie attendue:**
```
✓ honeypot_checker.py présent
✓ Import HoneypotChecker présent
✓ Initialisation HoneypotChecker présente
✓ Appel check_token présent
✓ requests installé
✓ honeypot_checker.py syntaxe OK
✓ Trader.py syntaxe OK
✓ API Honeypot accessible
```

---

## 🧪 TESTS POST-DÉPLOIEMENT

### Test 1: Module Honeypot Standalone
```bash
cd /home/basebot/trading-bot
source venv/bin/activate

# Test avec WETH (token légitime)
python3 src/honeypot_checker.py 0x4200000000000000000000000000000000000006
```

**Sortie attendue:**
```
🍯 HONEYPOT: NON
✅ SAFE TO TRADE: OUI
⚠️  RISK LEVEL: LOW
💰 Buy Tax: 0.0%
💸 Sell Tax: 0.0%
✅ Can Sell: True
```

### Test 2: Script de Test Complet
```bash
python3 test_honeypot.py
```

### Test 3: Vérifier les Logs du Trader
```bash
# Démarrer le trader en mode paper
sudo systemctl restart basebot-trader

# Surveiller les logs pour voir la vérification honeypot
tail -f logs/trader.log | grep "🍯"
```

**Logs attendus:**
```
🍯 Vérification honeypot pour TOKEN_SYMBOL...
🛡️  Honeypot check PASSED: TOKEN_SYMBOL | Taxes: Buy=0.0% Sell=0.0% | Risk=LOW
```

Ou en cas de détection:
```
🍯 Vérification honeypot pour SCAM_TOKEN...
❌ Token SCAM_TOKEN rejeté: HONEYPOT_CONFIRMED, CANNOT_SELL | Risk=CRITICAL
```

---

## ⚙️ CONFIGURATION

### Variables d'Environnement (déjà dans .env)
```bash
# Aucune nouvelle variable requise
# La protection honeypot utilise une API publique gratuite
```

### Seuils de Protection (dans honeypot_checker.py)
```python
# Critères de rejet automatique:
MAX_BUY_TAX = 10%     # Rejet si buy tax > 10%
MAX_SELL_TAX = 10%    # Rejet si sell tax > 10%
REJECT_IF_HONEYPOT = True
REJECT_IF_CANNOT_SELL = True
```

**Pour modifier les seuils:**
```bash
nano /home/basebot/trading-bot/src/honeypot_checker.py

# Chercher la section "is_safe" (ligne ~147-154)
# Modifier les valeurs et redémarrer le trader
sudo systemctl restart basebot-trader
```

---

## 🔧 TROUBLESHOOTING

### Problème: API Honeypot indisponible
**Symptôme:** Logs montrent "⚠️  API Honeypot indisponible"
**Impact:** Bot fonctionne en mode dégradé (autorise le trade)
**Solution:**
- Normal si temporaire (l'API peut avoir des downtimes)
- Le bot a d'autres protections (liquidité, volume, etc.)
- Vérifier après quelques heures

### Problème: Import Error honeypot_checker
**Symptôme:** `ModuleNotFoundError: No module named 'honeypot_checker'`
**Solution:**
```bash
cd /home/basebot/trading-bot
# Vérifier que le fichier existe
ls -la src/honeypot_checker.py

# Vérifier les permissions
chown -R basebot:basebot src/honeypot_checker.py

# Redémarrer le service
sudo systemctl restart basebot-trader
```

### Problème: Requests module not found
**Symptôme:** `ModuleNotFoundError: No module named 'requests'`
**Solution:**
```bash
cd /home/basebot/trading-bot
source venv/bin/activate
pip install requests==2.31.0
deactivate
sudo systemctl restart basebot-trader
```

---

## 📊 MONITORING

### Vérifier que la Protection Fonctionne
```bash
# Compter les vérifications honeypot dans les logs
grep -c "🍯 Vérification honeypot" logs/trader.log

# Voir les dernières vérifications
grep "🍯" logs/trader.log | tail -20

# Voir les rejets honeypot
grep "Token dangereux" logs/trader.log
```

### Statistiques API
```bash
# Nombre d'appels API honeypot par jour (devrait être 1-3)
grep "🍯 Vérification honeypot" logs/trader.log | grep "$(date +%Y-%m-%d)" | wc -l
```

---

## ✅ VALIDATION FINALE

### Checklist Avant Activation Mode Real
- [ ] verify_deployment.sh exécuté avec succès
- [ ] Test honeypot avec WETH réussi
- [ ] Logs montrent "🍯 Vérification honeypot" lors des achats
- [ ] Aucune erreur "ModuleNotFoundError"
- [ ] API Honeypot accessible (ou mode dégradé OK)
- [ ] Services systemd démarrés
- [ ] Balance ETH > 0.1 ETH sur le wallet
- [ ] Mode PAPER testé 24-48h sans erreur

### Commandes de Vérification Rapide
```bash
# Tout-en-un
cd /home/basebot/trading-bot && \
systemctl status basebot-trader --no-pager && \
tail -20 logs/trader.log | grep -E "🍯|🛡️|❌"
```

---

## 🎯 RÉSUMÉ DES MODIFICATIONS

### Nouveaux Fichiers
1. **src/honeypot_checker.py** - Module de protection honeypot
2. **test_honeypot.py** - Script de test
3. **verify_deployment.sh** - Vérification automatique

### Fichiers Modifiés
1. **src/Trader.py**
   - Import HoneypotChecker
   - Vérification honeypot dans validate_token_before_buy()
   - Fix bug min_amount dans execute_buy()
   - Check MAX_GAS_PRICE
   - Utilisation variables .env pour gas/slippage

### Impact Performance
- **Avant:** 0 appels API externes avant achat
- **Après:** 1 appel API Honeypot (2-5s) avant chaque achat
- **Fréquence:** 1-3 appels/jour (pas d'impact significatif)

### Sécurité Ajoutée
- ✅ Détection honeypot confirmé
- ✅ Vérification capacité de vente
- ✅ Analyse taxes (buy/sell/transfer)
- ✅ Détection concentration holders
- ✅ Risk scoring (LOW → CRITICAL)

---

## 📞 SUPPORT

En cas de problème lors du déploiement:
1. Consulter les logs: `tail -100 /var/log/basebot-deployment.log`
2. Vérifier les services: `systemctl status basebot-*`
3. Exécuter verify_deployment.sh
4. Vérifier les logs trader: `tail -100 logs/trader.log`

---

**Date de création:** 2025-11-12
**Version:** 1.0.0
**Prêt pour production:** ✅ OUI
