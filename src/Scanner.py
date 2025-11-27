#!/usr/bin/env python3
"""
Scanner - Avec récupération complète des données on-chain
"""

import asyncio
import sqlite3
import time
import os
import sys
import logging
import subprocess
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

# Setup paths
PROJECT_DIR = Path(__file__).parent.parent
sys.path.append(str(PROJECT_DIR / 'src'))

from web3 import Web3
from dotenv import load_dotenv
from web3_utils import BaseWeb3Manager, UniswapV3Manager, DexScreenerAPI, GeckoTerminalAPI

load_dotenv(PROJECT_DIR / 'config' / '.env')

class EnhancedScanner:
    def __init__(self):
        # Créer les dossiers nécessaires
        (PROJECT_DIR / 'data').mkdir(parents=True, exist_ok=True)
        (PROJECT_DIR / 'logs').mkdir(parents=True, exist_ok=True)
        (PROJECT_DIR / 'config').mkdir(parents=True, exist_ok=True)
        self.db_path = PROJECT_DIR / 'data' / 'trading.db'

        # Setup logging en premier
        self.setup_logging()

        # Initialiser la base de données si nécessaire
        self.init_database()

        # Web3 setup avec gestion d'erreur
        try:
            self.web3_manager = BaseWeb3Manager(
                rpc_url=os.getenv('RPC_URL', 'https://mainnet.base.org'),
                private_key=os.getenv('PRIVATE_KEY')
            )
            self.uniswap = UniswapV3Manager(self.web3_manager)
            self.dexscreener = DexScreenerAPI()
            self.geckoterminal = GeckoTerminalAPI()  # Nouveau: API pour nouveaux pools
        except Exception as e:
            self.logger.error(f"Erreur initialisation Web3/API: {e}")
            raise

        self.batch_size = 50  # Tokens à scanner par batch
        self.scan_delay = int(os.getenv('SCAN_INTERVAL_SECONDS', 30))  # Délai entre les scans (secondes)

    def setup_logging(self):
        """Configuration du logging"""
        log_file = PROJECT_DIR / 'logs' / 'scanner.log'
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

        # Table des tokens découverts
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

        # Table de l'état du scanner (dernier bloc scanné)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scanner_state (
                id INTEGER PRIMARY KEY,
                last_block INTEGER NOT NULL
            )
        ''')

        # Initialiser avec bloc 0 si vide
        cursor.execute("INSERT OR IGNORE INTO scanner_state (id, last_block) VALUES (1, 0)")

        conn.commit()
        conn.close()

    def get_last_scanned_block(self) -> int:
        """Récupère le dernier bloc scanné depuis la DB"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        result = cursor.execute("SELECT last_block FROM scanner_state WHERE id = 1").fetchone()
        conn.close()
        return result[0] if result else 0

    def update_last_scanned_block(self, block_number: int):
        """Met à jour le dernier bloc scanné dans la DB"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE scanner_state SET last_block = ? WHERE id = 1", (block_number,))
        conn.commit()
        conn.close()

    async def fetch_new_tokens(self) -> List[Dict]:
        """
        Récupère les nouveaux tokens depuis GeckoTerminal (priorité) puis DexScreener.
        GeckoTerminal est optimisé pour découvrir les nouveaux pools.
        """
        try:
            # PRIORITÉ 1: GeckoTerminal pour les nouveaux pools (mis à jour toutes les 60s)
            self.logger.info("Récupération des nouveaux pools depuis GeckoTerminal...")
            new_pools = self.geckoterminal.get_new_pools(network='base', page=1)

            if new_pools and len(new_pools) > 0:
                self.logger.info(f"{len(new_pools)} nouveaux pools trouvés sur GeckoTerminal")
                return new_pools

            # PRIORITÉ 2: DexScreener en fallback si GeckoTerminal ne retourne rien
            self.logger.info("Fallback vers DexScreener...")
            new_pairs = self.dexscreener.get_recent_pairs_on_chain('base', limit=50)

            if not new_pairs:
                self.logger.warning("Aucune nouvelle paire trouvée sur DexScreener")
                # Fallback: vérifier les tokens existants en DB
                return await self._fetch_tokens_from_db()

            self.logger.info(f"{len(new_pairs)} paires trouvées sur DexScreener")
            return new_pairs

        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des nouveaux tokens: {e}")
            # Fallback sur la DB en cas d'erreur
            return await self._fetch_tokens_from_db()

    async def _fetch_tokens_from_db(self) -> List[Dict]:
        """
        Fallback: récupère les tokens depuis la DB pour réanalyse
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT token_address, symbol, name, created_at FROM discovered_tokens
                ORDER BY created_at DESC
                LIMIT 10
            ''')
            rows = cursor.fetchall()
            col_names = [description[0] for description in cursor.description]
            recent_tokens = [dict(zip(col_names, row)) for row in rows]

            # Convertir au format attendu
            formatted_tokens = []
            for token_row in recent_tokens:
                token_info = self.dexscreener.get_token_info(token_row['token_address'])
                if token_info:
                    formatted_tokens.append({
                        'tokenAddress': token_row['token_address'],
                        'baseToken': {
                            'address': token_row['token_address'],
                            'symbol': token_row['symbol'],
                            'name': token_row['name']
                        },
                        'priceUsd': token_info.get('price_usd', 0),
                        'liquidity': {'usd': token_info.get('liquidity_usd', 0)},
                        'marketCap': token_info.get('market_cap', 0)
                    })

            return formatted_tokens

        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des tokens de la DB: {e}")
            return []
        finally:
            conn.close()


    async def process_token_batch(self, tokens: List[Dict]):
        """Traite un batch de tokens découverts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        skipped_existing = 0
        skipped_no_address = 0
        skipped_no_details = 0
        added = 0

        for token_data in tokens:
            try:
                # Extraire les données du token
                token_address = token_data.get('tokenAddress') or token_data.get('baseToken', {}).get('address')
                if not token_address:
                    skipped_no_address += 1
                    continue  # Passer si pas d'adresse

                # Vérifier si le token existe déjà
                cursor.execute("SELECT 1 FROM discovered_tokens WHERE token_address = ?", (token_address,))
                if cursor.fetchone():
                    skipped_existing += 1
                    continue  # Passer si déjà enregistré

                # Récupérer les détails on-chain via web3_utils
                token_details = self.web3_manager.get_token_info(token_address)
                if not token_details:
                    skipped_no_details += 1
                    continue

                # Récupérer les données de DexScreener
                pair_data = self.dexscreener.get_token_info(token_address) # Utilise la méthode existante

                # Extraire les infos pertinentes
                symbol = token_details.get('symbol', 'UNKNOWN')
                name = token_details.get('name', 'Unknown Token')
                decimals = token_details.get('decimals', 18)
                total_supply = str(token_details.get('total_supply', 0))
                price_usd = pair_data.get('price_usd') if pair_data else None
                price_eth = pair_data.get('price_native') if pair_data else None
                liquidity = pair_data.get('liquidity_usd', 0) if pair_data else 0
                market_cap = pair_data.get('market_cap', 0) if pair_data else 0
                volume_24h = pair_data.get('volume_24h', 0) if pair_data else 0

                # Insérer dans la base de données
                cursor.execute('''
                    INSERT OR IGNORE INTO discovered_tokens
                    (token_address, symbol, name, decimals, total_supply, liquidity, market_cap, volume_24h, price_usd, price_eth)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (token_address, symbol, name, decimals, total_supply, liquidity, market_cap, volume_24h, price_usd, price_eth))

                self.logger.info(f"✅ Token découvert: {symbol} ({token_address}) - MC: ${market_cap:.2f}")
                added += 1

            except Exception as e:
                self.logger.error(f"Erreur lors du traitement du token {token_data.get('tokenAddress', 'N/A')}: {e}")

        conn.commit()
        conn.close()

        # Log récapitulatif
        self.logger.info(f"📊 Batch traité: {added} nouveaux | {skipped_existing} déjà connus | {skipped_no_address} sans adresse | {skipped_no_details} sans détails")

    async def run(self):
        """Boucle principale du scanner"""
        self.logger.info("Scanner démarré...")
        while True:
            try:
                # Récupérer les nouveaux tokens
                new_tokens = await self.fetch_new_tokens()

                if new_tokens:
                    self.logger.info(f"{len(new_tokens)} nouveaux tokens potentiels trouvés. Traitement...")
                    await self.process_token_batch(new_tokens)

                # Délai avant le prochain scan
                await asyncio.sleep(self.scan_delay)

            except KeyboardInterrupt:
                self.logger.info("Scanner arrêté par l'utilisateur.")
                break
            except Exception as e:
                self.logger.error(f"Erreur dans la boucle principale du scanner: {e}")
                await asyncio.sleep(10)  # Attendre avant de réessayer

if __name__ == "__main__":
    scanner = EnhancedScanner()
    try:
        asyncio.run(scanner.run())
    except KeyboardInterrupt:
        print("\nScanner arrêté.")
    except Exception as e:
        print(f"Erreur fatale: {e}")
