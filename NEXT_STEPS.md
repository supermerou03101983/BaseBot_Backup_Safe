# Prochaines étapes - Scanner silencieux

## Situation actuelle

✅ Le service Scanner démarre sans erreur
✅ La connexion Web3 fonctionne (bloc 37860079 récupéré)
✅ Les permissions ont été corrigées (chown effectué)
❓ Aucun log n'apparaît dans journalctl

## Actions immédiates à effectuer sur votre VPS

### Action 1: Diagnostic complet automatique (5 min)

```bash
# Télécharger et exécuter le script de diagnostic
cd /home/basebot/trading-bot
bash diagnose_scanner.sh
```

Ce script va automatiquement vérifier:
- Statut du service
- Logs systemd et applicatifs
- Configuration .env
- Base de données
- Imports Python
- Connexion RPC
- Processus en cours

**Attendu:** Un rapport complet avec ✅, ⚠️, ou ❌ pour chaque élément.

---

### Action 2: Test manuel du Scanner (2 min)

Si le diagnostic ne révèle rien d'évident:

```bash
# Arrêter le service
systemctl stop basebot-scanner

# Se connecter en tant que basebot et lancer manuellement
su - basebot
cd /home/basebot/trading-bot
source venv/bin/activate
python src/Scanner.py
```

**Attendu dans les 5 premières secondes:**
```
2025-11-07 XX:XX:XX - INFO - Scanner démarré...
2025-11-07 XX:XX:XX - INFO - Récupération des nouveaux tokens depuis DexScreener...
```

**Si aucun log n'apparaît:**
- Problème avec la configuration .env
- Problème avec l'initialisation Web3/DexScreener

**Si des logs apparaissent:**
- Le problème vient du service systemd (buffering des logs)
- Solution: Ajouter `PYTHONUNBUFFERED=1` au service

Appuyer sur `Ctrl+C` pour arrêter après avoir vu les premiers logs.

---

### Action 3: Test des composants Python (3 min)

Si le test manuel ne produit aucun log:

```bash
# Toujours en tant que basebot
cd /home/basebot/trading-bot
source venv/bin/activate
python test_scanner_simple.py
```

Ce script teste chaque composant individuellement:
1. Environnement Python ✅
2. Fichier .env et variables ✅/❌
3. Import des modules ✅/❌
4. Connexion Web3 ✅/❌
5. API DexScreener ✅/❌
6. Base de données ✅/❌
7. Permissions logs ✅/❌
8. Initialisation Scanner ✅/❌

**Identifie précisément** où le problème se situe.

---

### Action 4: Vérifier la configuration .env (1 min)

```bash
# Vérifier les variables critiques
grep -E "^(PRIVATE_KEY|RPC_URL|SCAN_INTERVAL)" /home/basebot/trading-bot/config/.env
```

**Points de vigilance:**

1. **PRIVATE_KEY ne doit PAS être la valeur par défaut:**
   ```bash
   # ❌ INVALIDE (valeur par défaut):
   PRIVATE_KEY=votre_private_key

   # ✅ VALIDE (vraie clé):
   PRIVATE_KEY=0x1234567890abcdef...
   ```

2. **RPC_URL doit être accessible:**
   ```bash
   # Tester la connexion:
   curl -X POST https://mainnet.base.org \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
   ```

   **Résultat attendu:**
   ```json
   {"jsonrpc":"2.0","id":1,"result":"0x241e34f"}
   ```

---

## Scénarios probables et solutions

### Scénario A: Scanner attend simplement (PLUS PROBABLE)

**Symptôme:** Service tourne, pas d'erreur, mais silence pendant 30+ secondes.

**Explication:**
- Le Scanner attend `SCAN_INTERVAL_SECONDS` (30s par défaut) entre chaque scan
- DexScreener peut ne pas retourner de nouvelles paires immédiatement

**Solution:** Attendre 60 secondes et vérifier à nouveau:
```bash
journalctl -u basebot-scanner -f
# Attendre 60 secondes...
```

---

### Scénario B: Logs en buffer (PROBABLE)

**Symptôme:** Test manuel fonctionne, mais journalctl ne montre rien.

**Explication:** Python met les logs en buffer, ils n'apparaissent pas en temps réel dans systemd.

**Solution:** Désactiver le buffering dans le service:
```bash
nano /etc/systemd/system/basebot-scanner.service

# Ajouter dans [Service]:
Environment="PYTHONUNBUFFERED=1"

# Sauvegarder et recharger:
systemctl daemon-reload
systemctl restart basebot-scanner
journalctl -u basebot-scanner -f
```

