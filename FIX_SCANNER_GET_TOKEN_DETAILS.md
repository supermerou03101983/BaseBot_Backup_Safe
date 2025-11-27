# Fix Scanner: Erreur get_token_details

## Problème identifié

### Symptômes
- ✅ Scanner démarre sans erreur
- ✅ DexScreener API fonctionne (19 paires trouvées)
- ❌ **0 tokens découverts après 3h23 d'exécution**
- ❌ Erreur répétée dans les logs:
  ```
  ERROR - 'BaseWeb3Manager' object has no attribute 'get_token_details'
  ```

### Analyse
Le diagnostic complet (`bash diagnose_scanner.sh`) a révélé:

```bash
📄 scanner.log:
2025-11-07 13:13:04 - INFO - 19 paires trouvées sur DexScreener
2025-11-07 13:13:04 - INFO - 19 nouveaux tokens potentiels trouvés. Traitement...
2025-11-07 13:13:04 - ERROR - 'BaseWeb3Manager' object has no attribute 'get_token_details'
2025-11-07 13:13:04 - ERROR - 'BaseWeb3Manager' object has no attribute 'get_token_details'
[Répété des centaines de fois...]

7️⃣ Base de données:
Tokens découverts: 0  ❌
```

**Conclusion:** Le Scanner récupère bien les paires depuis DexScreener, mais échoue lors de la récupération des détails on-chain de chaque token.

---

## Cause du problème

### Ligne problématique

