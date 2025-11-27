#!/usr/bin/env python3
"""
Filter - Analyse complète avec nouvelle stratégie de trading
"""

import sqlite3
import time
import os
import sys
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Set, List
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.append(str(PROJECT_DIR))

from dotenv import load_dotenv
from web3_utils import (
    BaseWeb3Manager, UniswapV3Manager,
    DexScreenerAPI, BaseScanAPI, CoinGeckoAPI
)

load_dotenv(PROJECT_DIR / 'config' / '.env')

class AdvancedFilter:
    def __init__(self):
        # Créer les dossiers nécessaires
        (PROJECT_DIR / 'data').mkdir(parents=True, exist_ok=True)
        (PROJECT_DIR / 'logs').mkdir(parents=True, exist_ok=True)
        (PROJECT_DIR / 'config').mkdir(parents=True, exist_ok=True)
        self.db_path = PROJECT_DIR / 'data' / 'trading.db'

        # Setup logging
        self.setup_logging()

        # Initialiser la base de données si nécessaire
        self.init_database()

        # Charger la configuration
        self.load_config()

        # Initialiser les clients API
        self.web3_manager = BaseWeb3Manager(
            rpc_url=os.getenv('RPC_URL', 'https://mainnet.base.org'),
            private_key=os.getenv('PRIVATE_KEY')
        )
        self.uniswap = UniswapV3Manager(self.web3_manager)
        self.dexscreener = DexScreenerAPI()
        self.basescan = BaseScanAPI(os.getenv('ETHERSCAN_API_KEY')) # Utilise la clé Etherscan
        self.coingecko = CoinGeckoAPI(os.getenv('COINGECKO_API_KEY'))

        # Système de blacklist
        self.blacklist_file = PROJECT_DIR / 'config' / 'blacklist.json'
        self.load_blacklist()

        # Statistiques de filtrage
        self.stats = {
            'total_analyzed': 0,
            'total_approved': 0,
            'total_rejected': 0
        }

    def setup_logging(self):
        """Configuration du logging"""
        log_file = PROJECT_DIR / 'logs' / 'filter.log'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def init_database(self):
        """Initialise la base de données si nécessaire"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Table des tokens découverts (partagée avec Scanner)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discovered_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT UNIQUE NOT NULL,
                symbol TEXT,
                name TEXT,
                decimals INTEGER,
                total_supply TEXT,
                liquidity REAL,
                market_cap REAL,
                price_usd REAL,
                price_eth REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table des tokens approuvés
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS approved_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT UNIQUE NOT NULL,
                symbol TEXT,
                name TEXT,
                reason TEXT, -- Raison de l'approbation
                score REAL,  -- Score de qualité (0-100)
                analysis_data TEXT, -- JSON avec les détails de l'analyse
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table des tokens rejetés
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rejected_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT UNIQUE NOT NULL,
                symbol TEXT,
                name TEXT,
                reason TEXT, -- Raison du rejet
                analysis_data TEXT, -- JSON avec les détails de l'analyse
                rejected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table des règles de filtrage (optionnel, pour suivi)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS filter_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT UNIQUE NOT NULL,
                rule_config TEXT, -- JSON avec la configuration de la règle
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def load_config(self):
        """Charge la configuration avec nouvelle stratégie"""
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
            self.logger.error(f"Erreur chargement mode trading: {e}")
            self.trading_mode = 'paper' # Valeur par défaut

        # Règles de filtrage
        try:
            # Utiliser les variables standardisées du .env
            self.min_market_cap = float(os.getenv('MIN_MARKET_CAP', '25000'))
            self.max_market_cap = float(os.getenv('MAX_MARKET_CAP', '10000000'))
            self.min_liquidity = float(os.getenv('MIN_LIQUIDITY_USD', '30000'))
            self.max_liquidity = float(os.getenv('MAX_LIQUIDITY_USD', '10000000'))
            self.min_volume_24h = float(os.getenv('MIN_VOLUME_24H', '50000'))
            self.min_age_hours = float(os.getenv('MIN_AGE_HOURS', '2'))
            self.min_holders = int(os.getenv('MIN_HOLDERS', '150'))
            self.max_owner_percentage = float(os.getenv('MAX_OWNER_PERCENTAGE', '10.0'))
            self.max_buy_tax = float(os.getenv('MAX_BUY_TAX', '5.0'))
            self.max_sell_tax = float(os.getenv('MAX_SELL_TAX', '5.0'))
            self.min_safety_score = float(os.getenv('MIN_SAFETY_SCORE', '70.0'))
            self.min_potential_score = float(os.getenv('MIN_POTENTIAL_SCORE', '60.0'))
            self.score_threshold = float(os.getenv('MIN_SAFETY_SCORE', '70.0'))  # Utilise MIN_SAFETY_SCORE comme seuil
        except ValueError as e:
            self.logger.error(f"Erreur parsing config filtre: {e}. Utilisation des valeurs par défaut.")
            # Définir des valeurs par défaut si le parsing échoue
            self.min_market_cap = 25000
            self.max_market_cap = 10000000
            self.min_liquidity = 30000
            self.max_liquidity = 10000000
            self.min_volume_24h = 50000
            self.min_age_hours = 2
            self.min_holders = 150
            self.max_owner_percentage = 10.0
            self.max_buy_tax = 5.0
            self.max_sell_tax = 5.0
            self.min_safety_score = 70.0
            self.min_potential_score = 60.0
            self.score_threshold = 70.0


    def load_blacklist(self):
        """Charge la liste noire depuis le fichier JSON"""
        try:
            if self.blacklist_file.exists():
                with open(self.blacklist_file, 'r') as f:
                    self.blacklist = set(json.load(f))
            else:
                self.blacklist = set()
                # Créer un fichier vide si nécessaire
                with open(self.blacklist_file, 'w') as f:
                    json.dump([], f)
        except Exception as e:
            self.logger.error(f"Erreur chargement blacklist: {e}")
            self.blacklist = set()

    def is_blacklisted(self, token_address: str) -> bool:
        """Vérifie si un token est sur la liste noire"""
        return token_address.lower() in [addr.lower() for addr in self.blacklist]

    def calculate_score(self, token_data: Dict) -> Tuple[float, List[str]]:
        """
        Calcule un score de qualité basé sur les critères de filtrage.
        Retourne (score, liste_raisons_positive)
        """
        score = 0.0
        reasons = []

        # Vérifier la blacklist
        if self.is_blacklisted(token_data['token_address']):
            return 0.0, ["Blacklisted"]

        # --- Critères d'analyse ---
        # Market Cap
        mc = token_data.get('market_cap', 0)
        if self.min_market_cap <= mc <= self.max_market_cap:
            score += 20
            reasons.append(f"MC (${mc:,.2f}) OK")
        elif mc < self.min_market_cap:
            reasons.append(f"MC (${mc:,.2f}) < min (${self.min_market_cap:,.2f})")
        else:
            reasons.append(f"MC (${mc:,.2f}) > max (${self.max_market_cap:,.2f})")

        # Liquidity
        liquidity = token_data.get('liquidity', 0)
        if liquidity >= self.min_liquidity:
            score += 15
            reasons.append(f"Liquidity (${liquidity:,.2f}) OK")
        else:
            reasons.append(f"Liquidity (${liquidity:,.2f}) < min (${self.min_liquidity:,.2f})")

        # Age (si disponible) - Doit avoir AU MOINS min_age_hours
        created_at = token_data.get('created_at')
        if created_at:
            try:
                from datetime import timezone
                # Parser le format "2025-11-09 11:51:36"
                if 'T' in created_at:
                    # Format ISO avec T
                    token_creation_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    # Format "YYYY-MM-DD HH:MM:SS"
                    token_creation_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                    token_creation_date = token_creation_date.replace(tzinfo=timezone.utc)

                age_hours = (datetime.now(timezone.utc) - token_creation_date).total_seconds() / 3600

                if age_hours >= self.min_age_hours:
                    score += 10
                    reasons.append(f"Age ({age_hours:.1f}h) >= min ({self.min_age_hours}h)")
                else:
                    reasons.append(f"Age ({age_hours:.1f}h) < min ({self.min_age_hours}h)")
            except Exception as e:
                reasons.append(f"Age non vérifié (erreur: {str(e)[:50]})")

        # Holders (si disponible via BaseScan ou autre)
        # ⚠️ TEMPORAIREMENT DÉSACTIVÉ: L'API Base retourne toujours 0
        # TODO: Réactiver quand l'API Etherscan Base fonctionnera
        holders = token_data.get('holder_count', 0)
        if holders > 0:  # Seulement si on a une vraie valeur
            if holders >= self.min_holders:
                score += 10
                reasons.append(f"Holders ({holders}) OK")
            else:
                reasons.append(f"Holders ({holders}) < min ({self.min_holders})")
        else:
            # Ne pas pénaliser si API ne fonctionne pas
            score += 5  # Bonus partiel par défaut
            reasons.append(f"Holders non disponible (API Base)")

        # Owner percentage (si disponible via BaseScan)
        # ⚠️ TEMPORAIREMENT DÉSACTIVÉ: L'API Base retourne toujours 100%
        # TODO: Réactiver quand l'API Etherscan Base fonctionnera
        owner_pct = token_data.get('owner_percentage', 100.0)
        if owner_pct < 100.0:  # Seulement si on a une vraie valeur
            if owner_pct <= self.max_owner_percentage:
                score += 15
                reasons.append(f"Owner % ({owner_pct:.2f}%) OK")
            else:
                reasons.append(f"Owner % ({owner_pct:.2f}%) > max ({self.max_owner_percentage:.2f}%)")
        else:
            # Ne pas pénaliser si API ne fonctionne pas
            score += 7  # Bonus partiel par défaut
            reasons.append(f"Owner % non disponible (API Base)")

        # Taxes (si disponibles via BaseScan ou analyse du contrat)
        buy_tax = token_data.get('buy_tax', 0.0) # Cette donnée doit être récupérée ailleurs
        sell_tax = token_data.get('sell_tax', 0.0) # Cette donnée doit être récupérée ailleurs
        if buy_tax <= self.max_buy_tax and sell_tax <= self.max_sell_tax:
            score += 15
            reasons.append(f"Taxes (B:{buy_tax:.2f}%, S:{sell_tax:.2f}%) OK")
        else:
            reasons.append(f"Taxes (B:{buy_tax:.2f}%, S:{sell_tax:.2f}%) > max (B:{self.max_buy_tax:.2f}%, S:{self.max_sell_tax:.2f}%)")

        # Données on-chain (détails du contrat, honeypot, etc.) - via web3_utils
        try:
            token_address = token_data['token_address']
            honeypot_check = self.web3_manager.check_honeypot(token_address)
            if not honeypot_check.get('is_honeypot', True): # Si ce n'est PAS un honeypot
                score += 15
                reasons.append("Passed honeypot check")
            else:
                reasons.append("Failed honeypot check")
        except Exception as e:
            self.logger.warning(f"Erreur check honeypot pour {token_data['token_address']}: {e}")
            reasons.append("Honeypot check failed")

        # Limiter le score à 100
        score = min(score, 100.0)

        return score, reasons

    def approve_token(self, token_data: Dict, score: float, reasons: List[str]):
        """Enregistre un token comme approuvé"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        analysis_json = json.dumps({
            'score': score,
            'reasons': reasons,
            'details': token_data # Inclure les détails bruts pour référence
        })

        cursor.execute('''
            INSERT OR REPLACE INTO approved_tokens
            (token_address, symbol, name, reason, score, analysis_data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            token_data['token_address'],
            token_data['symbol'],
            token_data['name'],
            f"Score: {score:.2f} - {', '.join(reasons)}",
            score,
            analysis_json
        ))

        conn.commit()
        conn.close()
        self.stats['total_approved'] += 1
        self.logger.info(f"✅ Token APPROUVE: {token_data['symbol']} ({token_data['token_address']}) - Score: {score:.2f}")

    def reject_token(self, token_data: Dict, reasons: List[str]):
        """Enregistre un token comme rejeté"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        analysis_json = json.dumps({
            'reasons': reasons,
            'details': token_data
        })

        cursor.execute('''
            INSERT OR REPLACE INTO rejected_tokens
            (token_address, symbol, name, reason, analysis_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            token_data['token_address'],
            token_data['symbol'],
            token_data['name'],
            ', '.join(reasons),
            analysis_json
        ))

        conn.commit()
        conn.close()
        self.stats['total_rejected'] += 1
        self.logger.info(f"❌ Token REJETE: {token_data['symbol']} ({token_data['token_address']}) - Raisons: {', '.join(reasons)}")

    def run_filter_cycle(self):
        """Exécute un cycle de filtrage : récupère les tokens découverts, les analyse, les approuve/rejette"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Récupérer les tokens découverts non encore filtrés (ni approuvés ni rejetés)
            cursor.execute('''
                SELECT * FROM discovered_tokens
                WHERE token_address NOT IN (SELECT token_address FROM approved_tokens)
                AND token_address NOT IN (SELECT token_address FROM rejected_tokens)
            ''')
            new_tokens = cursor.fetchall()

            if not new_tokens:
                self.logger.info("Aucun nouveau token à filtrer pour le moment")
                conn.close()
                return

            # Récupérer les noms des colonnes pour reconstruire les dictionnaires
            col_names = [description[0] for description in cursor.description]

            self.logger.info(f"{len(new_tokens)} nouveau(x) token(s) à analyser")

            for row in new_tokens:
                token_dict = dict(zip(col_names, row))
                self.stats['total_analyzed'] += 1

                self.logger.info(f"Analyse du token: {token_dict.get('symbol', 'N/A')} ({token_dict['token_address']})")

                # Calculer le score
                score, reasons = self.calculate_score(token_dict)

                if score >= self.score_threshold:
                    self.approve_token(token_dict, score, reasons)
                else:
                    self.reject_token(token_dict, reasons)

        except Exception as e:
            self.logger.error(f"Erreur lors du cycle de filtrage: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        finally:
            conn.close()

    def run(self):
        """Boucle principale du filtre"""
        self.logger.info("Filter démarré...")
        self.logger.info(f"Mode: {self.trading_mode}")
        self.logger.info(f"Seuil de score: {self.score_threshold}")

        while True:
            try:
                self.logger.info("Démarrage d'un cycle de filtrage...")
                self.run_filter_cycle()
                self.logger.info(f"Cycle terminé. Stats: Analyzed={self.stats['total_analyzed']}, Approved={self.stats['total_approved']}, Rejected={self.stats['total_rejected']}")

                # Attendre avant le prochain cycle (ex: 5 minutes)
                time.sleep(300)

            except KeyboardInterrupt:
                self.logger.info("Filter arrêté par l'utilisateur.")
                break
            except Exception as e:
                self.logger.error(f"Erreur dans la boucle principale du filter: {e}")
                time.sleep(10)  # Attendre avant de réessayer

if __name__ == "__main__":
    filter_bot = AdvancedFilter()
    try:
        filter_bot.run()
    except KeyboardInterrupt:
        print("\nFilter arrêté.")
    except Exception as e:
        print(f"Erreur fatale: {e}")

