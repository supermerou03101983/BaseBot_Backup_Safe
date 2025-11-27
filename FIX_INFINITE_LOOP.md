# 🔧 FIX: Boucle Infinie sur Token Rejeté

## 📋 Problème Identifié

**Date:** 2025-11-17
**Symptôme:** Bot "freezé" avec positions bloquées
**Cause réelle:** Boucle infinie de re-validation sur ORACLE token

### 🔍 Analyse du Problème

**Logs observés:**
```
Nov 17 10:39:48 - INFO - ✨ Token sélectionné: ORACLE (Momentum: 65.0/100)
Nov 17 10:39:48 - WARNING - ❌ Token ORACLE rejeté à la re-validation: Volume 24h a chuté
[Se répète chaque seconde infiniment...]
```

**Flux du bug:**
1. `get_next_approved_token()` retourne ORACLE (meilleur score: 65/100)
2. `execute_buy()` appelle `validate_token_before_buy()`
3. Re-validation échoue: "Volume 24h a chuté"
4. `execute_buy()` retourne `False`
5. Boucle principale rappelle immédiatement `get_next_approved_token()`
6. **ORACLE est encore retourné** (toujours le meilleur score!)
7. → Boucle infinie ♾️

**Impact:**
- CPU à 100% sur boucle de re-validation
- Positions existantes **ignorées** (update jamais appelé)
- Apparence de "freeze" alors que le bot tourne en boucle

---

## ✅ Solution Implémentée

### **Système de Cooldown pour Tokens Rejetés**

**Principe:**
- Quand un token échoue à la re-validation, il est mis en **cooldown** pendant 30 minutes
- Pendant le cooldown, le token est **ignoré** par `get_next_approved_token()`
- Après 30 min, le cooldown expire automatiquement

### **Modifications Apportées**

#### **1. Attributs de classe ([Trader.py:107-109](src/Trader.py#L107-L109))**

```python
# Cooldown pour tokens rejetés (éviter boucles infinies)
self.rejected_tokens_cooldown = {}  # {token_address: timestamp}
self.cooldown_minutes = int(os.getenv('REJECTED_TOKEN_COOLDOWN_MINUTES', 30))
```

#### **2. Méthodes de gestion du cooldown ([Trader.py:296-328](src/Trader.py#L296-L328))**

```python
def is_token_in_cooldown(self, token_address: str) -> bool:
    """Vérifie si un token est en cooldown (rejeté récemment)"""
    if token_address not in self.rejected_tokens_cooldown:
        return False

    cooldown_time = self.rejected_tokens_cooldown[token_address]
    elapsed_minutes = (datetime.now() - cooldown_time).total_seconds() / 60

    if elapsed_minutes < self.cooldown_minutes:
        return True
    else:
        # Cooldown expiré, on peut le retirer
        del self.rejected_tokens_cooldown[token_address]
        return False

def add_token_to_cooldown(self, token_address: str, symbol: str, reason: str):
    """Ajoute un token au cooldown après rejet"""
    self.rejected_tokens_cooldown[token_address] = datetime.now()
    self.logger.warning(
        f"⏸️  {symbol} ajouté au cooldown ({self.cooldown_minutes} min) - Raison: {reason}"
    )

def cleanup_expired_cooldowns(self):
    """Nettoie les cooldowns expirés (appelé périodiquement)"""
    expired = [
        addr for addr, timestamp in self.rejected_tokens_cooldown.items()
        if (datetime.now() - timestamp).total_seconds() / 60 >= self.cooldown_minutes
    ]
    for addr in expired:
        del self.rejected_tokens_cooldown[addr]

    if expired:
        self.logger.info(f"🧹 {len(expired)} cooldowns expirés nettoyés")
```

#### **3. Filtrage dans get_next_approved_token() ([Trader.py:393-398](src/Trader.py#L393-L398))**

```python
# SKIP tokens en cooldown (rejetés récemment)
if self.is_token_in_cooldown(token_data['address']):
    self.logger.info(
        f"⏸️  {token_data['symbol']} ignoré (en cooldown après rejet récent)"
    )
    continue
```

#### **4. Ajout au cooldown après échec validation ([Trader.py:728-736](src/Trader.py#L728-L736))**

```python
# RE-VALIDATION avant achat (protection contre tokens obsolètes/rug)
is_valid, reason, fresh_price = self.validate_token_before_buy(token)
if not is_valid:
    self.logger.warning(
        f"❌ Token {token['symbol']} rejeté à la re-validation: {reason}"
    )
    # Ajouter au cooldown pour éviter boucle infinie
    self.add_token_to_cooldown(token['address'], token['symbol'], reason)
    return False
```

#### **5. Nettoyage périodique ([Trader.py:1433-1436](src/Trader.py#L1433-L1436))**

```python
# Log performance toutes les heures
if time.time() - last_performance_log > 3600:
    self.log_performance_metrics()
    self.cleanup_expired_cooldowns()  # Nettoyer cooldowns expirés
    last_performance_log = time.time()
```

