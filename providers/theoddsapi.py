
import aiohttp
from typing import List, Dict, Any, Optional

BASE = "https://api.the-odds-api.com/v4"

class TheOddsAPI:
    """
    Minimal adapter for The Odds API (https://theoddsapi.com/)
    Only uses /sports/{sport_key}/odds endpoint with h2h market.
    """
    def __init__(self, api_key: str, timeout: int = 20):
        self.api_key = api_key
        self.timeout = timeout

    async def fetch_odds(self, sport_key: str, regions: str = "us,uk,eu,au",
                         markets: str = "h2h", odds_format: str = "decimal",
                         date_format: str = "iso") -> List[Dict[str, Any]]:
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
            "dateFormat": date_format,
        }
        url = f"{BASE}/sports/{sport_key}/odds"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            async with session.get(url, params=params) as r:
                if r.status != 200:
                    text = await r.text()
                    raise RuntimeError(f"TheOddsAPI HTTP {r.status}: {text}")
                data = await r.json()
                # Normalize shape to our utils expectations
                return data
