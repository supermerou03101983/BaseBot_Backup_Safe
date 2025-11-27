#!/usr/bin/env python3
"""
Analyse approfondie de l'historique des trades
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

def parse_pnl(pnl_str):
    """Parse P&L string to float"""
    return float(pnl_str.replace('%', ''))

def analyze_trades(csv_path):
    """Analyse complète des trades"""

    # Charger les données
    df = pd.read_csv(csv_path)

    # Nettoyer les données
    df['P&L_pct'] = df['P&L'].apply(parse_pnl)
    df['Out_ETH'] = pd.to_numeric(df['Out (ETH)'])
    df['In_ETH'] = pd.to_numeric(df['In (ETH)'])
    df['Profit_ETH'] = df['Out_ETH'] - df['In_ETH']
    df['Entry_Time'] = pd.to_datetime(df['Entrée'])
    df['Exit_Time'] = pd.to_datetime(df['Sortie'])

    print("=" * 80)
    print("📊 ANALYSE COMPLÈTE DES TRADES - BASE BOT")
    print("=" * 80)

    # ========== STATISTIQUES GLOBALES ==========
    print("\n" + "=" * 80)
    print("🎯 STATISTIQUES GLOBALES")
    print("=" * 80)

    total_trades = len(df)
    winning_trades = len(df[df['P&L_pct'] > 0])
    losing_trades = len(df[df['P&L_pct'] < 0])
    win_rate = (winning_trades / total_trades) * 100

    avg_profit = df[df['P&L_pct'] > 0]['P&L_pct'].mean()
    avg_loss = df[df['P&L_pct'] < 0]['P&L_pct'].mean()

    total_profit_eth = df['Profit_ETH'].sum()
    total_profit_pct = ((df['Out_ETH'].sum() / df['In_ETH'].sum()) - 1) * 100

    risk_reward = abs(avg_profit / avg_loss) if avg_loss != 0 else 0

    print(f"📈 Nombre total de trades: {total_trades}")
    print(f"✅ Trades gagnants: {winning_trades} ({win_rate:.1f}%)")
    print(f"❌ Trades perdants: {losing_trades} ({100-win_rate:.1f}%)")
    print(f"\n�� PROFITABILITÉ:")
    print(f"   Profit moyen (winners): {avg_profit:.2f}%")
    print(f"   Loss moyen (losers): {avg_loss:.2f}%")
    print(f"   Risk/Reward Ratio: {risk_reward:.2f}x")
    print(f"\n💵 RÉSULTAT NET:")
    print(f"   Total P&L: {total_profit_eth:.4f} ETH ({total_profit_pct:.2f}%)")
    print(f"   Profit par trade: {total_profit_eth/total_trades:.4f} ETH")

    # ========== ANALYSE PAR TOKEN ==========
    print("\n" + "=" * 80)
    print("🪙 ANALYSE PAR TOKEN")
    print("=" * 80)

    token_stats = df.groupby('Symbol').agg({
        'P&L_pct': ['count', 'mean', 'sum'],
        'Profit_ETH': 'sum'
    }).round(2)

    token_stats.columns = ['Trades', 'Avg P&L %', 'Total P&L %', 'Total ETH']
    token_stats = token_stats.sort_values('Total ETH', ascending=False)

    print("\nTokens triés par profit total:")
    for token, row in token_stats.iterrows():
        emoji = "🟢" if row['Total ETH'] > 0 else "🔴"
        print(f"{emoji} {token:10s} | {int(row['Trades'])} trades | "
              f"Avg: {row['Avg P&L %']:+7.2f}% | Total: {row['Total ETH']:+.4f} ETH")

    # ========== ANALYSE DES TRADES PERDANTS ==========
    print("\n" + "=" * 80)
    print("🔍 ANALYSE DES TRADES PERDANTS")
    print("=" * 80)

    losers = df[df['P&L_pct'] < 0].sort_values('P&L_pct')

    print(f"\n⚠️  {len(losers)} trades perdants analysés:")
    print(f"   Pire loss: {losers['P&L_pct'].min():.2f}% ({losers.iloc[0]['Symbol']})")
    print(f"   Loss médian: {losers['P&L_pct'].median():.2f}%")
    print(f"\n📋 Top 5 pires trades:")
    for idx, row in losers.head(5).iterrows():
        print(f"   • {row['Symbol']:10s} {row['P&L_pct']:+7.2f}% | Entrée: {row['Entrée']}")

    # Patterns des perdants
    print(f"\n🔬 PATTERNS DES PERDANTS:")
    loser_tokens = losers['Symbol'].value_counts()
    print(f"   Tokens avec le + de pertes:")
    for token, count in loser_tokens.head(3).items():
        token_trades = df[df['Symbol'] == token]
        wr = (len(token_trades[token_trades['P&L_pct'] > 0]) / len(token_trades)) * 100
        print(f"   • {token}: {count} losses ({wr:.0f}% win rate)")

    # ========== ANALYSE DES TRADES GAGNANTS ==========
    print("\n" + "=" * 80)
    print("🏆 ANALYSE DES TRADES GAGNANTS")
    print("=" * 80)

    winners = df[df['P&L_pct'] > 0].sort_values('P&L_pct', ascending=False)

    print(f"\n✨ {len(winners)} trades gagnants:")
    print(f"   Meilleur gain: {winners['P&L_pct'].max():.2f}% ({winners.iloc[0]['Symbol']})")
    print(f"   Gain médian: {winners['P&L_pct'].median():.2f}%")
    print(f"\n📋 Top 5 meilleurs trades:")
    for idx, row in winners.head(5).iterrows():
        print(f"   • {row['Symbol']:10s} {row['P&L_pct']:+7.2f}% | Profit: {row['Profit_ETH']:+.4f} ETH")

    # ========== ANALYSE TEMPORELLE ==========
    print("\n" + "=" * 80)
    print("⏰ ANALYSE TEMPORELLE")
    print("=" * 80)

    df['Hour'] = df['Entry_Time'].dt.hour
    hourly_stats = df.groupby('Hour').agg({
        'P&L_pct': ['count', 'mean'],
        'Profit_ETH': 'sum'
    }).round(2)

    hourly_stats.columns = ['Trades', 'Avg P&L %', 'Total ETH']
    hourly_stats = hourly_stats[hourly_stats['Trades'] > 0].sort_values('Total ETH', ascending=False)

    print("\nPerformance par heure (Top 5):")
    for hour, row in hourly_stats.head(5).iterrows():
        print(f"   {int(hour):02d}h00 | {int(row['Trades'])} trades | "
              f"Avg: {row['Avg P&L %']:+7.2f}% | Total: {row['Total ETH']:+.4f} ETH")

    print("\nPires heures (Bottom 3):")
    for hour, row in hourly_stats.tail(3).iterrows():
        print(f"   {int(hour):02d}h00 | {int(row['Trades'])} trades | "
              f"Avg: {row['Avg P&L %']:+7.2f}% | Total: {row['Total ETH']:+.4f} ETH")

    # ========== DURÉE DES POSITIONS ==========
    print("\n" + "=" * 80)
    print("⏱️  DURÉE DES POSITIONS")
    print("=" * 80)

    df['Duration_minutes'] = (df['Exit_Time'] - df['Entry_Time']).dt.total_seconds() / 60

    winners_with_duration = winners[winners['Duration_minutes'].notna()]
    losers_with_duration = losers[losers['Duration_minutes'].notna()]

    if len(winners_with_duration) > 0:
        print(f"\n✅ Trades gagnants:")
        print(f"   Durée moyenne: {winners_with_duration['Duration_minutes'].mean():.1f} minutes")
        print(f"   Durée médiane: {winners_with_duration['Duration_minutes'].median():.1f} minutes")

    if len(losers_with_duration) > 0:
        print(f"\n❌ Trades perdants:")
        print(f"   Durée moyenne: {losers_with_duration['Duration_minutes'].mean():.1f} minutes")
        print(f"   Durée médiane: {losers_with_duration['Duration_minutes'].median():.1f} minutes")

    # ========== DISTRIBUTION DES GAINS/PERTES ==========
    print("\n" + "=" * 80)
    print("📊 DISTRIBUTION DES GAINS/PERTES")
    print("=" * 80)

    bins = [(-100, -20, "💀 < -20%"),
            (-20, -10, "🔴 -20% à -10%"),
            (-10, -5, "🟠 -10% à -5%"),
            (-5, 0, "🟡 -5% à 0%"),
            (0, 5, "🟢 0% à 5%"),
            (5, 10, "💚 5% à 10%"),
            (10, 20, "💎 10% à 20%"),
            (20, 50, "🚀 20% à 50%"),
            (50, 200, "🌙 > 50%")]

    print("\nRépartition:")
    for min_val, max_val, label in bins:
        count = len(df[(df['P&L_pct'] >= min_val) & (df['P&L_pct'] < max_val)])
        if count > 0:
            pct = (count / total_trades) * 100
            bar = "█" * int(pct / 2)
            print(f"{label:20s} | {count:2d} trades ({pct:5.1f}%) {bar}")

    # ========== RECOMMANDATIONS ==========
    print("\n" + "=" * 80)
    print("💡 RECOMMANDATIONS")
    print("=" * 80)

    # Calcul de l'expectancy
    expectancy = (win_rate/100 * avg_profit) + ((100-win_rate)/100 * avg_loss)

    print(f"\n🎲 Expectancy par trade: {expectancy:.2f}%")
    if expectancy > 5:
        print("   ✅ Excellent! Votre stratégie est très profitable.")
    elif expectancy > 2:
        print("   ✅ Bon! Stratégie rentable.")
    elif expectancy > 0:
        print("   ⚠️  Marginalement profitable. Améliorations nécessaires.")
    else:
        print("   ❌ Non profitable. Révision urgente requise.")

    print(f"\n📈 POINTS FORTS:")
    if win_rate > 60:
        print(f"   ✅ Win rate excellent ({win_rate:.1f}%)")
    if risk_reward > 2:
        print(f"   ✅ Risk/Reward très bon ({risk_reward:.2f}x)")
    if avg_profit > 20:
        print(f"   ✅ Gains moyens élevés ({avg_profit:.1f}%)")

    print(f"\n⚠️  POINTS D'AMÉLIORATION:")
    if abs(avg_loss) > 10:
        print(f"   🔴 Pertes moyennes trop élevées ({avg_loss:.1f}%)")
        print(f"      → Resserrer le stop loss de 15% à 8-10%")

    if win_rate < 55:
        print(f"   🔴 Win rate insuffisant ({win_rate:.1f}%)")
        print(f"      → Améliorer les filtres d'entrée (score minimum)")

    # Identifier les tokens problématiques
    losing_tokens = df[df['P&L_pct'] < 0].groupby('Symbol')['P&L_pct'].agg(['count', 'mean'])
    problematic = losing_tokens[losing_tokens['count'] >= 2].sort_values('mean')
    if len(problematic) > 0:
        print(f"\n   🔴 Tokens à éviter:")
        for token, stats in problematic.iterrows():
            print(f"      → {token}: {int(stats['count'])} losses, avg {stats['mean']:.1f}%")

    # Identifier les meilleurs horaires
    best_hours = hourly_stats.head(3)
    if len(best_hours) > 0:
        print(f"\n   ✅ Meilleurs créneaux horaires à privilégier:")
        for hour, _ in best_hours.iterrows():
            print(f"      → {int(hour):02d}h00")

    print("\n" + "=" * 80)
    print("FIN DE L'ANALYSE")
    print("=" * 80)

if __name__ == "__main__":
    csv_path = "Historique des trades 14 novembre Base Bot 1.csv"
    analyze_trades(csv_path)
