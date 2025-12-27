"""
📊 COT (Commitment of Traders) Data Service - V2.5.2
=====================================================

Holt und verarbeitet COT-Daten von der CFTC für Commodity-Trading.

Datenquellen:
1. CFTC PRE API (kostenlos, offiziell)
   - URL: https://publicreporting.cftc.gov/
   - Doku: https://publicreporting.cftc.gov/stories/s/User-s-Guide/p2fg-u73y/
   
2. cot_reports Python Library (GitHub)
   - pip install cot_reports
   - GitHub: https://github.com/NDelventhal/cot_reports

COT-Report Typen:
- Legacy: Einfache Aufteilung (Commercial/Non-Commercial/Non-Reportable)
- Disaggregated: Detaillierte Aufteilung nach Trader-Typ
- TFF (Traders in Financial Futures): Für Finanz-Futures

Für Trading relevant:
- commercial_net: Hedger-Positionen (Smart Money, produzenten/Verbraucher)
- noncommercial_net: Spekulanten (Hedge Funds, CTAs)
- Änderung zur Vorwoche: Momentum-Indikator
"""

import logging
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# CFTC Contract Codes für unsere Assets
# Quelle: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm
CFTC_CONTRACT_CODES = {
    # Edelmetalle (COMEX)
    'GOLD': '088691',      # Gold Futures
    'SILVER': '084691',    # Silver Futures
    'PLATINUM': '076651',  # Platinum Futures
    'PALLADIUM': '075651', # Palladium Futures
    
    # Energie (NYMEX)
    'WTI_CRUDE': '067651',     # Crude Oil, Light Sweet
    'BRENT_CRUDE': '06765T',   # Brent (ICE)
    'NATURAL_GAS': '023651',   # Natural Gas
    
    # Agrar (CBOT)
    'WHEAT': '001602',     # Wheat
    'CORN': '002602',      # Corn
    'SOYBEANS': '005602',  # Soybeans
    'SOYBEAN': '005602',   # Alias
    
    # Soft Commodities (ICE/NYBOT)
    'COFFEE': '083731',    # Coffee C
    'SUGAR': '080732',     # Sugar No. 11
    'COCOA': '073732',     # Cocoa
    'COTTON': '033661',    # Cotton No. 2
    
    # Forex (CME)
    'EURUSD': '099741',    # Euro FX
    'EUR/USD': '099741',
    'GBPUSD': '096742',    # British Pound
    'USDJPY': '097741',    # Japanese Yen
    
    # Crypto
    'BITCOIN': '133741',   # Bitcoin (CME)
    'BTC': '133741',
    'BTCUSD': '133741'
}