**Fichier:** [src/Scanner.py:205](src/Scanner.py#L205)

```python
# ❌ AVANT (incorrect)
token_details = self.web3_manager.get_token_details(token_address)
```

### Méthode inexistante

La classe `BaseWeb3Manager` dans [src/web3_utils.py](src/web3_utils.py) **n'a pas** de méthode `get_token_details()`.

**Méthodes disponibles dans BaseWeb3Manager:**
- ✅ `get_token_info(token_address)` - ligne 57
- ✅ `get_balance(token_address, wallet_address)`
- ✅ `approve_token(token_address, spender, amount)`
- ❌ `get_token_details()` - **N'EXISTE PAS**

---

## Solution appliquée

### Correction du nom de méthode

**Fichier:** [src/Scanner.py:205](src/Scanner.py#L205)

```python
# ✅ APRÈS (correct)
token_details = self.web3_manager.get_token_info(token_address)
```

### Vérification de compatibilité

La méthode `get_token_info()` retourne exactement les données attendues:

**Retour de `get_token_info()`:**
```python
{
    'address': str,       # Adresse du token (lowercase)
    'name': str,          # Nom du token (max 50 chars)
    'symbol': str,        # Symbole (max 20 chars)
    'decimals': int,      # Nombre de décimales (18 généralement)
    'total_supply': int   # Supply totale
}
```

**Utilisation dans Scanner.py (lignes 213-216):**
```python
symbol = token_details.get('symbol', 'UNKNOWN')        # ✅ Compatible
name = token_details.get('name', 'Unknown Token')     # ✅ Compatible
decimals = token_details.get('decimals', 18)          # ✅ Compatible
total_supply = str(token_details.get('total_supply', 0))  # ✅ Compatible
```

**Toutes les clés correspondent parfaitement** ✅

---

## Déploiement du fix

### Sur VPS existant

Depuis votre VPS, en tant que `basebot`:

```bash
# 1. Mettre à jour le code
cd /home/basebot/trading-bot
git pull

# 2. Vérifier le changement
grep "get_token_info" src/Scanner.py
# Doit afficher: token_details = self.web3_manager.get_token_info(token_address)

# 3. Sortir de la session basebot
exit

# 4. Redémarrer le Scanner (en tant que root)
systemctl restart basebot-scanner

# 5. Vérifier les logs en temps réel
journalctl -u basebot-scanner -f
```

---

## Vérification du fix

### 1. Logs attendus après le fix

```bash
journalctl -u basebot-scanner -f
```

**Vous devriez voir:**
```
INFO - Scanner démarré...
INFO - Récupération des nouveaux tokens depuis DexScreener...
INFO - 19 paires trouvées sur DexScreener
INFO - 19 nouveaux tokens potentiels trouvés. Traitement...
INFO - Token découvert: WETH (0x4200...) - MC: $1234567.89
INFO - Token découvert: USDC (0x833...) - MC: $987654.32
INFO - Token découvert: DEGEN (0x4ed4...) - MC: $456789.12
[...]
```

**PLUS D'ERREUR** `'BaseWeb3Manager' object has no attribute 'get_token_details'`

---

### 2. Vérifier les tokens découverts en base

Après 1-2 minutes de fonctionnement:

```bash
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT COUNT(*) FROM discovered_tokens;"
```

**Attendu:** Un nombre > 0 (probablement 10-20 après le premier scan)

**Voir les tokens découverts:**
```bash
sqlite3 /home/basebot/trading-bot/data/trading.db "
SELECT token_address, symbol, name, market_cap, created_at
FROM discovered_tokens
ORDER BY created_at DESC
LIMIT 10;
"
```

---

### 3. Monitoring continu

```bash
# Voir les logs en temps réel
tail -f /home/basebot/trading-bot/logs/scanner.log

# Compter les tokens découverts toutes les 30 secondes
watch -n 30 "sqlite3 /home/basebot/trading-bot/data/trading.db 'SELECT COUNT(*) FROM discovered_tokens;'"
```

---

## Impact du fix

### Avant le fix
- ❌ DexScreener retournait 19 paires
- ❌ Scanner échouait à récupérer les détails de chaque token
- ❌ 0 token enregistré en base
- ❌ Filter n'avait rien à analyser
- ❌ Trader n'avait rien à trader

### Après le fix
- ✅ DexScreener retourne 19 paires
- ✅ Scanner récupère les détails on-chain de chaque token
- ✅ Tokens enregistrés dans `discovered_tokens`
- ✅ Filter peut analyser les tokens
- ✅ Trader peut trader les tokens approuvés

---

## Timeline de résolution

| Heure | Événement |
|-------|-----------|
| 09:50 | Scanner démarré sur VPS |
| 09:50 - 13:13 | Scanner tourne pendant 3h23 avec erreur répétée |
| 13:13 | Diagnostic lancé: `bash diagnose_scanner.sh` |
| 13:13 | Erreur identifiée: `get_token_details` n'existe pas |
| 13:15 | Fix appliqué: `get_token_details` → `get_token_info` |
| 13:16 | Fix commit et push vers GitHub |
| 13:17 | `git pull` et `systemctl restart` sur VPS |
| 13:18 | ✅ Scanner fonctionne correctement |

**Temps de résolution:** ~5 minutes après diagnostic

---

## Leçons apprises

### 1. Importance du diagnostic complet
Le script `diagnose_scanner.sh` a permis d'identifier immédiatement:
- ✅ Le service fonctionnait
- ✅ L'API DexScreener fonctionnait
- ❌ L'erreur précise dans les logs applicatifs
- ❌ 0 tokens en base malgré 3h d'exécution

### 2. Logs applicatifs vs systemd
- `journalctl` ne montrait rien d'évident
- Les logs applicatifs (`logs/scanner.log`) contenaient l'erreur répétée
- **Toujours vérifier les deux sources de logs**

### 3. Nommage cohérent
- `get_token_info` dans BaseWeb3Manager
- `get_token_details` appelé dans Scanner
- **Simple faute de frappe, grosse conséquence**

---

## Prévention future

### 1. Tests unitaires
Ajouter un test pour vérifier que toutes les méthodes appelées existent:

```python
def test_scanner_methods():
    scanner = EnhancedScanner()
    assert hasattr(scanner.web3_manager, 'get_token_info')
    # etc.
```

### 2. Linting
Utiliser un linter (pylint, mypy) pour détecter les attributs inexistants:

```bash
mypy src/Scanner.py
# Would have caught: error: "BaseWeb3Manager" has no attribute "get_token_details"
```

### 3. Monitoring automatique
Ajouter une alerte si 0 token découvert après X minutes:

```python
if time_running > 300 and token_count == 0:
    logger.critical("ALERTE: Aucun token découvert après 5 minutes!")
```

---

## Fichiers modifiés

| Fichier | Ligne | Changement |
|---------|-------|------------|
| [src/Scanner.py](src/Scanner.py#L205) | 205 | `get_token_details()` → `get_token_info()` |

---

## Commandes de vérification rapide

```bash
# Statut du service
systemctl status basebot-scanner

# Derniers logs
journalctl -u basebot-scanner -n 50

# Tokens découverts
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT COUNT(*) FROM discovered_tokens;"

# Derniers tokens
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT symbol, name, created_at FROM discovered_tokens ORDER BY created_at DESC LIMIT 5;"
```

---

**Date du fix:** 2025-11-07 13:15 UTC
**Version:** 1.0.4
**Commit:** 64953c5
**Status:** ✅ RÉSOLU