---

### Scénario C: PRIVATE_KEY non configurée (POSSIBLE)

**Symptôme:** Le test Python montre `❌ PRIVATE_KEY: NON DÉFINI`.

**Explication:** Le Scanner ne peut pas initialiser Web3Manager sans clé privée valide.

**Solution:**
```bash
nano /home/basebot/trading-bot/config/.env

# Trouver la ligne PRIVATE_KEY et remplacer par votre vraie clé:
PRIVATE_KEY=0xVOTRE_CLE_PRIVEE_ICI
```

⚠️ **Sécurité:**
- Utiliser un wallet dédié (pas votre wallet principal)
- Ne jamais partager cette clé
- Commencer avec un petit montant pour tester

Puis:
```bash
systemctl restart basebot-scanner
```

---

### Scénario D: RPC_URL inaccessible (RARE)

**Symptôme:** Test connexion Web3 échoue: `Connecté: False`.

**Solution:** Changer le RPC dans .env:
```bash
nano /home/basebot/trading-bot/config/.env

# Essayer les RPC suivants (dans l'ordre):
RPC_URL=https://mainnet.base.org
# OU
RPC_URL=https://base.drpc.org
# OU
RPC_URL=https://base-rpc.publicnode.com
```

---

## Commandes de monitoring en continu

### Voir les logs en temps réel:
```bash
journalctl -u basebot-scanner -f
```

### Voir les 100 dernières lignes:
```bash
journalctl -u basebot-scanner -n 100 --no-pager
```

### Voir le fichier de log applicatif:
```bash
tail -f /home/basebot/trading-bot/logs/scanner.log
```

### Statut du service:
```bash
systemctl status basebot-scanner
```

### Vérifier le processus:
```bash
ps aux | grep Scanner.py
```

---

## Timeline de diagnostic (15 minutes maximum)

| Temps | Action | Durée |
|-------|--------|-------|
| 0-5 min | Exécuter `diagnose_scanner.sh` | 5 min |
| 5-7 min | Lire le rapport, identifier les ❌ | 2 min |
| 7-9 min | Test manuel: `python src/Scanner.py` | 2 min |
| 9-12 min | Si échec: `test_scanner_simple.py` | 3 min |
| 12-14 min | Corriger la config (.env, service) | 2 min |
| 14-15 min | Relancer et vérifier: `systemctl restart` | 1 min |

---

## Checklist de résolution

- [ ] Exécuté `diagnose_scanner.sh`
- [ ] Tous les composants sont ✅ dans le diagnostic
- [ ] `PRIVATE_KEY` est configurée (pas la valeur par défaut)
- [ ] `RPC_URL` est accessible (test curl réussi)
- [ ] Test manuel du Scanner produit des logs
- [ ] Ajouté `PYTHONUNBUFFERED=1` au service systemd
- [ ] Service redémarré: `systemctl restart basebot-scanner`
- [ ] Logs apparaissent dans `journalctl -f`

---

## À faire après résolution

Une fois que le Scanner fonctionne:

1. **Vérifier les autres services:**
   ```bash
   systemctl status basebot-filter
   systemctl status basebot-trader
   systemctl status basebot-dashboard
   ```

2. **Activer tous les services:**
   ```bash
   bash /home/basebot/trading-bot/start_all_services.sh
   ```

3. **Configurer le mode de trading:**
   ```bash
   # Mode paper (simulation) par défaut - RECOMMANDÉ
   # Vérifier dans .env:
   grep "TRADING_MODE" /home/basebot/trading-bot/config/.env
   ```

4. **Accéder au dashboard:**
   - Ouvrir dans le navigateur: `http://VOTRE_IP_VPS:8501`

---

## Support

Si le problème persiste après avoir suivi toutes ces étapes:

1. **Collecter les diagnostics:**
   ```bash
   cd /home/basebot/trading-bot
   bash diagnose_scanner.sh > diagnostic.txt 2>&1
   python test_scanner_simple.py > test_python.txt 2>&1
   journalctl -u basebot-scanner -n 200 > systemd_logs.txt 2>&1
   ```

2. **Partager les fichiers générés:**
   - `diagnostic.txt`
   - `test_python.txt`
   - `systemd_logs.txt`

---

**Dernière mise à jour:** 2025-11-07
**Temps estimé de résolution:** 10-15 minutes
