#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trader - Trading reel avec strategie unique optimisee
"""

import sqlite3
import json
import time
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from pathlib import Path
from decimal import Decimal

PROJECT_DIR = Path(__file__).parent.parent
sys.path.append(str(PROJECT_DIR))

from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
from web3_utils import (
    BaseWeb3Manager, UniswapV3Manager,
    DexScreenerAPI, CoinGeckoAPI
)
from honeypot_checker import HoneypotChecker

load_dotenv(PROJECT_DIR / 'config' / '.env')

class Position:
    """Represente une position ouverte avec gestion avancee"""
    def __init__(self, token_address: str, symbol: str, entry_price: float,
                 amount: float, amount_eth: float):
        self.token_address = token_address
        self.symbol = symbol
        self.entry_price = entry_price
        self.current_price = entry_price
        self.amount = amount
        self.amount_eth = amount_eth
        self.entry_time = datetime.now()
        self.max_price = entry_price
        self.current_level = 0
        self.stop_loss = entry_price * 0.95  # Stop loss fixe a -5%
        self.trailing_config = None
        self.trailing_active = False
        self.highest_price = entry_price

        # Grace period: 3 minutes avec stop loss élargi
        self.grace_period_minutes = 3
        self.grace_period_stop_loss_percent = 35  # -35% pendant grace period
        self.normal_stop_loss_percent = 5  # -5% après grace period
        self.grace_period_active = True

    def get_active_stop_loss_percent(self):
        """Retourne le stop loss actif selon le grace period"""
        time_since_entry = (datetime.now() - self.entry_time).total_seconds() / 60  # en minutes

        if time_since_entry < self.grace_period_minutes:
            # Pendant le grace period: stop loss élargi
            return self.grace_period_stop_loss_percent
        else:
            # Après le grace period: stop loss normal
            if self.grace_period_active:
                # Première fois qu'on sort du grace period
                self.grace_period_active = False
            return self.normal_stop_loss_percent

    def is_in_grace_period(self):
        """Vérifie si la position est encore dans le grace period"""
        time_since_entry = (datetime.now() - self.entry_time).total_seconds() / 60
        return time_since_entry < self.grace_period_minutes

class RealTrader:
    def __init__(self):
        # Creer les dossiers necessaires
        (PROJECT_DIR / 'data').mkdir(parents=True, exist_ok=True)
        (PROJECT_DIR / 'logs').mkdir(parents=True, exist_ok=True)
        (PROJECT_DIR / 'config').mkdir(parents=True, exist_ok=True)
        
        self.db_path = PROJECT_DIR / 'data' / 'trading.db'
        self.setup_logging()
        
        # Web3 setup avec gestion d'erreur
        try:
            self.web3_manager = BaseWeb3Manager(
                rpc_url=os.getenv('RPC_URL', 'https://mainnet.base.org'),
                private_key=os.getenv('PRIVATE_KEY')
            )
            
            self.uniswap = UniswapV3Manager(self.web3_manager)
            self.dexscreener = DexScreenerAPI()
            self.coingecko = CoinGeckoAPI(os.getenv('COINGECKO_API_KEY'))
            self.honeypot_checker = HoneypotChecker()
        except Exception as e:
            self.logger.error(f"Erreur initialisation Web3: {e}")
            raise
        
        # Configuration de trading
        self.load_config()
        self.positions = {}
        self.load_positions()
        self.daily_trades = 0
        self.last_trade_day = None

        # Cooldown pour tokens rejetés (éviter boucles infinies)
        self.rejected_tokens_cooldown = {}  # {token_address: timestamp}
        self.cooldown_minutes = int(os.getenv('REJECTED_TOKEN_COOLDOWN_MINUTES', 30))
        
        # Router ABI pour Uniswap V3
        self.router_abi = json.loads('''[
            {
                "inputs": [
                    {
                        "components": [
                            {"internalType": "address", "name": "tokenIn", "type": "address"},
                            {"internalType": "address", "name": "tokenOut", "type": "address"},
                            {"internalType": "uint24", "name": "fee", "type": "uint24"},
                            {"internalType": "address", "name": "recipient", "type": "address"},
                            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                            {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                        ],
                        "internalType": "struct ISwapRouter.ExactInputSingleParams",
                        "name": "params",
                        "type": "tuple"
                    }
                ],
                "name": "exactInputSingle",
                "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function"
            }
        ]''')
        
        try:
            self.router = self.web3_manager.w3.eth.contract(
                address=Web3.to_checksum_address(self.uniswap.router),
                abi=self.router_abi
            )
        except Exception as e:
            self.logger.error(f"Erreur initialisation router: {e}")
            raise
    
    def setup_logging(self):
        """Configuration du logging"""
        log_file = PROJECT_DIR / 'logs' / 'trader.log'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_config(self):
        """Charge la configuration avec nouvelle strategie"""
        # Mode de trading
        mode_file = PROJECT_DIR / 'config' / 'trading_mode.json'
        try:
            if mode_file.exists():
                with open(mode_file, 'r') as f:
                    data = json.load(f)
                    self.trading_mode = data.get('mode', 'paper')
            else:
                self.trading_mode = 'paper'
                with open(mode_file, 'w') as f:
                    json.dump({'mode': 'paper'}, f)
        except Exception as e:
            self.logger.error(f"Erreur chargement config: {e}")
            self.trading_mode = 'paper'
                
        # Configuration depuis l'environnement
        self.position_size_percent = float(os.getenv('POSITION_SIZE_PERCENT', 15))
        self.max_positions = int(os.getenv('MAX_POSITIONS', 2))
        self.max_trades_per_day = int(os.getenv('MAX_TRADES_PER_DAY', 3))
        self.stop_loss_percent = float(os.getenv('STOP_LOSS_PERCENT', 5))
        self.monitoring_interval = int(os.getenv('MONITORING_INTERVAL', 1))
        self.token_max_age_hours = int(os.getenv('TOKEN_APPROVAL_MAX_AGE_HOURS', 12))
        
        # Configuration trailing stop unique
        self.trailing_config = {
            'activation_threshold': float(os.getenv('TRAILING_ACTIVATION_THRESHOLD', 12)),
            'levels': [
                {'min_profit': 12, 'max_profit': 30, 'distance': 3},
                {'min_profit': 30, 'max_profit': 100, 'distance': 5},
                {'min_profit': 100, 'max_profit': 300, 'distance': 10},
                {'min_profit': 300, 'max_profit': 99999, 'distance': 30}
            ]
        }
        
        # Configuration Time Exit Intelligent
        self.time_exit_config = {
            'stagnation': {
                'hours': int(os.getenv('TIME_EXIT_STAGNATION_HOURS', 24)),
                'min_profit': float(os.getenv('TIME_EXIT_STAGNATION_MIN_PROFIT', 5))
            },
            'low_momentum': {
                'hours': int(os.getenv('TIME_EXIT_LOW_MOMENTUM_HOURS', 48)),
                'min_profit': float(os.getenv('TIME_EXIT_LOW_MOMENTUM_MIN_PROFIT', 20))
            },
            'maximum': {
                'hours': int(os.getenv('TIME_EXIT_MAXIMUM_HOURS', 72)),
                'force_exit': True
            },
            'emergency': {
                'hours': int(os.getenv('TIME_EXIT_EMERGENCY_HOURS', 120)),
                'force_exit': True
            }
        }
        
        # Metriques de performance
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit_percent': 0,
            'best_trade': 0,
            'worst_trade': 0,
            'time_exits': 0,
            'trailing_exits': 0,
            'stoploss_exits': 0
        }
    
    def save_position_state(self, position):
        """Sauvegarde l'etat d'une position avec metadonnees etendues"""
        try:
            state_file = PROJECT_DIR / 'data' / f'position_{position.token_address}.json'
            with open(state_file, 'w') as f:
                json.dump({
                    'token_address': position.token_address,
                    'symbol': position.symbol,
                    'entry_price': position.entry_price,
                    'current_price': position.current_price,  # AJOUT: prix actuel pour Dashboard
                    'amount': position.amount,
                    'amount_eth': position.amount_eth,
                    'stop_loss': position.stop_loss,
                    'current_level': position.current_level,
                    'entry_time': position.entry_time.isoformat() if position.entry_time else None,
                    'max_price': position.max_price,
                    'highest_price': position.highest_price,
                    'trailing_active': position.trailing_active,
                    'trailing_config': position.trailing_config
                }, f)
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde position {position.symbol}: {e}")
            
    def load_positions(self):
        """Recupere les positions au demarrage"""
        state_dir = PROJECT_DIR / 'data'
        loaded_count = 0
        
        if not state_dir.exists():
            return
            
        for state_file in state_dir.glob('position_*.json'):
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    
                position = Position(
                    data['token_address'],
                    data['symbol'],
                    data['entry_price'],
                    data['amount'],
                    data['amount_eth']
                )
                
                position.stop_loss = data['stop_loss']
                position.current_level = data['current_level']
                position.max_price = data.get('max_price', data['entry_price'])
                position.highest_price = data.get('highest_price', data['entry_price'])
                position.trailing_active = data.get('trailing_active', False)
                position.trailing_config = data.get('trailing_config')
                
                if data.get('entry_time'):
                    position.entry_time = datetime.fromisoformat(data['entry_time'])
                    
                self.positions[data['token_address']] = position
                loaded_count += 1
                
                self.logger.info(f"Position recuperee: {data['symbol']}")
                
            except Exception as e:
                self.logger.error(f"Erreur chargement position {state_file}: {e}")
                
        if loaded_count > 0:
            self.logger.info(f"✅ {loaded_count} positions recuperees")

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

    def get_next_token(self) -> Optional[Dict]:
        """
        Recupere le prochain token a trader avec priorisation par momentum
        Récupère les 5 meilleurs candidats et choisit celui avec le meilleur momentum actuel
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Recuperer TOP 5 tokens frais (pas expirés)
            cursor.execute("""
                SELECT at.token_address, at.symbol, at.name, at.score,
                       dt.liquidity, dt.market_cap, dt.price_usd, dt.volume_24h,
                       at.created_at
                FROM approved_tokens at
                LEFT JOIN discovered_tokens dt ON at.token_address = dt.token_address
                WHERE at.token_address NOT IN (
                    SELECT token_address FROM trade_history WHERE exit_time IS NULL
                )
                AND datetime(at.created_at) > datetime('now', '-' || ? || ' hours')
                ORDER BY at.score DESC, at.created_at DESC
                LIMIT 5
            """, (self.token_max_age_hours,))

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                # Vérifier tokens expirés
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM approved_tokens
                    WHERE token_address NOT IN (
                        SELECT token_address FROM trade_history WHERE exit_time IS NULL
                    )
                    AND datetime(created_at) <= datetime('now', '-' || ? || ' hours')
                """, (self.token_max_age_hours,))
                expired_count = cursor.fetchone()[0]
                conn.close()

                if expired_count > 0:
                    self.logger.warning(
                        f"⏰ {expired_count} tokens approuvés ont expiré "
                        f"(>{self.token_max_age_hours}h) - Aucun token frais disponible"
                    )
                return None

            # Calculer le momentum score pour chaque candidat
            candidates = []
            for row in rows:
                token_data = {
                    'address': row[0],
                    'symbol': row[1],
                    'name': row[2],
                    'score': row[3],
                    'liquidity': row[4] or 0,
                    'market_cap': row[5] or 0,
                    'price_usd': row[6] or 0,
                    'volume_24h': row[7] or 0,
                    'created_at': row[8]
                }

                # SKIP tokens en cooldown (rejetés récemment)
                if self.is_token_in_cooldown(token_data['address']):
                    self.logger.info(
                        f"⏸️  {token_data['symbol']} ignoré (en cooldown après rejet récent)"
                    )
                    continue

                # Obtenir données fraîches pour momentum
                dex_data = self.dexscreener.get_token_info(token_data['address'])
                if dex_data:
                    momentum_score = self.calculate_momentum_score(token_data, dex_data)
                    token_data['momentum_score'] = momentum_score
                    token_data['dex_data'] = dex_data
                    candidates.append(token_data)

            if not candidates:
                self.logger.warning("Aucun candidat avec données DexScreener disponibles")
                return None

            # Trier par momentum score (meilleur en premier)
            candidates.sort(key=lambda x: x['momentum_score'], reverse=True)

            # Log les scores des candidats
            self.logger.info(f"🎯 {len(candidates)} candidats évalués:")
            for i, c in enumerate(candidates[:3], 1):  # Top 3
                self.logger.info(
                    f"  {i}. {c['symbol']}: Momentum={c['momentum_score']:.1f} "
                    f"Score={c['score']:.1f} Age={c.get('created_at', 'N/A')[:16]}"
                )

            # Retourner le meilleur
            best = candidates[0]
            self.logger.info(
                f"✨ Token sélectionné: {best['symbol']} (Momentum: {best['momentum_score']:.1f}/100)"
            )

            return best

        except Exception as e:
            self.logger.error(f"Erreur recuperation token: {e}")
            return None
        
    def validate_token_before_buy(self, token: Dict) -> tuple[bool, str, float]:
        """
        Re-valide un token avant achat (vérification de fraîcheur des données)
        Retourne (is_valid, reason, fresh_price)
        """
        try:
            # Critères minimums depuis les variables d'environnement
            min_liquidity = float(os.getenv('MIN_LIQUIDITY_USD', '30000'))
            min_volume_24h = float(os.getenv('MIN_VOLUME_24H', '50000'))

            # Obtenir données fraîches depuis DexScreener (PRIORITÉ: prix frais)
            dex_data = self.dexscreener.get_token_info(token['address'])
            if not dex_data:
                return False, "Impossible d'obtenir données DexScreener", 0

            # Récupérer le prix frais (CRITICAL pour éviter faux gains)
            fresh_price = dex_data.get('price_usd', 0)
            if fresh_price <= 0:
                return False, "Prix frais invalide ou non disponible", 0

            # Vérifier que la liquidité n'a pas été retirée (rug pull)
            fresh_liquidity = dex_data.get('liquidity_usd', 0)  # Clé corrigée
            if fresh_liquidity < min_liquidity:
                return False, f"Liquidité actuelle trop basse: ${fresh_liquidity:,.0f} (possible rug)", 0

            # Vérifier que le volume n'a pas chuté drastiquement
            fresh_volume = dex_data.get('volume_24h', 0)
            if fresh_volume < min_volume_24h * 0.5:  # Tolérance 50%
                return False, f"Volume 24h a chuté: ${fresh_volume:,.0f} (possible abandon)", 0

            # VÉRIFICATION HONEYPOT (Protection critique)
            self.logger.info(f"🍯 Vérification honeypot pour {token['symbol']}...")
            honeypot_result = self.honeypot_checker.check_token(token['address'], chain_id=8453)

            if honeypot_result.get('error'):
                # Si l'API est down, logger mais ne pas bloquer (mode dégradé)
                self.logger.warning(
                    f"⚠️  API Honeypot indisponible: {honeypot_result['error']} "
                    f"- Trade autorisé en mode dégradé"
                )
            elif not honeypot_result['is_safe']:
                # Token dangereux détecté
                flags = ', '.join(honeypot_result['flags'])
                return False, (
                    f"Token dangereux: {flags} | "
                    f"Risk={honeypot_result['risk_level']} | "
                    f"Taxes: Buy={honeypot_result['buy_tax']:.1f}% Sell={honeypot_result['sell_tax']:.1f}% | "
                    f"Can_Sell={honeypot_result['can_sell']}"
                ), 0
            else:
                # Token safe
                self.logger.info(
                    f"🛡️  Honeypot check PASSED: {token['symbol']} | "
                    f"Taxes: Buy={honeypot_result['buy_tax']:.1f}% Sell={honeypot_result['sell_tax']:.1f}% | "
                    f"Risk={honeypot_result['risk_level']}"
                )

            self.logger.info(
                f"✅ Token {token['symbol']} validé: "
                f"Prix=${fresh_price:.8f} Liq=${fresh_liquidity:,.0f} Vol=${fresh_volume:,.0f}"
            )
            return True, "Token valide", fresh_price

        except Exception as e:
            self.logger.error(f"Erreur validation token {token.get('symbol')}: {e}")
            return False, f"Erreur validation: {str(e)}", 0

    def calculate_momentum_score(self, token: Dict, dex_data: Dict) -> float:
        """
        Calcule un score de momentum dynamique (0-100) pour prioriser les tokens
        Basé sur: tendance prix, ratio vol/liq, vélocité achats, stabilité
        """
        try:
            score = 0.0

            # 1. RATIO VOLUME/LIQUIDITÉ (0-30 points)
            # Plus le volume est élevé par rapport à la liquidité = plus d'activité
            liquidity = dex_data.get('liquidity_usd', 0)  # Clé corrigée
            volume_24h = dex_data.get('volume_24h', 0)

            if liquidity > 0:
                vol_liq_ratio = volume_24h / liquidity
                # Ratio idéal: 1-3 (100-300% du liquidity en volume)
                if vol_liq_ratio > 3:
                    score += 30  # Très actif
                elif vol_liq_ratio > 1.5:
                    score += 25  # Actif
                elif vol_liq_ratio > 0.8:
                    score += 20  # Modéré
                elif vol_liq_ratio > 0.3:
                    score += 10  # Faible
                # Sinon 0 points

            # 2. TENDANCE DE PRIX (0-30 points)
            # Variation prix sur 1h et 24h
            price_change_1h = dex_data.get('price_change_1h', 0)
            price_change_24h = dex_data.get('price_change_24h', 0)

            # 1h doit être positif (momentum court terme)
            if price_change_1h > 10:
                score += 15  # Fort momentum
            elif price_change_1h > 5:
                score += 12  # Bon momentum
            elif price_change_1h > 0:
                score += 8   # Momentum positif
            # Négatif = 0 points

            # 24h doit être positif mais pas trop (éviter FOMO)
            if 0 < price_change_24h < 50:
                score += 15  # Tendance saine
            elif 50 <= price_change_24h < 200:
                score += 10  # Tendance forte
            elif price_change_24h >= 200:
                score += 5   # Risque de correction
            # Négatif = 0 points

            # 3. BUY PRESSURE (0-25 points)
            # Ratio buy/sell transactions
            txns = dex_data.get('txns', {})
            buys = txns.get('buys', 0)
            sells = txns.get('sells', 0)

            if buys + sells > 0:
                buy_ratio = buys / (buys + sells)
                if buy_ratio > 0.7:
                    score += 25  # Forte pression acheteuse
                elif buy_ratio > 0.6:
                    score += 20  # Bonne pression
                elif buy_ratio > 0.5:
                    score += 15  # Équilibré
                elif buy_ratio > 0.4:
                    score += 10  # Légère vente
                # < 0.4 = pression vendeuse (0 points)

            # 4. STABILITÉ (0-15 points)
            # Pas de dump récent (basé sur variation 1h)
            price_change_1h_abs = abs(price_change_1h)

            if price_change_1h_abs < 20:
                score += 15  # Stable
            elif price_change_1h_abs < 40:
                score += 10  # Modéré
            elif price_change_1h_abs < 60:
                score += 5   # Volatil
            # > 60% = très volatil (0 points)

            return min(score, 100)  # Cap à 100

        except Exception as e:
            self.logger.warning(f"Erreur calcul momentum score: {e}")
            return 50.0  # Score neutre par défaut

    def get_eth_balance(self) -> float:
        """Recupere le balance ETH du wallet"""
        try:
            balance_wei = self.web3_manager.w3.eth.get_balance(self.web3_manager.account.address)
            return balance_wei / 10**18
        except Exception as e:
            self.logger.error(f"Erreur recuperation balance ETH: {e}")
            return 0
        
    def calculate_position_size(self) -> float:
        """Calcule la taille de position (15% du wallet)"""
        eth_balance = self.get_eth_balance()
        
        # Garder 0.01 ETH pour les frais de gas
        available = max(0, eth_balance - 0.01)
        
        # 15% du capital disponible
        position_size = available * (self.position_size_percent / 100)
        
        # Limiter entre 0.05 et 2 ETH
        return max(0.05, min(2.0, position_size))
        
    def get_token_balance(self, token_address: str) -> int:
        """Recupere le balance exact d'un token"""
        try:
            token_contract = self.web3_manager.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=self.web3_manager.erc20_abi
            )
            
            balance = token_contract.functions.balanceOf(
                self.web3_manager.account.address
            ).call()
            
            return balance
        except Exception as e:
            self.logger.error(f"Erreur recuperation balance token: {e}")
            return 0
    
    def update_trailing_stop(self, position: Position):
        """Strategie de trailing stop unique avec 4 niveaux"""
        # Protection contre division par zero
        if position.entry_price == 0:
            self.logger.error(f"Prix d'entree invalide pour {position.symbol}")
            return
            
        profit_percent = ((position.current_price - position.entry_price) / 
                         position.entry_price) * 100
        
        # Mettre a jour le plus haut
        if position.current_price > position.highest_price:
            position.highest_price = position.current_price
        
        # Activer le trailing stop a +12%
        if profit_percent >= self.trailing_config['activation_threshold'] and not position.trailing_active:
            position.trailing_active = True
            self.logger.info(
                f"⚡ Trailing active: {position.symbol} a +{profit_percent:.1f}% "
                f"Prix: ${position.current_price:.8f}"
            )
        
        # Si trailing actif, ajuster le stop loss dynamiquement
        if position.trailing_active:
            # Determiner la distance selon le niveau de profit ACTUEL (depuis highest_price)
            # Calculer le profit depuis le pic pour determiner le niveau
            profit_from_peak = ((position.current_price - position.entry_price) /
                               position.entry_price) * 100

            distance = 3  # Par defaut (niveau 1)
            current_level = position.current_level  # Ne JAMAIS descendre

            for i, level in enumerate(self.trailing_config['levels']):
                if level['min_profit'] <= profit_from_peak < level['max_profit']:
                    distance = level['distance']
                    # Le niveau ne peut QUE monter
                    if i + 1 > position.current_level:
                        current_level = i + 1
                    break

            # Calculer le nouveau stop
            new_stop = position.highest_price * (1 - distance / 100)

            # Ne mettre a jour que si le nouveau stop est meilleur
            if new_stop > position.stop_loss or current_level > position.current_level:
                old_stop = position.stop_loss
                position.stop_loss = new_stop
                position.current_level = current_level
                
                self.logger.info(
                    f"📈 Trailing update: {position.symbol} | "
                    f"Profit: +{profit_percent:.1f}% | "
                    f"Niveau: {current_level} | "
                    f"Stop: ${old_stop:.8f} → ${new_stop:.8f} | "
                    f"Distance: -{distance}% du pic (${position.highest_price:.8f})"
                )
                self.save_position_state(position)
    
    def check_time_exit(self, position: Position) -> Tuple[bool, str]:
        """Verifie si une position doit être fermee selon le temps ecoule"""
        if not position.entry_time or position.entry_price == 0:
            return False, ""
        
        hours_held = (datetime.now() - position.entry_time).total_seconds() / 3600
        profit_percent = ((position.current_price - position.entry_price) / 
                         position.entry_price) * 100
        
        # Stagnation: 24h avec profit entre 0% et 5% (ne pas vendre si négatif!)
        if hours_held >= self.time_exit_config['stagnation']['hours']:
            if 0 < profit_percent < self.time_exit_config['stagnation']['min_profit']:
                self.performance_metrics['time_exits'] += 1
                return True, f"Stagnation ({hours_held:.0f}h, +{profit_percent:.1f}%)"

        # Low momentum: 48h avec profit entre 0% et 20% (ne pas vendre si négatif!)
        if hours_held >= self.time_exit_config['low_momentum']['hours']:
            if 0 < profit_percent < self.time_exit_config['low_momentum']['min_profit']:
                self.performance_metrics['time_exits'] += 1
                return True, f"Low momentum ({hours_held:.0f}h, +{profit_percent:.1f}%)"
        
        # Maximum: 72h force exit
        if hours_held >= self.time_exit_config['maximum']['hours']:
            self.performance_metrics['time_exits'] += 1
            return True, f"Max time ({hours_held:.0f}h, +{profit_percent:.1f}%)"
        
        # Emergency: 120h force exit
        if hours_held >= self.time_exit_config['emergency']['hours']:
            self.performance_metrics['time_exits'] += 1
            return True, f"Emergency ({hours_held:.0f}h)"
        
        return False, ""
        
    def execute_buy(self, token: Dict) -> bool:
        """Execute un achat reel ou simule"""
        # Validation des donnees
        if not token.get('address') or not token.get('symbol'):
            self.logger.error("Token invalide: donnees manquantes")
            return False

        if token.get('price_usd', 0) <= 0:
            self.logger.error(f"Prix invalide pour {token['symbol']}: {token.get('price_usd')}")
            return False

        # RE-VALIDATION avant achat (protection contre tokens obsolètes/rug)
        is_valid, reason, fresh_price = self.validate_token_before_buy(token)
        if not is_valid:
            self.logger.warning(
                f"❌ Token {token['symbol']} rejeté à la re-validation: {reason}"
            )
            # Ajouter au cooldown pour éviter boucle infinie
            self.add_token_to_cooldown(token['address'], token['symbol'], reason)
            return False

        # Utiliser le prix FRAIS (pas celui de la DB qui peut être vieux de 48h!)
        entry_price = fresh_price
            
        try:
            weth_address = "0x4200000000000000000000000000000000000006"
            
            if self.trading_mode == 'paper':
                # Mode simulation
                self.logger.info(
                    f"[PAPER] Achat simule: {token['symbol']} @ ${entry_price:.8f}"
                )

                # Simuler la position avec le prix FRAIS
                position = Position(
                    token['address'],
                    token['symbol'],
                    entry_price,  # Prix frais de la re-validation
                    1000000,  # Amount simule
                    0.15  # 0.15 ETH simule (15%)
                )
                position.trailing_config = self.trailing_config

                # Log du grace period activé
                self.logger.info(
                    f"🛡️ Grace period activé pour {token['symbol']}: "
                    f"3 minutes avec stop loss à -35% (puis -5%)"
                )

                self.positions[token['address']] = position
                self.save_position_state(position)

                # Enregistrer dans la DB avec le prix frais
                self.save_trade_to_db(token, 'BUY', entry_price, 0.15, 'paper')

                return True
                
            else:
                # Mode reel
                self.logger.info(f"[REAL] Preparation achat: {token['symbol']}")

                # Calculer la taille de position (15%)
                position_size_eth = self.calculate_position_size()
                position_size_wei = int(position_size_eth * 10**18)

                # Lire slippage depuis .env
                slippage_percent = float(os.getenv('MAX_SLIPPAGE_PERCENT', 3))
                slippage = slippage_percent / 100

                # Verifier le gas price avant d'executer
                current_gas_price = self.web3_manager.w3.eth.gas_price
                max_gas_price_gwei = float(os.getenv('MAX_GAS_PRICE_GWEI', 50))
                max_gas_price_wei = int(max_gas_price_gwei * 10**9)

                if current_gas_price > max_gas_price_wei:
                    self.logger.warning(
                        f"⛽ Gas price trop eleve: {current_gas_price/10**9:.1f} Gwei > "
                        f"{max_gas_price_gwei:.1f} Gwei - Achat annule"
                    )
                    return False

                self.logger.info(f"⛽ Gas price: {current_gas_price/10**9:.1f} Gwei")

                # CORRECTION: Calculer le nombre de tokens attendus pour position_size_wei ETH
                # On achete des tokens avec de l'ETH, donc on envoie token['address'] pour obtenir son prix
                # La fonction get_token_price retourne le prix en ETH pour 1 token
                # On doit calculer combien de tokens on recevra pour position_size_wei ETH

                # Methode correcte: utiliser le prix USD du token
                eth_price_usd = self.coingecko.get_eth_price()
                if eth_price_usd == 0:
                    eth_price_usd = 3000  # Fallback

                # Valeur de notre achat en USD
                buy_value_usd = position_size_eth * eth_price_usd

                # Nombre de tokens qu'on devrait recevoir
                token_price_usd = token['price_usd']
                if token_price_usd <= 0:
                    self.logger.error(f"Prix token invalide: ${token_price_usd}")
                    return False

                expected_tokens = buy_value_usd / token_price_usd

                # Appliquer slippage
                min_tokens_out = int(expected_tokens * (1 - slippage))

                self.logger.info(
                    f"💰 Achat {position_size_eth:.4f} ETH (${buy_value_usd:.2f}) "
                    f"-> ~{expected_tokens:.0f} {token['symbol']} "
                    f"(min: {min_tokens_out:.0f} avec {slippage_percent}% slippage)"
                )

                # Preparer la transaction
                deadline = int(time.time()) + 300  # 5 minutes

                # Lire gas limit depuis .env
                gas_limit_buy = int(os.getenv('GAS_LIMIT_BUY', 250000))

                params = {
                    'tokenIn': Web3.to_checksum_address(weth_address),
                    'tokenOut': Web3.to_checksum_address(token['address']),
                    'fee': 3000,  # 0.3%
                    'recipient': self.web3_manager.account.address,
                    'deadline': deadline,
                    'amountIn': position_size_wei,
                    'amountOutMinimum': min_tokens_out,
                    'sqrtPriceLimitX96': 0
                }

                # Construire la transaction
                swap_txn = self.router.functions.exactInputSingle(params).build_transaction({
                    'from': self.web3_manager.account.address,
                    'value': position_size_wei,
                    'gas': gas_limit_buy,
                    'gasPrice': current_gas_price,
                    'nonce': self.web3_manager.w3.eth.get_transaction_count(
                        self.web3_manager.account.address
                    )
                })
                
                # Signer et envoyer
                signed_txn = self.web3_manager.account.sign_transaction(swap_txn)
                tx_hash = self.web3_manager.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
                
                self.logger.info(f"Transaction envoyee: {tx_hash.hex()}")
                
                # Attendre confirmation
                receipt = self.web3_manager.w3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt['status'] == 1:
                    self.logger.info(f"✅ Achat reussi: {token['symbol']}")

                    # Creer la position avec le prix FRAIS
                    position = Position(
                        token['address'],
                        token['symbol'],
                        entry_price,  # Prix frais de la re-validation
                        expected_amount,
                        position_size_eth
                    )
                    position.trailing_config = self.trailing_config

                    # Log du grace period activé
                    self.logger.info(
                        f"🛡️ Grace period activé pour {token['symbol']}: "
                        f"3 minutes avec stop loss à -35% (puis -5%)"
                    )

                    self.positions[token['address']] = position
                    self.save_position_state(position)
                    
                    # Enregistrer avec le prix frais
                    self.save_trade_to_db(
                        token, 'BUY', entry_price,
                        position_size_eth, 'real', tx_hash.hex()
                    )
                    
                    return True
                else:
                    self.logger.error("Transaction echouee")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Erreur execution achat: {e}")
            return False
            
    def execute_sell(self, position: Position, reason: str) -> bool:
        """Execute une vente complete avec approval et swap"""
        if position.entry_price == 0:
            self.logger.error(f"Prix d'entree invalide pour {position.symbol}")
            return False
            
        try:
            # Calculer le profit avant la vente
            profit_percent = ((position.current_price - position.entry_price) / 
                            position.entry_price) * 100
            
            # Mettre a jour les metriques
            self.performance_metrics['total_trades'] += 1
            if profit_percent > 0:
                self.performance_metrics['winning_trades'] += 1
            else:
                self.performance_metrics['losing_trades'] += 1
            
            self.performance_metrics['total_profit_percent'] += profit_percent
            
            if profit_percent > self.performance_metrics['best_trade']:
                self.performance_metrics['best_trade'] = profit_percent
            if profit_percent < self.performance_metrics['worst_trade']:
                self.performance_metrics['worst_trade'] = profit_percent
            
            # Compter le type de sortie
            if "Trailing" in reason:
                self.performance_metrics['trailing_exits'] += 1
            elif "Stop Loss" in reason:
                self.performance_metrics['stoploss_exits'] += 1
            
            if self.trading_mode == 'paper':
                # Mode simulation
                self.logger.info(
                    f"[PAPER] Vente: {position.symbol} | "
                    f"Profit: {profit_percent:.2f}% | "
                    f"Raison: {reason}"
                )
                
                self.save_sell_to_db(position, profit_percent, reason, 'paper')
                del self.positions[position.token_address]
                
                # Supprimer le fichier de sauvegarde
                state_file = PROJECT_DIR / 'data' / f'position_{position.token_address}.json'
                if state_file.exists():
                    state_file.unlink()

                return True
                
            else:
                # Mode reel - Vente complete
                self.logger.info(f"[REAL] Execution vente reelle: {position.symbol}")
                
                weth_address = "0x4200000000000000000000000000000000000006"
                router_address = self.uniswap.router
                
                # Verifier le gas price avant d'executer
                current_gas_price = self.web3_manager.w3.eth.gas_price
                max_gas_price_gwei = float(os.getenv('MAX_GAS_PRICE_GWEI', 50))
                max_gas_price_wei = int(max_gas_price_gwei * 10**9)

                if current_gas_price > max_gas_price_wei:
                    self.logger.warning(
                        f"⛽ Gas price trop eleve: {current_gas_price/10**9:.1f} Gwei > "
                        f"{max_gas_price_gwei:.1f} Gwei - Vente reportee"
                    )
                    # Ne pas vendre si gas trop cher, sauf si c'est une urgence (stop loss)
                    if "Stop Loss" not in reason:
                        return False

                self.logger.info(f"⛽ Gas price: {current_gas_price/10**9:.1f} Gwei")

                # 1. APPROVE TOKEN POUR LE ROUTER
                self.logger.info("etape 1: Approval du token pour le router")

                approve_abi = json.loads('''[
                    {
                        "inputs": [
                            {"name": "_spender", "type": "address"},
                            {"name": "_value", "type": "uint256"}
                        ],
                        "name": "approve",
                        "outputs": [{"name": "", "type": "bool"}],
                        "type": "function"
                    }
                ]''')

                token_contract = self.web3_manager.w3.eth.contract(
                    address=Web3.to_checksum_address(position.token_address),
                    abi=approve_abi
                )

                amount_to_sell = int(position.amount)

                approve_txn = token_contract.functions.approve(
                    Web3.to_checksum_address(router_address),
                    amount_to_sell
                ).build_transaction({
                    'from': self.web3_manager.account.address,
                    'gas': 100000,
                    'gasPrice': current_gas_price,
                    'nonce': self.web3_manager.w3.eth.get_transaction_count(
                        self.web3_manager.account.address
                    )
                })
                
                signed_approve = self.web3_manager.account.sign_transaction(approve_txn)
                approve_hash = self.web3_manager.w3.eth.send_raw_transaction(
                    signed_approve.rawTransaction
                )
                
                self.logger.info(f"Approval envoyee: {approve_hash.hex()}")
                
                approve_receipt = self.web3_manager.w3.eth.wait_for_transaction_receipt(
                    approve_hash, timeout=120
                )
                
                if approve_receipt['status'] != 1:
                    self.logger.error("echec de l'approval")
                    return False
                    
                self.logger.info("✅ Token approuve pour la vente")
                
                # 2. EXeCUTER LE SWAP TOKEN -> WETH
                self.logger.info("etape 2: Swap token vers WETH")

                # Lire slippage depuis .env
                slippage_percent = float(os.getenv('MAX_SLIPPAGE_PERCENT', 3))
                slippage = slippage_percent / 100

                # Calculer le minimum acceptable
                eth_price = self.coingecko.get_eth_price()
                if eth_price == 0:
                    eth_price = 3000  # Valeur par defaut si erreur API

                expected_weth = (position.current_price * position.amount) / eth_price
                min_weth_out = int(expected_weth * (1 - slippage) * 10**18)

                self.logger.info(
                    f"💰 Vente ~{position.amount:.0f} {position.symbol} "
                    f"-> ~{expected_weth:.4f} ETH "
                    f"(min: {min_weth_out/10**18:.4f} avec {slippage_percent}% slippage)"
                )

                deadline = int(time.time()) + 300  # 5 minutes

                # Lire gas limit depuis .env
                gas_limit_sell = int(os.getenv('GAS_LIMIT_SELL', 300000))

                swap_params = {
                    'tokenIn': Web3.to_checksum_address(position.token_address),
                    'tokenOut': Web3.to_checksum_address(weth_address),
                    'fee': 3000,
                    'recipient': self.web3_manager.account.address,
                    'deadline': deadline,
                    'amountIn': amount_to_sell,
                    'amountOutMinimum': min_weth_out,
                    'sqrtPriceLimitX96': 0
                }

                swap_txn = self.router.functions.exactInputSingle(
                    swap_params
                ).build_transaction({
                    'from': self.web3_manager.account.address,
                    'gas': gas_limit_sell,
                    'gasPrice': current_gas_price,
                    'nonce': self.web3_manager.w3.eth.get_transaction_count(
                        self.web3_manager.account.address
                    )
                })
                
                signed_swap = self.web3_manager.account.sign_transaction(swap_txn)
                swap_hash = self.web3_manager.w3.eth.send_raw_transaction(
                    signed_swap.rawTransaction
                )
                
                self.logger.info(f"Swap envoye: {swap_hash.hex()}")
                
                swap_receipt = self.web3_manager.w3.eth.wait_for_transaction_receipt(
                    swap_hash, timeout=120
                )
                
                if swap_receipt['status'] == 1:
                    self.logger.info(
                        f"✅ Vente reussie: {position.symbol} | "
                        f"Profit: {profit_percent:.2f}% | "
                        f"TX: {swap_hash.hex()}"
                    )
                    
                    self.save_sell_to_db(position, profit_percent, reason, 'real', swap_hash.hex())
                    
                    del self.positions[position.token_address]
                    
                    # Supprimer le fichier de sauvegarde
                    state_file = PROJECT_DIR / 'data' / f'position_{position.token_address}.json'
                    if state_file.exists():
                        state_file.unlink()
                        
                    return True
                else:
                    self.logger.error(f"echec du swap: {swap_receipt}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Erreur vente: {e}")
            if 'position' in locals():
                self.save_position_state(position)
            return False
                       
    def update_positions(self):
        """Met a jour toutes les positions avec checks complets et retry"""
        for address, position in list(self.positions.items()):
            try:
                # Recuperer le prix actuel avec retry
                dex_data = None
                max_retries = 3
                
                for attempt in range(max_retries):
                    try:
                        dex_data = self.dexscreener.get_token_info(address)
                        if dex_data:
                            break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            self.logger.error(f"Impossible de recuperer le prix apres {max_retries} tentatives: {e}")
                        else:
                            self.logger.warning(f"Tentative {attempt + 1}/{max_retries} echouee, retry dans 2s")
                            time.sleep(2)
                
                if dex_data:
                    new_price = dex_data.get('price_usd', position.current_price)

                    # Validation du prix: ne peut pas varier de plus de 1000x par rapport au prix d'entrée
                    if new_price > 0 and position.entry_price > 0:
                        price_change_ratio = new_price / position.entry_price
                        if price_change_ratio > 1000 or price_change_ratio < 0.001:
                            self.logger.warning(
                                f"⚠️ Prix aberrant pour {position.symbol}: "
                                f"Entry=${position.entry_price:.8f}, New=${new_price:.8f} "
                                f"(ratio: {price_change_ratio:.1f}x) - Prix ignoré"
                            )
                            # Garder le dernier prix connu
                        else:
                            position.current_price = new_price
                    else:
                        position.current_price = new_price

                    # Protection contre division par zero
                    if position.entry_price == 0:
                        self.logger.error(f"Prix d'entree invalide pour {position.symbol}")
                        continue
                        
                    # Calculer le profit actuel
                    profit_percent = ((position.current_price - position.entry_price) /
                                    position.entry_price) * 100

                    # 1. Verifier TIME EXIT
                    should_exit, exit_reason = self.check_time_exit(position)
                    if should_exit:
                        self.logger.info(f"⏱️ Time exit: {exit_reason}")
                        self.execute_sell(position, exit_reason)
                        continue

                    # 2. Verifier STOP LOSS avec GRACE PERIOD
                    active_stop_loss = position.get_active_stop_loss_percent()

                    # Log si transition du grace period
                    if hasattr(position, 'grace_period_active') and position.grace_period_active:
                        time_in_position = (datetime.now() - position.entry_time).total_seconds() / 60
                        if time_in_position >= position.grace_period_minutes:
                            self.logger.info(
                                f"⏰ {position.symbol} - Grace period terminé "
                                f"(3 min écoulées) - Stop loss activé à -5%"
                            )
                            position.grace_period_active = False

                    if profit_percent <= -active_stop_loss:
                        in_grace = position.is_in_grace_period() if hasattr(position, 'is_in_grace_period') else False
                        grace_status = " (Grace Period)" if in_grace else ""
                        self.logger.info(
                            f"🛑 Stop Loss{grace_status}: {profit_percent:.1f}% "
                            f"(seuil: -{active_stop_loss:.0f}%)"
                        )
                        self.execute_sell(position, f"Stop Loss ({profit_percent:.1f}%){grace_status}")
                        continue
                    
                    # 3. Mettre a jour TRAILING STOP
                    self.update_trailing_stop(position)
                    
                    # 4. Verifier TRAILING STOP
                    if position.trailing_active and position.current_price <= position.stop_loss:
                        self.logger.info(
                            f"📉 Trailing Stop: {position.symbol} | "
                            f"Niveau {position.current_level} | "
                            f"Profit final: {profit_percent:.1f}%"
                        )
                        self.execute_sell(position, f"Trailing Stop L{position.current_level}")
                else:
                    self.logger.warning(f"Pas de donnees de prix pour {position.symbol}, utilisation du dernier prix connu")
                        
            except Exception as e:
                self.logger.error(f"Erreur update position {address}: {e}")
                # Sauvegarder l'etat en cas d'erreur
                self.save_position_state(position)

    def save_trade_to_db(self, token: Dict, action: str, price: float,
                         amount_eth: float, mode: str, tx_hash: str = ''):
        """Sauvegarde un trade dans la DB"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Inserer dans trade_log avec le schema correct
            cursor.execute('''
                INSERT INTO trade_log
                (timestamp, level, message, token_address, tx_hash)
                VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?)
            ''', ('INFO', f'{action} {token["symbol"]} @ ${price:.8f}', token['address'], tx_hash))

            if action == 'BUY':
                # Inserer dans trade_history avec entry_time
                cursor.execute('''
                    INSERT INTO trade_history
                    (token_address, symbol, side, amount_in, price, entry_time, timestamp)
                    VALUES (?, ?, 'BUY', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (token['address'], token['symbol'], amount_eth, price))

            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde trade DB: {e}")
            if 'conn' in locals():
                conn.close()
       
    def save_sell_to_db(self, position: Position, profit: float, reason: str, mode: str, tx_hash: str = ''):
        """Sauvegarde une vente dans la DB en mettant a jour la ligne existante"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculer la valeur de sortie en ETH
            # amount_out = amount_in * (1 + profit/100)
            amount_out_eth = position.amount_eth * (1 + profit / 100)

            # MISE A JOUR de la ligne existante (BUY) avec les donnees de sortie
            cursor.execute('''
                UPDATE trade_history
                SET amount_out = ?,
                    exit_time = CURRENT_TIMESTAMP,
                    profit_loss = ?
                WHERE token_address = ?
                AND exit_time IS NULL
            ''', (amount_out_eth, profit, position.token_address))

            if cursor.rowcount == 0:
                self.logger.warning(f"Aucune position ouverte trouvee pour {position.symbol} dans trade_history")

            # Log la transaction
            cursor.execute('''
                INSERT INTO trade_log
                (timestamp, level, message, token_address, tx_hash)
                VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?)
            ''', ('INFO', f'SELL {position.symbol} - Profit: {profit:.2f}% - {reason}',
                  position.token_address, tx_hash))

            # Inserer dans trailing_level_stats si c'etait un trailing stop
            if position.trailing_active:
                cursor.execute('''
                    INSERT INTO trailing_level_stats
                    (token_address, level, activation_price, stop_loss_price, timestamp)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (position.token_address, position.current_level,
                      position.highest_price, position.stop_loss))

            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde vente DB: {e}")
            if 'conn' in locals():
                conn.close()
   
    def log_performance_metrics(self):
        """Affiche les metriques de performance"""
        if self.performance_metrics['total_trades'] > 0:
            win_rate = (self.performance_metrics['winning_trades'] / 
                       self.performance_metrics['total_trades'] * 100)
            avg_profit = (self.performance_metrics['total_profit_percent'] / 
                         self.performance_metrics['total_trades'])
        else:
            win_rate = 0
            avg_profit = 0
           
        self.logger.info(
            f"📊 PERFORMANCE - "
            f"Trades: {self.performance_metrics['total_trades']} | "
            f"Win Rate: {win_rate:.1f}% | "
            f"Avg: {avg_profit:.1f}% | "
            f"Best: +{self.performance_metrics['best_trade']:.1f}% | "
            f"Worst: {self.performance_metrics['worst_trade']:.1f}% | "
            f"Time Exits: {self.performance_metrics['time_exits']} | "
            f"Trailing: {self.performance_metrics['trailing_exits']} | "
            f"Stop Loss: {self.performance_metrics['stoploss_exits']}"
        )
    
    def cleanup(self):
        """Nettoie les ressources"""
        if hasattr(self, 'dexscreener'):
            self.dexscreener.close()
        if hasattr(self, 'coingecko'):
            self.coingecko.close()
        if hasattr(self, 'honeypot_checker'):
            self.honeypot_checker.close()
       
    def run(self):
        """Boucle principale avec monitoring 1 seconde"""
        self.logger.info(f"🚀 Trader - Strategie unique activee")
        self.logger.info(
            f"⚙️ Config: {self.position_size_percent}% positions | "
            f"Max {self.max_positions} positions | "
            f"{self.max_trades_per_day} trades/jour | "
            f"Stop Loss: -{self.stop_loss_percent}% | "
            f"Trailing: {self.trailing_config['activation_threshold']}%+"
        )
        self.logger.info(
            f"⏱️ Time Exit: {self.time_exit_config['stagnation']['hours']}h/+{self.time_exit_config['stagnation']['min_profit']}% | "
            f"{self.time_exit_config['low_momentum']['hours']}h/+{self.time_exit_config['low_momentum']['min_profit']}% | "
            f"{self.time_exit_config['maximum']['hours']}h force | "
            f"{self.time_exit_config['emergency']['hours']}h emergency"
        )
        
        # Compteurs pour logs periodiques
        last_performance_log = time.time()
        monitoring_counter = 0
        
        try:
            while True:
                try:
                    # Verifier le mode de trading
                    mode_file = PROJECT_DIR / 'config' / 'trading_mode.json'
                    if mode_file.exists():
                        try:
                            with open(mode_file, 'r') as f:
                                data = json.load(f)
                                new_mode = data.get('mode', 'paper')
                                if new_mode != self.trading_mode:
                                    self.logger.info(f"🔄 Mode change: {self.trading_mode} → {new_mode}")
                                    self.trading_mode = new_mode
                        except Exception as e:
                            self.logger.error(f"Erreur lecture mode: {e}")
                            
                    # Mettre a jour les positions existantes
                    if self.positions:
                        self.update_positions()
                        
                        # Log rapide toutes les 10 secondes
                        monitoring_counter += 1
                        if monitoring_counter >= 10:
                            for addr, pos in self.positions.items():
                                if pos.entry_price > 0:
                                    profit = ((pos.current_price - pos.entry_price) /
                                            pos.entry_price) * 100
                                    hours = (datetime.now() - pos.entry_time).total_seconds() / 3600
                                    minutes = hours * 60

                                    # Déterminer le statut avec grace period
                                    if hasattr(pos, 'is_in_grace_period') and pos.is_in_grace_period():
                                        time_left = pos.grace_period_minutes - minutes
                                        status = f"🛡️ Grace ({time_left:.1f}min)"
                                        stop_info = f"SL: -35%"
                                    elif pos.trailing_active:
                                        status = "📈 Trailing"
                                        stop_info = f"Stop: ${pos.stop_loss:.8f}"
                                    else:
                                        status = "⏳ Attente"
                                        stop_info = f"SL: -5%"

                                    self.logger.info(
                                        f"{status} {pos.symbol}: "
                                        f"{profit:+.1f}% | "
                                        f"{hours:.1f}h | "
                                        f"{stop_info}"
                                    )
                            monitoring_counter = 0
                    
                    # Verifier limite quotidienne
                    today = datetime.now().date()
                    if self.last_trade_day != today:
                        self.daily_trades = 0
                        self.last_trade_day = today
                        self.logger.info(f"📅 Nouveau jour - Trades disponibles: {self.max_trades_per_day}")
                        
                    # Chercher nouvelle opportunite
                    if (len(self.positions) < self.max_positions and 
                        self.daily_trades < self.max_trades_per_day):
                        
                        token = self.get_next_token()
                        if token:
                            # Validation supplementaire
                            if token.get('price_usd', 0) <= 0:
                                self.logger.warning(f"Token {token.get('symbol')} avec prix invalide, ignore")
                                continue

                            # Calculer l'âge du token
                            if token.get('created_at'):
                                created_dt = datetime.fromisoformat(token['created_at'].replace('Z', '+00:00'))
                                token_age_hours = (datetime.now(created_dt.tzinfo) - created_dt).total_seconds() / 3600
                                age_str = f"{token_age_hours:.1f}h"
                            else:
                                age_str = "N/A"

                            self.logger.info(
                                f"📊 Opportunite detectee: {token['symbol']} | "
                                f"Liq: ${token['liquidity']:,.0f} | "
                                f"Vol: ${token['volume_24h']:,.0f} | "
                                f"Score: {token['score']} | Age: {age_str}"
                            )
                            
                            # Verification finale avant achat
                            if len(self.positions) < self.max_positions:
                                if self.execute_buy(token):
                                    self.daily_trades += 1
                                    self.logger.info(
                                        f"📈 Position {len(self.positions)}/{self.max_positions} | "
                                        f"Trades aujourd'hui: {self.daily_trades}/{self.max_trades_per_day}"
                                    )
                            else:
                                self.logger.warning("Positions maximum atteintes")
                                
                    # Log performance toutes les heures
                    if time.time() - last_performance_log > 3600:
                        self.log_performance_metrics()
                        self.cleanup_expired_cooldowns()  # Nettoyer cooldowns expirés
                        last_performance_log = time.time()

                    # Pause de 1 seconde (monitoring rapide)
                    time.sleep(self.monitoring_interval)
                    
                except KeyboardInterrupt:
                    self.logger.info("🛑 Arrêt demande par l'utilisateur")
                    self.log_performance_metrics()
                    
                    # Sauvegarder l'etat final
                    for position in self.positions.values():
                        self.save_position_state(position)
                        
                    break
                    
                except Exception as e:
                    self.logger.error(f"Erreur boucle principale: {e}")
                    # En cas d'erreur critique, sauvegarder les positions
                    for position in self.positions.values():
                        try:
                            self.save_position_state(position)
                        except:
                            pass
                    time.sleep(10)
        finally:
            self.cleanup()

if __name__ == "__main__":
    trader = RealTrader()
    try:
        trader.run()
    except Exception as e:
        trader.logger.error(f"Erreur fatale: {e}")
        # Sauvegarder les positions en cas de crash
        for position in trader.positions.values():
            try:
                trader.save_position_state(position)
            except:
                pass
        trader.cleanup()
