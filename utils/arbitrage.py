
from typing import Dict, Any, List, Tuple, Optional
from math import isfinite

def _best_odds_by_outcome(bookmakers: List[Dict[str, Any]], bookmaker_whitelist: set) -> Tuple[Dict[str, float], Dict[str, str]]:
    """
    For a list of bookmaker price sets, return best decimal odds per outcome and which book offered it.
    Supports 2- or 3-outcome markets (e.g., tennis moneyline or soccer 1x2 h2h).
    """
    best: Dict[str, float] = {}
    source: Dict[str, str] = {}
    for bm in bookmakers:
        name = (bm.get("title") or bm.get("key") or "").lower()
        if bookmaker_whitelist and name not in bookmaker_whitelist:
            continue
        for market in bm.get("markets", []):
            if market.get("key") != "h2h":
                continue
            for out in market.get("outcomes", []):
                outcome_name = out.get("name")
                price = out.get("price")
                if outcome_name is None or price is None:
                    continue
                try:
                    price = float(price)
                except Exception:
                    continue
                if not isfinite(price) or price <= 1.0:
                    continue
                if outcome_name not in best or price > best[outcome_name]:
                    best[outcome_name] = price
                    source[outcome_name] = name
    return best, source

def _arb_edge(best: Dict[str, float]) -> float:
    inv_sum = sum(1.0 / o for o in best.values())
    return (1.0 - inv_sum) * 100.0  # percent

def _stakes_for_edge(best: Dict[str, float], bankroll: float = 100.0) -> Dict[str, float]:
    inv = {k: 1.0 / v for k, v in best.items()}
    inv_sum = sum(inv.values())
    stakes = {k: bankroll * inv_v / inv_sum for k, inv_v in inv.items()}
    return stakes

def find_arbs_for_event(event: Dict[str, Any], min_edge_pct: float = 0.25, bookmaker_whitelist: set = None) -> List[Dict[str, Any]]:
    """
    Given a single event (from The Odds API) compute arbitrage opportunities.
    Returns a list of arbs (usually 0 or 1) with details.
    """
    bookmaker_whitelist = bookmaker_whitelist or set()
    bms = event.get("bookmakers") or []
    if not bms:
        return []
    best, source = _best_odds_by_outcome(bms, bookmaker_whitelist)
    if len(best) not in (2, 3):
        return []
    edge = _arb_edge(best)
    if edge <= min_edge_pct:
        return []
    stakes = _stakes_for_edge(best, bankroll=100.0)
    return [{
        "event_id": event.get("id"),
        "sport_title": event.get("sport_title"),
        "commence_time": event.get("commence_time"),
        "home": event.get("home_team"),
        "away": event.get("away_team"),
        "best_odds": best,
        "best_books": source,
        "edge_pct": round(edge, 4),
        "stakes_100": {k: round(v, 2) for k, v in stakes.items()},
    }]

def format_arb_message(arb: Dict[str, Any]) -> str:
    """Pretty Telegram message in Russian."""
    title = f"🎯 Арбитраж обнаружен ({arb['sport_title']})"
    time_str = f"⏱ {arb.get('commence_time','?')}"
    teams = f"🏟 {arb.get('home','?')} vs {arb.get('away','?')}"
    lines = [title, time_str, teams, ""]
    lines.append("📈 Лучшие коэффициенты:")
    for outcome, odd in arb["best_odds"].items():
        book = arb["best_books"].get(outcome, "?")
        lines.append(f"• {outcome}: {odd} (букмекер: {book})")
    lines.append("")
    lines.append(f"💰 Гарантированная маржа: {arb['edge_pct']}% на банке 100$")
    stake_lines = " | ".join([f"{k}: ${v}" for k, v in arb["stakes_100"].items()])
    lines.append(f"Распределение ставок: {stake_lines}")
    lines.append("")
    lines.append("⚠️ Внимание: проверьте лимиты и правила букмекеров. Курсы быстро меняются.")
    return "\n".join(lines)