---

## 📊 Comportement Après Fix

### **Scénario Typique:**

```
10:39:00 - ✨ Token sélectionné: ORACLE (Momentum: 65.0/100)
10:39:00 - ❌ Token ORACLE rejeté à la re-validation: Volume 24h a chuté
10:39:00 - ⏸️  ORACLE ajouté au cooldown (30 min) - Raison: Volume 24h a chuté
10:39:01 - ✨ Token sélectionné: DEL (Momentum: 58.0/100)
10:39:01 - ✅ Achat reussi: DEL
[...]
10:40:00 - ⏸️  ORACLE ignoré (en cooldown après rejet récent)
[...]
11:09:00 - 🧹 1 cooldowns expirés nettoyés
11:09:01 - ✨ Token sélectionné: ORACLE (Momentum: 65.0/100)  # Nouvelle tentative
```

### **Avantages:**

✅ **Plus de boucle infinie** - Token rejeté ignoré pendant 30 min
✅ **Positions mises à jour normalement** - CPU libéré pour monitoring
✅ **Passage au 2ème meilleur token** - Trading continue sans interruption
✅ **Re-tentative automatique après cooldown** - Si conditions s'améliorent
✅ **Configuration flexible** - Variable d'environnement `REJECTED_TOKEN_COOLDOWN_MINUTES`

---

## ⚙️ Configuration

### **Variable d'environnement (.env):**

```bash
# Durée du cooldown pour tokens rejetés (en minutes)
# Défaut: 30 minutes
REJECTED_TOKEN_COOLDOWN_MINUTES=30
```

**Valeurs recommandées:**
- `15` - Mode agressif (re-test rapide si conditions changent)
- `30` - Mode équilibré (défaut recommandé)
- `60` - Mode conservateur (évite spam sur tokens problématiques)

---

## 🧪 Tests à Effectuer

### **1. Test de la boucle infinie (résolu):**

**Avant le fix:**
- ORACLE sélectionné en boucle
- CPU 100%
- Positions ignorées

**Après le fix:**
- ORACLE ajouté au cooldown
- Passage au token suivant (DEL)
- Positions mises à jour normalement

### **2. Test du cooldown expiré:**

- Attendre 30+ minutes
- Vérifier que ORACLE est réessayé après expiration
- Log attendu: `🧹 1 cooldowns expirés nettoyés`

### **3. Test multi-tokens en cooldown:**

- Plusieurs tokens rejetés simultanément
- Vérifier que tous sont ignorés
- Bot passe au premier token non-cooldown

---

## 📝 Logs Générés

### **Ajout au cooldown:**
```
⏸️  ORACLE ajouté au cooldown (30 min) - Raison: Volume 24h a chuté
```

### **Token ignoré pendant cooldown:**
```
⏸️  ORACLE ignoré (en cooldown après rejet récent)
```

### **Nettoyage cooldowns expirés:**
```
🧹 3 cooldowns expirés nettoyés
```

---

## 🚀 Déploiement

### **Sur VPS (après commit):**

```bash
# 1. Pull dernière version
cd /home/basebot/trading-bot
git pull origin main

# 2. Redémarrer le trader
sudo systemctl restart basebot-trader

# 3. Vérifier les logs
sudo journalctl -u basebot-trader -f | grep -E "cooldown|sélectionné|rejeté"
```

### **Vérification post-déploiement:**

```bash
# Attendre quelques minutes, puis vérifier qu'aucune boucle infinie:
bot-status

# Devrait montrer:
# - Pas de CPU à 100%
# - Positions mises à jour normalement
# - Logs variés (pas répétition du même token)
```

---

## 🎯 Critères de Validation

**Le fix sera validé si:**

- ✅ Aucune boucle infinie détectée sur 48h
- ✅ CPU moyen <20% (vs 100% avant)
- ✅ Positions mises à jour toutes les 10 secondes
- ✅ Cooldowns appliqués correctement (logs `⏸️`)
- ✅ Nettoyage auto toutes les heures (logs `🧹`)

---

## 📈 Impact Attendu

**Avant:**
- 🔴 Freeze apparent avec positions bloquées
- 🔴 CPU 100% sur boucle infinie
- 🔴 Aucun nouveau trade possible
- 🔴 Monitoring arrêté

**Après:**
- ✅ Trading continu sans interruption
- ✅ CPU normal <20%
- ✅ Passage automatique au token suivant
- ✅ Monitoring actif en permanence

---

## 🔍 Code Review Checklist

- [x] Cooldown dictionary initialisé
- [x] Check cooldown avant sélection token
- [x] Ajout cooldown après échec validation
- [x] Nettoyage périodique cooldowns expirés
- [x] Logs informatifs à chaque étape
- [x] Configuration via variable d'environnement
- [x] Gestion des timestamps correcte
- [x] Pas d'impact sur performances

---

**Créé:** 2025-11-17
**Auteur:** Claude Code
**Commit:** À venir
**Statut:** ✅ Prêt pour déploiement
