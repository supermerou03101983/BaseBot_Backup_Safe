#!/usr/bin/env python3
"""
Analyse approfondie de l'historique des trades (sans dépendances externes)
"""

import csv
from datetime import datetime
from collections import defaultdict

def parse_pnl(pnl_str):
    """Parse P&L string to float"""
    return float(pnl_str.replace('%', ''))

def parse_eth(eth_str):
    """Parse ETH value"""
    return float(eth_str)

def analyze_trades(csv_path):
    """Analyse complète des trades"""

    # Charger les données
    trades = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                trade = {
                    'symbol': row['Symbol'],
                    'pnl_pct': parse_pnl(row['P&L']),
                    'in_eth': parse_eth(row['In (ETH)']),
                    'out_eth': parse_eth(row['Out (ETH)']),
                    'entry_time': datetime.strptime(row['Entrée'], '%Y-%m-%d %H:%M:%S'),
                    'exit_time': datetime.strptime(row['Sortie'], '%Y-%m-%d %H:%M:%S'),
                }
                trade['profit_eth'] = trade['out_eth'] - trade['in_eth']
                trades.append(trade)
            except Exception as e:
                continue

    print("=" * 80)
    print("📊 ANALYSE COMPLÈTE DES TRADES - BASE BOT")
    print("=" * 80)

    # ========== STATISTIQUES GLOBALES ==========
    print("\n" + "=" * 80)
    print("🎯 STATISTIQUES GLOBALES")
    print("=" * 80)

    total_trades = len(trades)
    winners = [t for t in trades if t['pnl_pct'] > 0]
    losers = [t for t in trades if t['pnl_pct'] < 0]

    win_rate = (len(winners) / total_trades) * 100

    avg_profit = sum(t['pnl_pct'] for t in winners) / len(winners) if winners else 0
    avg_loss = sum(t['pnl_pct'] for t in losers) / len(losers) if losers else 0

    total_profit_eth = sum(t['profit_eth'] for t in trades)
    total_in_eth = sum(t['in_eth'] for t in trades)
    total_out_eth = sum(t['out_eth'] for t in trades)
    total_profit_pct = ((total_out_eth / total_in_eth) - 1) * 100

    risk_reward = abs(avg_profit / avg_loss) if avg_loss != 0 else 0

    print(f"📈 Nombre total de trades: {total_trades}")
    print(f"✅ Trades gagnants: {len(winners)} ({win_rate:.1f}%)")
    print(f"❌ Trades perdants: {len(losers)} ({100-win_rate:.1f}%)")
    print(f"\n💰 PROFITABILITÉ:")
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

    token_stats = defaultdict(lambda: {'count': 0, 'total_pnl': 0, 'total_eth': 0, 'pnls': []})
    for t in trades:
        token_stats[t['symbol']]['count'] += 1
        token_stats[t['symbol']]['total_pnl'] += t['pnl_pct']
        token_stats[t['symbol']]['total_eth'] += t['profit_eth']
        token_stats[t['symbol']]['pnls'].append(t['pnl_pct'])

    sorted_tokens = sorted(token_stats.items(), key=lambda x: x[1]['total_eth'], reverse=True)

    print("\nTokens triés par profit total:")
    for token, stats in sorted_tokens:
        emoji = "🟢" if stats['total_eth'] > 0 else "🔴"
        avg_pnl = stats['total_pnl'] / stats['count']
        print(f"{emoji} {token:10s} | {stats['count']} trades | "
              f"Avg: {avg_pnl:+7.2f}% | Total: {stats['total_eth']:+.4f} ETH")

    # ========== ANALYSE DES TRADES PERDANTS ==========
    print("\n" + "=" * 80)
    print("🔍 ANALYSE DES TRADES PERDANTS")
    print("=" * 80)

    losers_sorted = sorted(losers, key=lambda x: x['pnl_pct'])

    print(f"\n⚠️  {len(losers)} trades perdants analysés:")
    if losers_sorted:
        print(f"   Pire loss: {losers_sorted[0]['pnl_pct']:.2f}% ({losers_sorted[0]['symbol']})")
        median_idx = len(losers_sorted) // 2
        print(f"   Loss médian: {losers_sorted[median_idx]['pnl_pct']:.2f}%")
        print(f"\n📋 Top 5 pires trades:")
        for t in losers_sorted[:5]:
            print(f"   • {t['symbol']:10s} {t['pnl_pct']:+7.2f}% | "
                  f"Entrée: {t['entry_time'].strftime('%Y-%m-%d %H:%M')}")

    # Patterns des perdants
    print(f"\n🔬 PATTERNS DES PERDANTS:")
    loser_tokens = defaultdict(int)
    for t in losers:
        loser_tokens[t['symbol']] += 1

    sorted_loser_tokens = sorted(loser_tokens.items(), key=lambda x: x[1], reverse=True)
    print(f"   Tokens avec le + de pertes:")
    for token, count in sorted_loser_tokens[:3]:
        token_trades = [t for t in trades if t['symbol'] == token]
        token_winners = [t for t in token_trades if t['pnl_pct'] > 0]
        wr = (len(token_winners) / len(token_trades)) * 100
        print(f"   • {token}: {count} losses ({wr:.0f}% win rate)")

    # ========== ANALYSE DES TRADES GAGNANTS ==========
    print("\n" + "=" * 80)
    print("🏆 ANALYSE DES TRADES GAGNANTS")
    print("=" * 80)

    winners_sorted = sorted(winners, key=lambda x: x['pnl_pct'], reverse=True)

    print(f"\n✨ {len(winners)} trades gagnants:")
    if winners_sorted:
        print(f"   Meilleur gain: {winners_sorted[0]['pnl_pct']:.2f}% ({winners_sorted[0]['symbol']})")
        median_idx = len(winners_sorted) // 2
        print(f"   Gain médian: {winners_sorted[median_idx]['pnl_pct']:.2f}%")
        print(f"\n📋 Top 5 meilleurs trades:")
        for t in winners_sorted[:5]:
            print(f"   • {t['symbol']:10s} {t['pnl_pct']:+7.2f}% | Profit: {t['profit_eth']:+.4f} ETH")

    # ========== ANALYSE TEMPORELLE ==========
    print("\n" + "=" * 80)
    print("⏰ ANALYSE TEMPORELLE")
    print("=" * 80)

    hourly_stats = defaultdict(lambda: {'count': 0, 'total_pnl': 0, 'total_eth': 0})
    for t in trades:
        hour = t['entry_time'].hour
        hourly_stats[hour]['count'] += 1
        hourly_stats[hour]['total_pnl'] += t['pnl_pct']
        hourly_stats[hour]['total_eth'] += t['profit_eth']

    sorted_hours = sorted(hourly_stats.items(), key=lambda x: x[1]['total_eth'], reverse=True)

    print("\nPerformance par heure (Top 5):")
    for hour, stats in sorted_hours[:5]:
        avg_pnl = stats['total_pnl'] / stats['count']
        print(f"   {hour:02d}h00 | {stats['count']} trades | "
              f"Avg: {avg_pnl:+7.2f}% | Total: {stats['total_eth']:+.4f} ETH")

    print("\nPires heures (Bottom 3):")
    for hour, stats in sorted_hours[-3:]:
        avg_pnl = stats['total_pnl'] / stats['count']
        print(f"   {hour:02d}h00 | {stats['count']} trades | "
              f"Avg: {avg_pnl:+7.2f}% | Total: {stats['total_eth']:+.4f} ETH")

    # ========== DURÉE DES POSITIONS ==========
    print("\n" + "=" * 80)
    print("⏱️  DURÉE DES POSITIONS")
    print("=" * 80)

    winners_durations = []
    losers_durations = []

    for t in winners:
        duration_minutes = (t['exit_time'] - t['entry_time']).total_seconds() / 60
        winners_durations.append(duration_minutes)

    for t in losers:
        duration_minutes = (t['exit_time'] - t['entry_time']).total_seconds() / 60
        losers_durations.append(duration_minutes)

    if winners_durations:
        avg_winner_duration = sum(winners_durations) / len(winners_durations)
        winners_durations_sorted = sorted(winners_durations)
        median_winner = winners_durations_sorted[len(winners_durations_sorted) // 2]
        print(f"\n✅ Trades gagnants:")
        print(f"   Durée moyenne: {avg_winner_duration:.1f} minutes")
        print(f"   Durée médiane: {median_winner:.1f} minutes")

    if losers_durations:
        avg_loser_duration = sum(losers_durations) / len(losers_durations)
        losers_durations_sorted = sorted(losers_durations)
        median_loser = losers_durations_sorted[len(losers_durations_sorted) // 2]
        print(f"\n❌ Trades perdants:")
        print(f"   Durée moyenne: {avg_loser_duration:.1f} minutes")
        print(f"   Durée médiane: {median_loser:.1f} minutes")

    # ========== DISTRIBUTION DES GAINS/PERTES ==========
    print("\n" + "=" * 80)
    print("📊 DISTRIBUTION DES GAINS/PERTES")
    print("=" * 80)

    bins = [
        (-100, -20, "💀 < -20%"),
        (-20, -10, "🔴 -20% à -10%"),
        (-10, -5, "🟠 -10% à -5%"),
        (-5, 0, "🟡 -5% à 0%"),
        (0, 5, "🟢 0% à 5%"),
        (5, 10, "💚 5% à 10%"),
        (10, 20, "💎 10% à 20%"),
        (20, 50, "🚀 20% à 50%"),
        (50, 200, "🌙 > 50%")
    ]

    print("\nRépartition:")
    for min_val, max_val, label in bins:
        count = len([t for t in trades if min_val <= t['pnl_pct'] < max_val])
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
        print(f"      → Resserrer le stop loss à 8-10% au lieu du niveau actuel")

    if win_rate < 55:
        print(f"   🔴 Win rate insuffisant ({win_rate:.1f}%)")
        print(f"      → Améliorer les filtres d'entrée (score minimum)")

    # Identifier les tokens problématiques
    problematic_tokens = []
    for token, stats in token_stats.items():
        if stats['count'] >= 2:
            losses = [pnl for pnl in stats['pnls'] if pnl < 0]
            if len(losses) >= 2:
                avg_loss_token = sum(losses) / len(losses)
                problematic_tokens.append((token, len(losses), avg_loss_token))

    if problematic_tokens:
        problematic_tokens.sort(key=lambda x: x[2])
        print(f"\n   🔴 Tokens à éviter:")
        for token, loss_count, avg_loss_val in problematic_tokens[:3]:
            print(f"      → {token}: {loss_count} losses, avg {avg_loss_val:.1f}%")

    # Identifier les meilleurs horaires
    if sorted_hours[:3]:
        print(f"\n   ✅ Meilleurs créneaux horaires à privilégier:")
        for hour, _ in sorted_hours[:3]:
            print(f"      → {hour:02d}h00")

    print("\n" + "=" * 80)
    print("FIN DE L'ANALYSE")
    print("=" * 80)

if __name__ == "__main__":
    csv_path = "Historique des trades 14 novembre Base Bot 1.csv"
    analyze_trades(csv_path)