class COTDataService:
    """
    Service zum Abrufen und Cachen von COT-Daten.
    
    Die CFTC veröffentlicht COT-Daten jeden Freitag um 15:30 EST
    für Positionen vom Dienstag derselben Woche.
    """
    
    # CFTC PRE API Base URL
    CFTC_BASE_URL = "https://publicreporting.cftc.gov/resource"
    
    # Disaggregated Futures-Only Dataset ID
    DISAGGREGATED_DATASET = "72hh-3qpy"  # Disaggregated Futures Only
    LEGACY_DATASET = "6dca-aqww"          # Legacy Futures Only
    
    def __init__(self, cache_dir: str = "/app/backend/data/cot_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict] = {}
        self._last_fetch: Dict[str, datetime] = {}
        
    async def get_cot_data(self, commodity: str) -> Optional[Dict]:
        """
        Holt COT-Daten für ein Commodity.
        
        Returns:
            Dict mit:
            - commercial_long: Long Positionen der Commercials
            - commercial_short: Short Positionen der Commercials
            - commercial_net: Netto-Position (Long - Short)
            - noncommercial_long: Spekulanten Long
            - noncommercial_short: Spekulanten Short
            - noncommercial_net: Spekulanten Netto
            - weekly_change: Änderung zur Vorwoche
            - report_date: Datum des Reports
            - sentiment: 'bullish' / 'bearish' / 'neutral'
        """
        commodity_upper = commodity.upper()
        contract_code = CFTC_CONTRACT_CODES.get(commodity_upper)
        
        if not contract_code:
            logger.warning(f"Kein CFTC Contract Code für {commodity}")
            return None
        
        # Cache prüfen (max 24h alt)
        cache_key = f"{commodity_upper}_{contract_code}"
        if cache_key in self._cache:
            last_fetch = self._last_fetch.get(cache_key)
            if last_fetch and (datetime.now(timezone.utc) - last_fetch).total_seconds() < 86400:
                logger.debug(f"COT Cache Hit für {commodity}")
                return self._cache[cache_key]
        
        # Von CFTC API abrufen
        try:
            data = await self._fetch_from_cftc(contract_code, commodity_upper)
            if data:
                self._cache[cache_key] = data
                self._last_fetch[cache_key] = datetime.now(timezone.utc)
                await self._save_to_file_cache(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der COT-Daten für {commodity}: {e}")
            # Versuche File-Cache
            return await self._load_from_file_cache(cache_key)
    
    async def _fetch_from_cftc(self, contract_code: str, commodity: str) -> Optional[Dict]:
        """
        Ruft COT-Daten direkt von der CFTC PRE API ab.
        
        API Doku: https://publicreporting.cftc.gov/stories/s/User-s-Guide/p2fg-u73y/
        """
        # Query für die letzten 2 Wochen (für Vergleich)
        two_weeks_ago = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        
        url = f"{self.CFTC_BASE_URL}/{self.LEGACY_DATASET}.json"
        params = {
            "cftc_contract_market_code": contract_code,
            "$where": f"report_date_as_yyyy_mm_dd >= '{two_weeks_ago}'",
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": 2
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"CFTC API returned {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if not data or len(data) == 0:
                        logger.warning(f"Keine COT-Daten für Contract {contract_code}")
                        return None
                    
                    # Neuester Report
                    latest = data[0]
                    previous = data[1] if len(data) > 1 else None
                    
                    # Positionen extrahieren
                    comm_long = int(latest.get('comm_positions_long_all', 0))
                    comm_short = int(latest.get('comm_positions_short_all', 0))
                    comm_net = comm_long - comm_short
                    
                    noncomm_long = int(latest.get('noncomm_positions_long_all', 0))
                    noncomm_short = int(latest.get('noncomm_positions_short_all', 0))
                    noncomm_net = noncomm_long - noncomm_short
                    
                    # Wöchentliche Änderung
                    weekly_change = 0
                    if previous:
                        prev_noncomm_net = int(previous.get('noncomm_positions_long_all', 0)) - \
                                          int(previous.get('noncomm_positions_short_all', 0))
                        weekly_change = noncomm_net - prev_noncomm_net
                    
                    # Sentiment bestimmen
                    if noncomm_net > 10000 and weekly_change > 0:
                        sentiment = 'bullish'
                    elif noncomm_net < -10000 and weekly_change < 0:
                        sentiment = 'bearish'
                    else:
                        sentiment = 'neutral'
                    
                    result = {
                        'commercial_long': comm_long,
                        'commercial_short': comm_short,
                        'commercial_net': comm_net,
                        'noncommercial_long': noncomm_long,
                        'noncommercial_short': noncomm_short,
                        'noncommercial_net': noncomm_net,
                        'weekly_change': weekly_change,
                        'report_date': latest.get('report_date_as_yyyy_mm_dd', ''),
                        'sentiment': sentiment,
                        'contract_code': contract_code,
                        'commodity': commodity,
                        'fetched_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    logger.info(f"📊 COT-Daten für {commodity}: Net={noncomm_net:+,} | Change={weekly_change:+,} | {sentiment.upper()}")
                    return result
                    
        except asyncio.TimeoutError:
            logger.error(f"CFTC API Timeout für {contract_code}")
            return None
        except Exception as e:
            logger.error(f"CFTC API Fehler: {e}")
            return None
    
    async def _save_to_file_cache(self, cache_key: str, data: Dict):
        """Speichert Daten im File-Cache"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Cache-Speicherfehler: {e}")
    
    async def _load_from_file_cache(self, cache_key: str) -> Optional[Dict]:
        """Lädt Daten aus dem File-Cache"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"COT-Daten aus Cache geladen für {cache_key}")
                    return data
        except Exception as e:
            logger.error(f"Cache-Ladefehler: {e}")
        return None
    
    async def get_all_cot_data(self, commodities: List[str]) -> Dict[str, Dict]:
        """
        Holt COT-Daten für mehrere Commodities parallel.
        """
        tasks = [self.get_cot_data(c) for c in commodities]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            commodity: result 
            for commodity, result in zip(commodities, results)
            if result and not isinstance(result, Exception)
        }
    
    def interpret_cot(self, cot_data: Dict, signal: str) -> Dict:
        """
        Interpretiert COT-Daten für ein Trading-Signal.
        
        Returns:
            Dict mit:
            - supports_signal: bool
            - confidence_boost: float (-0.1 bis +0.1)
            - reason: str
        """
        if not cot_data:
            return {
                'supports_signal': None,
                'confidence_boost': 0,
                'reason': 'Keine COT-Daten verfügbar'
            }
        
        is_buy = signal.upper() == 'BUY'
        noncomm_net = cot_data.get('noncommercial_net', 0)
        weekly_change = cot_data.get('weekly_change', 0)
        sentiment = cot_data.get('sentiment', 'neutral')
        
        # Spekulanten-Position analysieren
        speculators_bullish = noncomm_net > 0
        momentum_bullish = weekly_change > 0
        
        if is_buy:
            if speculators_bullish and momentum_bullish:
                return {
                    'supports_signal': True,
                    'confidence_boost': 0.10,
                    'reason': f'COT bullish: Spekulanten long ({noncomm_net:+,}), Momentum positiv ({weekly_change:+,})'
                }
            elif speculators_bullish:
                return {
                    'supports_signal': True,
                    'confidence_boost': 0.05,
                    'reason': f'COT moderat bullish: Spekulanten long ({noncomm_net:+,})'
                }
            elif not speculators_bullish and not momentum_bullish:
                return {
                    'supports_signal': False,
                    'confidence_boost': -0.10,
                    'reason': f'COT bearish: Spekulanten short ({noncomm_net:+,}), Momentum negativ'
                }
            else:
                return {
                    'supports_signal': None,
                    'confidence_boost': 0,
                    'reason': 'COT gemischt'
                }
        else:  # SELL
            if not speculators_bullish and not momentum_bullish:
                return {
                    'supports_signal': True,
                    'confidence_boost': 0.10,
                    'reason': f'COT bearish: Spekulanten short ({noncomm_net:+,}), Momentum negativ ({weekly_change:+,})'
                }
            elif not speculators_bullish:
                return {
                    'supports_signal': True,
                    'confidence_boost': 0.05,
                    'reason': f'COT moderat bearish: Spekulanten short ({noncomm_net:+,})'
                }
            elif speculators_bullish and momentum_bullish:
                return {
                    'supports_signal': False,
                    'confidence_boost': -0.10,
                    'reason': f'COT bullish: Spekulanten long ({noncomm_net:+,}), Momentum positiv'
                }
            else:
                return {
                    'supports_signal': None,
                    'confidence_boost': 0,
                    'reason': 'COT gemischt'
                }


# Singleton Instance
cot_service = COTDataService()


# ═══════════════════════════════════════════════════════════════════════════
# API INFORMATIONEN FÜR DEN BENUTZER
# ═══════════════════════════════════════════════════════════════════════════

COT_API_INFO = """
═══════════════════════════════════════════════════════════════════════════════
📊 COT (Commitment of Traders) API INFORMATIONEN
═══════════════════════════════════════════════════════════════════════════════

Die COT-Daten werden KOSTENLOS von der CFTC (Commodity Futures Trading Commission) 
bereitgestellt. KEINE API-KEY erforderlich!

📌 OFFIZIELLE QUELLEN:

1. CFTC Public Reporting Environment (PRE) - EMPFOHLEN
   URL: https://publicreporting.cftc.gov/
   Doku: https://publicreporting.cftc.gov/stories/s/User-s-Guide/p2fg-u73y/
   
   ✅ Kostenlos
   ✅ Keine Registrierung
   ✅ JSON/CSV/XML Format
   ✅ Wöchentliche Updates (Freitag 15:30 EST)

2. CFTC Historical Compressed Files (Bulk Download)
   URL: https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm
   
   ✅ Historische Daten (Jahre zurück)
   ✅ ZIP-Archive

3. Python Library: cot_reports
   pip install cot_reports
   GitHub: https://github.com/NDelventhal/cot_reports
   
   ✅ Einfache Python Integration
   ✅ Pandas DataFrame Output

📌 ALTERNATIVE QUELLEN (mit API-Key):

1. Quandl/Nasdaq Data Link
   URL: https://data.nasdaq.com/
   Kostenloser Tier verfügbar
   
2. FinancialModelingPrep
   URL: https://site.financialmodelingprep.com/developer/docs/cot-symbols-list-api
   Freemium

3. Barchart
   URL: https://www.barchart.com/futures/commitment-of-traders
   Charts + API

═══════════════════════════════════════════════════════════════════════════════
AKTUELL VERWENDET: CFTC PRE API (kostenlos, keine Keys benötigt)
═══════════════════════════════════════════════════════════════════════════════
"""


async def test_cot_service():
    """Test-Funktion für den COT-Service"""
    service = COTDataService()
    
    test_commodities = ['GOLD', 'WTI_CRUDE', 'WHEAT', 'EURUSD']
    
    for commodity in test_commodities:
        print(f"\n{'='*50}")
        print(f"Testing COT for: {commodity}")
        print('='*50)
        
        data = await service.get_cot_data(commodity)
        if data:
            print(f"  Report Date: {data.get('report_date')}")
            print(f"  Commercials Net: {data.get('commercial_net'):+,}")
            print(f"  Speculators Net: {data.get('noncommercial_net'):+,}")
            print(f"  Weekly Change: {data.get('weekly_change'):+,}")
            print(f"  Sentiment: {data.get('sentiment')}")
            
            # Test Interpretation
            buy_interp = service.interpret_cot(data, 'BUY')
            print(f"\n  BUY Signal Support: {buy_interp}")
        else:
            print("  ❌ Keine Daten verfügbar")


if __name__ == "__main__":
    print(COT_API_INFO)
    asyncio.run(test_cot_service())
