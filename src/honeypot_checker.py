#!/usr/bin/env python3
"""
Module de vérification honeypot pour tokens ERC20
Utilise l'API Honeypot.is pour détecter les tokens malveillants
"""

import requests
from typing import Dict, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HoneypotChecker:
    """Vérification honeypot via API Honeypot.is"""

    def __init__(self):
        self.api_url = "https://api.honeypot.is/v2/IsHoneypot"
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Crée une session avec retry automatique"""
        session = requests.Session()
        retry = Retry(
            total=2,  # Seulement 2 retries pour ne pas ralentir
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def check_token(self, token_address: str, chain_id: int = 8453) -> Dict:
        """
        Vérifie si un token est un honeypot

        Args:
            token_address: Adresse du token à vérifier
            chain_id: ID de la blockchain (8453 = Base)

        Returns:
            {
                'is_honeypot': bool,
                'is_safe': bool,  # True si le token est sûr à trader
                'buy_tax': float,
                'sell_tax': float,
                'transfer_tax': float,
                'can_buy': bool,
                'can_sell': bool,
                'liquidity_amount': float,
                'flags': list,
                'risk_level': str,  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
                'error': str or None
            }
        """
        try:
            # Appel API
            params = {
                'address': token_address.lower(),
                'chainID': chain_id
            }

            response = self.session.get(
                self.api_url,
                params=params,
                timeout=8  # Timeout court pour ne pas bloquer le bot
            )

            if response.status_code != 200:
                return self._error_response(f"API returned {response.status_code}")

            data = response.json()

            # Parser la réponse
            honeypot_result = data.get('honeypotResult', {})
            simulation_result = data.get('simulationResult', {})
            holder_analysis = data.get('holderAnalysis', {})

            # Données de base
            is_honeypot = honeypot_result.get('isHoneypot', False)

            # Taxes
            buy_tax = float(simulation_result.get('buyTax', 0))
            sell_tax = float(simulation_result.get('sellTax', 0))
            transfer_tax = float(simulation_result.get('transferTax', 0))

            # Capacités
            buy_gas = simulation_result.get('buyGas')
            sell_gas = simulation_result.get('sellGas')

            can_buy = buy_gas is not None and buy_gas > 0
            can_sell = sell_gas is not None and sell_gas > 0

            # Flags de danger
            flags = []
            risk_level = 'LOW'

            # CRITICAL: Honeypot confirmé
            if is_honeypot:
                flags.append('HONEYPOT_CONFIRMED')
                risk_level = 'CRITICAL'

            # CRITICAL: Impossible de vendre
            if not can_sell:
                flags.append('CANNOT_SELL')
                risk_level = 'CRITICAL'

            # HIGH: Taxes excessives
            if sell_tax >= 50:
                flags.append('EXTREME_SELL_TAX')
                risk_level = 'CRITICAL'
            elif sell_tax >= 20:
                flags.append('VERY_HIGH_SELL_TAX')
                risk_level = 'HIGH'
            elif sell_tax >= 10:
                flags.append('HIGH_SELL_TAX')
                risk_level = 'MEDIUM' if risk_level == 'LOW' else risk_level

            if buy_tax >= 20:
                flags.append('VERY_HIGH_BUY_TAX')
                risk_level = 'HIGH' if risk_level == 'LOW' else risk_level
            elif buy_tax >= 10:
                flags.append('HIGH_BUY_TAX')
                risk_level = 'MEDIUM' if risk_level == 'LOW' else risk_level

            # MEDIUM: Autres signaux suspects
            if transfer_tax > 5:
                flags.append('HIGH_TRANSFER_TAX')
                risk_level = 'MEDIUM' if risk_level == 'LOW' else risk_level

            # Vérification holders (concentration)
            holders = holder_analysis.get('holders', [])
            if holders:
                # Top holder possède > 50% = RED FLAG
                top_holder_pct = holders[0].get('percent', 0) if len(holders) > 0 else 0
                if top_holder_pct > 50:
                    flags.append('CONCENTRATED_OWNERSHIP')
                    risk_level = 'HIGH' if risk_level in ['LOW', 'MEDIUM'] else risk_level

            # Simulation non réussie
            if not simulation_result.get('simulationSuccess', False):
                flags.append('SIMULATION_FAILED')
                risk_level = 'HIGH' if risk_level == 'LOW' else risk_level

            # Déterminer si le token est sûr
            is_safe = (
                not is_honeypot and
                can_sell and
                sell_tax < 10 and  # Max 10% sell tax
                buy_tax < 10 and   # Max 10% buy tax
                risk_level in ['LOW', 'MEDIUM']
            )

            return {
                'is_honeypot': is_honeypot,
                'is_safe': is_safe,
                'buy_tax': buy_tax,
                'sell_tax': sell_tax,
                'transfer_tax': transfer_tax,
                'can_buy': can_buy,
                'can_sell': can_sell,
                'liquidity_amount': float(simulation_result.get('liquidityAmount', 0)),
                'flags': flags,
                'risk_level': risk_level,
                'error': None
            }

        except requests.Timeout:
            # Timeout = rejeter par sécurité mais pas bloquer le bot
            return self._error_response("API timeout")
        except Exception as e:
            return self._error_response(str(e))

    def _error_response(self, error_msg: str) -> Dict:
        """Retourne une réponse d'erreur sécurisée"""
        return {
            'is_honeypot': True,  # Par sécurité, rejeter si erreur
            'is_safe': False,
            'buy_tax': 0,
            'sell_tax': 0,
            'transfer_tax': 0,
            'can_buy': False,
            'can_sell': False,
            'liquidity_amount': 0,
            'flags': ['API_ERROR'],
            'risk_level': 'CRITICAL',
            'error': error_msg
        }

    def close(self):
        """Ferme la session HTTP"""
        if self.session:
            self.session.close()


# Fonction standalone pour usage rapide
def check_honeypot(token_address: str, chain_id: int = 8453) -> Dict:
    """
    Vérifie rapidement si un token est un honeypot

    Usage:
        result = check_honeypot("0x...")
        if result['is_safe']:
            print("Token OK")
        else:
            print(f"Token dangereux: {result['flags']}")
    """
    checker = HoneypotChecker()
    try:
        return checker.check_token(token_address, chain_id)
    finally:
        checker.close()


if __name__ == "__main__":
    # Test du module
    import sys

    if len(sys.argv) < 2:
        print("Usage: python honeypot_checker.py <token_address>")
        sys.exit(1)

    token = sys.argv[1]
    print(f"🔍 Vérification du token {token}...\n")

    result = check_honeypot(token)

    print("=" * 60)
    print(f"🍯 HONEYPOT: {'OUI' if result['is_honeypot'] else 'NON'}")
    print(f"✅ SAFE TO TRADE: {'OUI' if result['is_safe'] else 'NON'}")
    print(f"⚠️  RISK LEVEL: {result['risk_level']}")
    print("=" * 60)
    print(f"💰 Buy Tax: {result['buy_tax']:.1f}%")
    print(f"💸 Sell Tax: {result['sell_tax']:.1f}%")
    print(f"🔄 Transfer Tax: {result['transfer_tax']:.1f}%")
    print(f"✅ Can Buy: {result['can_buy']}")
    print(f"❌ Can Sell: {result['can_sell']}")
    print(f"💧 Liquidity: ${result['liquidity_amount']:,.0f}")

    if result['flags']:
        print(f"\n🚩 FLAGS: {', '.join(result['flags'])}")

    if result['error']:
        print(f"\n❌ ERROR: {result['error']}")

    print("=" * 60)
