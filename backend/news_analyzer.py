"""
📰 News Analyzer & Learning Module
V2.3.35: Automatische Börsen-News Erkennung und Auswertung

Features:
- Automatisches Fetching von Finanz-News
- Klassifizierung nach Asset, Impact, Richtung
- Verbindliche Regeln für Trade-Blockierung
- Lernmodul für News-Muster
"""

import asyncio
import logging
import os
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import aiohttp

logger = logging.getLogger(__name__)

# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class NewsImpact(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class NewsDirection(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNCLEAR = "unclear"

class NewsRelevance(Enum):
    UPCOMING = "upcoming"      # Bevorstehend
    CURRENT = "current"        # Aktuell
    PAST = "past"              # Vergangen

class AssetCategory(Enum):
    COMMODITIES = "commodities"
    CRYPTO = "crypto"
    FOREX = "forex"
    INDICES = "indices"
    GENERAL = "general"

# Asset-Mapping für News-Klassifizierung
ASSET_KEYWORDS = {
    AssetCategory.COMMODITIES: [
        "gold", "silver", "oil", "crude", "wti", "brent", "natural gas",
        "copper", "platinum", "palladium", "wheat", "corn", "coffee",
        "commodities", "rohstoffe", "edelmetalle", "öl", "erdgas"
    ],
    AssetCategory.CRYPTO: [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency",
        "blockchain", "sec", "etf approval", "krypto", "binance", "coinbase"
    ],
    AssetCategory.FOREX: [
        "eurusd", "eur/usd", "euro", "dollar", "fed", "ecb", "ezb",
        "interest rate", "zinsen", "inflation", "cpi", "nfp", "payroll",
        "employment", "arbeitsmarkt", "währung", "forex", "central bank"
    ],
    AssetCategory.INDICES: [
        "s&p", "dow jones", "nasdaq", "dax", "stocks", "equities", "aktien"
    ]
}

# High-Impact Events (blockieren Trades)
HIGH_IMPACT_EVENTS = [
    "fomc", "fed decision", "interest rate decision", "zinsentscheidung",
    "nfp", "non-farm payroll", "employment report", "arbeitsmarktbericht",
    "cpi", "inflation report", "inflationsdaten", "verbraucherpreise",
    "ecb decision", "ezb entscheidung", "gdp", "bip"
]

# Medium-Impact Events
MEDIUM_IMPACT_EVENTS = [
    "pmi", "retail sales", "einzelhandelsumsätze", "housing",
    "consumer confidence", "verbrauchervertrauen", "trade balance",
    "industrial production", "industrieproduktion"
]


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class NewsItem:
    """Einzelne News-Meldung"""
    id: str
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Klassifizierung
    asset_category: AssetCategory = AssetCategory.GENERAL
    related_assets: List[str] = field(default_factory=list)
    impact: NewsImpact = NewsImpact.LOW
    direction: NewsDirection = NewsDirection.NEUTRAL
    relevance: NewsRelevance = NewsRelevance.CURRENT
    
    # Analyse
    confidence_modifier: float = 0.0  # -0.5 bis +0.5
    trade_blocked: bool = False
    block_until: Optional[datetime] = None
    
    # Learning
    actual_market_reaction: Optional[str] = None
    was_accurate: Optional[bool] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "url": self.url,
            "published_at": self.published_at.isoformat(),
            "fetched_at": self.fetched_at.isoformat(),
            "asset_category": self.asset_category.value,
            "related_assets": self.related_assets,
            "impact": self.impact.value,
            "direction": self.direction.value,
            "relevance": self.relevance.value,
            "confidence_modifier": self.confidence_modifier,
            "trade_blocked": self.trade_blocked,
            "block_until": self.block_until.isoformat() if self.block_until else None
        }


@dataclass
class NewsDecision:
    """Entscheidung basierend auf News-Analyse"""
    allow_trade: bool
    reason: str
    confidence_adjustment: float = 0.0
    max_positions_multiplier: float = 1.0
    blocked_strategies: List[str] = field(default_factory=list)
    relevant_news: List[NewsItem] = field(default_factory=list)


# ============================================================================
# NEWS FETCHER
# ============================================================================

class NewsFetcher:
    """Holt News von verschiedenen Quellen"""
    
    def __init__(self):
        self.news_api_key = os.getenv("NEWS_API_KEY", "")
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_KEY", "")
        self.last_fetch = None
        self.fetch_interval_minutes = 15
        self.cached_news: List[NewsItem] = []
        
    async def fetch_news(self, force: bool = False) -> List[NewsItem]:
        """
        Holt aktuelle Finanz-News
        """
        now = datetime.now(timezone.utc)
        
        # Cache prüfen
        if not force and self.last_fetch:
            if (now - self.last_fetch).total_seconds() < self.fetch_interval_minutes * 60:
                return self.cached_news
        
        all_news = []
        
        # 1. NewsAPI (wenn Key vorhanden)
        if self.news_api_key:
            try:
                news = await self._fetch_from_newsapi()
                all_news.extend(news)
            except Exception as e:
                logger.warning(f"NewsAPI fetch failed: {e}")
        
        # 2. Alpha Vantage News (wenn Key vorhanden)
        if self.alpha_vantage_key:
            try:
                news = await self._fetch_from_alpha_vantage()
                all_news.extend(news)
            except Exception as e:
                logger.warning(f"Alpha Vantage fetch failed: {e}")
        
        # 3. Fallback: Simulierte wichtige Events (Economic Calendar)
        try:
            news = await self._get_economic_calendar()
            all_news.extend(news)
        except Exception as e:
            logger.warning(f"Economic calendar failed: {e}")
        
        self.cached_news = all_news
        self.last_fetch = now
        
        logger.info(f"📰 Fetched {len(all_news)} news items")
        return all_news
    
    async def _fetch_from_newsapi(self) -> List[NewsItem]:
        """Fetch von NewsAPI.org"""
        news_items = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Business/Finance News
                url = "https://newsapi.org/v2/top-headlines"
                params = {
                    "category": "business",
                    "language": "en",
                    "pageSize": 20,
                    "apiKey": self.news_api_key
                }
                
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for article in data.get("articles", []):
                            news_id = hashlib.md5(article.get("url", "").encode()).hexdigest()[:12]
                            
                            published = article.get("publishedAt", "")
                            if published:
                                try:
                                    pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                                except:
                                    pub_dt = datetime.now(timezone.utc)
                            else:
                                pub_dt = datetime.now(timezone.utc)
                            
                            news_items.append(NewsItem(
                                id=news_id,
                                title=article.get("title", ""),
                                summary=article.get("description", ""),
                                source=article.get("source", {}).get("name", "NewsAPI"),
                                url=article.get("url", ""),
                                published_at=pub_dt
                            ))
        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
        
        return news_items
    
    async def _fetch_from_alpha_vantage(self) -> List[NewsItem]:
        """Fetch von Alpha Vantage News Sentiment"""
        news_items = []
        
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://www.alphavantage.co/query"
                params = {
                    "function": "NEWS_SENTIMENT",
                    "topics": "finance,economy,forex",
                    "apikey": self.alpha_vantage_key
                }
                
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for article in data.get("feed", [])[:20]:
                            news_id = hashlib.md5(article.get("url", "").encode()).hexdigest()[:12]
                            
                            # Parse sentiment
                            sentiment = article.get("overall_sentiment_label", "Neutral")
                            direction = NewsDirection.NEUTRAL
                            if "Bullish" in sentiment:
                                direction = NewsDirection.BULLISH
                            elif "Bearish" in sentiment:
                                direction = NewsDirection.BEARISH
                            
                            published = article.get("time_published", "")
                            try:
                                pub_dt = datetime.strptime(published, "%Y%m%dT%H%M%S")
                                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                            except:
                                pub_dt = datetime.now(timezone.utc)
                            
                            item = NewsItem(
                                id=news_id,
                                title=article.get("title", ""),
                                summary=article.get("summary", ""),
                                source=article.get("source", "Alpha Vantage"),
                                url=article.get("url", ""),
                                published_at=pub_dt,
                                direction=direction
                            )
                            news_items.append(item)
        except Exception as e:
            logger.error(f"Alpha Vantage error: {e}")
        
        return news_items
    
    async def _get_economic_calendar(self) -> List[NewsItem]:
        """
        Simulierter Economic Calendar für wichtige Events
        In Produktion: Ersetzen durch echte API (Investing.com, ForexFactory, etc.)
        """
        now = datetime.now(timezone.utc)
        events = []
        
        # Bekannte wiederkehrende Events (UTC Zeiten)
        # Diese sollten in Produktion von einer echten API kommen
        weekly_events = [
            # Mittwoch: FOMC Minutes / Fed
            {"day": 2, "hour": 18, "name": "FOMC Meeting Minutes", "impact": NewsImpact.HIGH},
            # Freitag: NFP (erster Freitag des Monats)
            {"day": 4, "hour": 12, "name": "US Non-Farm Payroll", "impact": NewsImpact.HIGH},
            # Donnerstag: EZB
            {"day": 3, "hour": 11, "name": "ECB Interest Rate Decision", "impact": NewsImpact.HIGH},
        ]
        
        # Prüfe ob heute ein Event ansteht
        for event in weekly_events:
            if now.weekday() == event["day"]:
                event_time = now.replace(hour=event["hour"], minute=30, second=0, microsecond=0)
                
                # Relevanz bestimmen
                time_diff = (event_time - now).total_seconds() / 60  # in Minuten
                
                if -90 <= time_diff <= 60:  # 60 Min vorher bis 90 Min nachher
                    relevance = NewsRelevance.CURRENT
                elif time_diff > 60:
                    relevance = NewsRelevance.UPCOMING
                else:
                    relevance = NewsRelevance.PAST
                
                if relevance != NewsRelevance.PAST:
                    events.append(NewsItem(
                        id=f"calendar_{event['name'].lower().replace(' ', '_')}_{now.strftime('%Y%m%d')}",
                        title=event["name"],
                        summary=f"Scheduled economic event: {event['name']}",
                        source="Economic Calendar",
                        url="",
                        published_at=event_time,
                        impact=event["impact"],
                        relevance=relevance,
                        asset_category=AssetCategory.FOREX,
                        related_assets=["EURUSD"],
                        trade_blocked=event["impact"] == NewsImpact.HIGH
                    ))
        
        return events


# ============================================================================
# NEWS CLASSIFIER
# ============================================================================

class NewsClassifier:
    """Klassifiziert News nach Asset, Impact, Richtung"""
    
    def classify(self, news: NewsItem) -> NewsItem:
        """Klassifiziert eine einzelne News"""
        text = f"{news.title} {news.summary}".lower()
        
        # 1. Asset-Kategorie erkennen
        news.asset_category = self._detect_asset_category(text)
        news.related_assets = self._detect_related_assets(text)
        
        # 2. Impact erkennen
        news.impact = self._detect_impact(text)
        
        # 3. Richtung erkennen (wenn noch nicht gesetzt)
        if news.direction == NewsDirection.NEUTRAL:
            news.direction = self._detect_direction(text)
        
        # 4. Trade-Blockierung berechnen
        news.trade_blocked, news.block_until = self._calculate_block(news)
        
        # 5. Konfidenz-Modifier berechnen
        news.confidence_modifier = self._calculate_confidence_modifier(news)
        
        return news
    
    def _detect_asset_category(self, text: str) -> AssetCategory:
        """Erkennt die Asset-Kategorie"""
        scores = {cat: 0 for cat in AssetCategory}
        
        for category, keywords in ASSET_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[category] += 1
        
        # Höchsten Score finden
        max_cat = max(scores, key=scores.get)
        if scores[max_cat] > 0:
            return max_cat
        return AssetCategory.GENERAL
    
    def _detect_related_assets(self, text: str) -> List[str]:
        """Erkennt konkrete Assets"""
        assets = []
        
        asset_map = {
            "gold": "GOLD", "silver": "SILVER", "silber": "SILVER",
            "oil": "WTI_CRUDE", "crude": "WTI_CRUDE", "öl": "WTI_CRUDE",
            "brent": "BRENT_CRUDE", "wti": "WTI_CRUDE",
            "natural gas": "NATURAL_GAS", "erdgas": "NATURAL_GAS",
            "bitcoin": "BITCOIN", "btc": "BITCOIN",
            "euro": "EURUSD", "eur/usd": "EURUSD", "eurusd": "EURUSD",
            "copper": "COPPER", "kupfer": "COPPER",
            "platinum": "PLATINUM", "platin": "PLATINUM",
            "palladium": "PALLADIUM",
            "wheat": "WHEAT", "weizen": "WHEAT",
            "coffee": "COFFEE", "kaffee": "COFFEE"
        }
        
        for keyword, asset in asset_map.items():
            if keyword in text and asset not in assets:
                assets.append(asset)
        
        return assets
    
    def _detect_impact(self, text: str) -> NewsImpact:
        """Erkennt den Impact-Level"""
        # High-Impact Keywords
        for keyword in HIGH_IMPACT_EVENTS:
            if keyword in text:
                return NewsImpact.HIGH
        
        # Medium-Impact Keywords
        for keyword in MEDIUM_IMPACT_EVENTS:
            if keyword in text:
                return NewsImpact.MEDIUM
        
        return NewsImpact.LOW
    
    def _detect_direction(self, text: str) -> NewsDirection:
        """Erkennt die Marktrichtung"""
        bullish_words = [
            "surge", "rally", "bullish", "gain", "rise", "up", "growth",
            "strong", "optimism", "recovery", "steigt", "anstieg", "wachstum"
        ]
        bearish_words = [
            "drop", "fall", "bearish", "decline", "down", "weak", "concern",
            "fear", "recession", "crash", "fällt", "rückgang", "verlust"
        ]
        
        bullish_count = sum(1 for w in bullish_words if w in text)
        bearish_count = sum(1 for w in bearish_words if w in text)
        
        if bullish_count > bearish_count + 1:
            return NewsDirection.BULLISH
        elif bearish_count > bullish_count + 1:
            return NewsDirection.BEARISH
        elif bullish_count > 0 or bearish_count > 0:
            return NewsDirection.UNCLEAR
        return NewsDirection.NEUTRAL
    
    def _calculate_block(self, news: NewsItem) -> Tuple[bool, Optional[datetime]]:
        """Berechnet ob Trades blockiert werden sollen"""
        now = datetime.now(timezone.utc)
        
        if news.impact == NewsImpact.HIGH:
            # High-Impact: 30-60 Min vorher, 30-90 Min nachher blockieren
            if news.relevance == NewsRelevance.UPCOMING:
                return True, news.published_at + timedelta(minutes=90)
            elif news.relevance == NewsRelevance.CURRENT:
                return True, now + timedelta(minutes=60)
        
        return False, None
    
    def _calculate_confidence_modifier(self, news: NewsItem) -> float:
        """Berechnet den Konfidenz-Modifier"""
        modifier = 0.0
        
        if news.impact == NewsImpact.HIGH:
            modifier = -0.3 if news.direction == NewsDirection.UNCLEAR else -0.1
        elif news.impact == NewsImpact.MEDIUM:
            modifier = -0.1
        
        # Richtung verstärkt oder schwächt
        if news.direction == NewsDirection.BULLISH:
            modifier += 0.1
        elif news.direction == NewsDirection.BEARISH:
            modifier -= 0.1
        
        return max(-0.5, min(0.5, modifier))


# ============================================================================
# NEWS DECISION ENGINE
# ============================================================================

class NewsDecisionEngine:
    """Trifft Entscheidungen basierend auf News"""
    
    def __init__(self):
        self.fetcher = NewsFetcher()
        self.classifier = NewsClassifier()
        self.learning_module = NewsLearningModule()
        self.decision_log: List[Dict] = []
    
    async def get_trading_decision(
        self, 
        asset: str, 
        strategy: str,
        technical_signal: str
    ) -> NewsDecision:
        """
        Gibt eine Entscheidung basierend auf News zurück.
        
        WICHTIG: News blockieren nur, lösen NIEMALS selbst Trades aus!
        """
        # 1. News holen und klassifizieren
        raw_news = await self.fetcher.fetch_news()
        classified_news = [self.classifier.classify(n) for n in raw_news]
        
        # 2. Relevante News für dieses Asset filtern
        relevant_news = self._filter_relevant_news(classified_news, asset)
        
        # 3. Entscheidung treffen
        decision = self._make_decision(relevant_news, asset, strategy, technical_signal)
        
        # 4. Loggen
        self._log_decision(decision, asset, strategy, technical_signal)
        
        return decision
    
    def _filter_relevant_news(self, news: List[NewsItem], asset: str) -> List[NewsItem]:
        """Filtert News die für dieses Asset relevant sind"""
        relevant = []
        
        asset_category_map = {
            "GOLD": AssetCategory.COMMODITIES,
            "SILVER": AssetCategory.COMMODITIES,
            "PLATINUM": AssetCategory.COMMODITIES,
            "PALLADIUM": AssetCategory.COMMODITIES,
            "WTI_CRUDE": AssetCategory.COMMODITIES,
            "BRENT_CRUDE": AssetCategory.COMMODITIES,
            "NATURAL_GAS": AssetCategory.COMMODITIES,
            "COPPER": AssetCategory.COMMODITIES,
            "BITCOIN": AssetCategory.CRYPTO,
            "EURUSD": AssetCategory.FOREX,
        }
        
        asset_cat = asset_category_map.get(asset, AssetCategory.GENERAL)
        
        for item in news:
            # Direkt erwähnt
            if asset in item.related_assets:
                relevant.append(item)
            # Gleiche Kategorie
            elif item.asset_category == asset_cat:
                relevant.append(item)
            # High-Impact Events betreffen alle
            elif item.impact == NewsImpact.HIGH and item.asset_category == AssetCategory.FOREX:
                relevant.append(item)
        
        return relevant
    
    def _make_decision(
        self, 
        news: List[NewsItem], 
        asset: str, 
        strategy: str,
        technical_signal: str
    ) -> NewsDecision:
        """Macht die finale Entscheidung"""
        
        blocked_strategies = []
        total_confidence_adj = 0.0
        max_positions_mult = 1.0
        block_reason = None
        
        for item in news:
            # High-Impact: Blockiere bestimmte Strategien
            if item.impact == NewsImpact.HIGH:
                if item.trade_blocked:
                    blocked_strategies.extend(["scalping", "grid", "breakout"])
                    block_reason = f"High-Impact News: {item.title}"
                    max_positions_mult = min(max_positions_mult, 0.3)
            
            # Medium-Impact: Erhöhe Konfidenz-Anforderung
            elif item.impact == NewsImpact.MEDIUM:
                total_confidence_adj -= 0.1
                max_positions_mult = min(max_positions_mult, 0.7)
            
            # Konfidenz-Modifier addieren
            total_confidence_adj += item.confidence_modifier
            
            # News widerspricht technischem Signal?
            if technical_signal == "BUY" and item.direction == NewsDirection.BEARISH:
                total_confidence_adj -= 0.15
            elif technical_signal == "SELL" and item.direction == NewsDirection.BULLISH:
                total_confidence_adj -= 0.15
        
        # Strategie blockiert?
        strategy_lower = strategy.lower().replace("_trading", "")
        if strategy_lower in blocked_strategies:
            return NewsDecision(
                allow_trade=False,
                reason=block_reason or f"Strategie {strategy} durch News blockiert",
                confidence_adjustment=total_confidence_adj,
                max_positions_multiplier=max_positions_mult,
                blocked_strategies=blocked_strategies,
                relevant_news=news
            )
        
        # Erlaubt
        return NewsDecision(
            allow_trade=True,
            reason="News erlauben Trade" if news else "Keine relevanten News",
            confidence_adjustment=total_confidence_adj,
            max_positions_multiplier=max_positions_mult,
            blocked_strategies=blocked_strategies,
            relevant_news=news
        )
    
    def _log_decision(self, decision: NewsDecision, asset: str, strategy: str, signal: str):
        """Loggt die Entscheidung für Transparenz"""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "asset": asset,
            "strategy": strategy,
            "signal": signal,
            "allow_trade": decision.allow_trade,
            "reason": decision.reason,
            "confidence_adjustment": decision.confidence_adjustment,
            "blocked_strategies": decision.blocked_strategies,
            "news_count": len(decision.relevant_news),
            "news_titles": [n.title for n in decision.relevant_news[:3]]
        }
        
        self.decision_log.append(log_entry)
        
        # Log beschränken
        if len(self.decision_log) > 1000:
            self.decision_log = self.decision_log[-500:]
        
        logger.info(f"📰 News Decision for {asset}/{strategy}: {decision.reason}")
    
    def get_decision_log(self) -> List[Dict]:
        """Gibt das Decision-Log für UI zurück"""
        return self.decision_log[-100:]  # Letzte 100 Einträge


# ============================================================================
# NEWS LEARNING MODULE
# ============================================================================

class NewsLearningModule:
    """
    Lernmodul für News-Muster
    
    DARF:
    - Konfidenz-Gewichtung anpassen
    - News-Impact-Klassen feinjustieren
    - Regime-Erkennung verbessern
    
    DARF NICHT:
    - SL, TP, Risiko oder Haltezeit verändern
    - Neue Strategien erfinden
    - Trades außerhalb der Regel-Logik ausführen
    """
    
    def __init__(self):
        self.patterns: List[Dict] = []
        self.accuracy_stats: Dict[str, Dict] = {}
        self.load_patterns()
    
    def load_patterns(self):
        """Lädt gelernte Muster aus Datei"""
        try:
            pattern_file = "/app/backend/data/news_patterns.json"
            if os.path.exists(pattern_file):
                with open(pattern_file, "r") as f:
                    data = json.load(f)
                    self.patterns = data.get("patterns", [])
                    self.accuracy_stats = data.get("accuracy_stats", {})
                    logger.info(f"📚 Loaded {len(self.patterns)} news patterns")
        except Exception as e:
            logger.warning(f"Could not load patterns: {e}")
    
    def save_patterns(self):
        """Speichert gelernte Muster"""
        try:
            os.makedirs("/app/backend/data", exist_ok=True)
            pattern_file = "/app/backend/data/news_patterns.json"
            with open(pattern_file, "w") as f:
                json.dump({
                    "patterns": self.patterns,
                    "accuracy_stats": self.accuracy_stats,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
            logger.info(f"💾 Saved {len(self.patterns)} news patterns")
        except Exception as e:
            logger.error(f"Could not save patterns: {e}")
    
    def record_trade_result(
        self,
        news_item: NewsItem,
        strategy: str,
        trade_result: str,  # "profit", "loss", "neutral"
        market_reaction: str  # "as_expected", "opposite", "no_reaction"
    ):
        """
        Speichert das Ergebnis eines Trades nach News
        """
        pattern = {
            "news_type": news_item.impact.value,
            "news_direction": news_item.direction.value,
            "asset_category": news_item.asset_category.value,
            "strategy": strategy,
            "trade_result": trade_result,
            "market_reaction": market_reaction,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self.patterns.append(pattern)
        
        # Stats aktualisieren
        key = f"{news_item.impact.value}_{news_item.direction.value}"
        if key not in self.accuracy_stats:
            self.accuracy_stats[key] = {"correct": 0, "total": 0}
        
        self.accuracy_stats[key]["total"] += 1
        if market_reaction == "as_expected":
            self.accuracy_stats[key]["correct"] += 1
        
        # Periodisch speichern
        if len(self.patterns) % 10 == 0:
            self.save_patterns()
    
    def get_confidence_adjustment(self, news_item: NewsItem) -> float:
        """
        Gibt eine gelernte Konfidenz-Anpassung basierend auf historischen Mustern
        """
        key = f"{news_item.impact.value}_{news_item.direction.value}"
        
        if key in self.accuracy_stats:
            stats = self.accuracy_stats[key]
            if stats["total"] >= 10:  # Mindestens 10 Samples
                accuracy = stats["correct"] / stats["total"]
                
                # Wenn Vorhersagen oft falsch waren, reduziere Konfidenz
                if accuracy < 0.4:
                    return -0.1
                elif accuracy > 0.7:
                    return 0.1
        
        return 0.0
    
    def detect_overreaction_pattern(self, news_item: NewsItem) -> bool:
        """
        Erkennt ob ähnliche News in der Vergangenheit zu Overreactions führten
        """
        similar_patterns = [
            p for p in self.patterns
            if p["news_type"] == news_item.impact.value
            and p["news_direction"] == news_item.direction.value
        ]
        
        if len(similar_patterns) >= 5:
            overreaction_count = sum(
                1 for p in similar_patterns 
                if p["market_reaction"] == "opposite"
            )
            
            return overreaction_count / len(similar_patterns) > 0.5
        
        return False


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Singleton Instance
_news_engine: Optional[NewsDecisionEngine] = None

def get_news_engine() -> NewsDecisionEngine:
    """Gibt die globale News Engine Instanz zurück"""
    global _news_engine
    if _news_engine is None:
        _news_engine = NewsDecisionEngine()
    return _news_engine


# ============================================================================
# API FUNCTIONS (für server.py)
# ============================================================================

async def check_news_for_trade(
    asset: str,
    strategy: str,
    technical_signal: str
) -> NewsDecision:
    """
    Hauptfunktion zur News-Prüfung vor einem Trade.
    Wird von der Trading-Logik aufgerufen.
    """
    engine = get_news_engine()
    return await engine.get_trading_decision(asset, strategy, technical_signal)


async def get_current_news() -> List[Dict]:
    """Gibt aktuelle News für UI zurück"""
    engine = get_news_engine()
    raw_news = await engine.fetcher.fetch_news()
    classified = [engine.classifier.classify(n) for n in raw_news]
    return [n.to_dict() for n in classified]


def get_news_decision_log() -> List[Dict]:
    """Gibt das Decision-Log für UI zurück"""
    engine = get_news_engine()
    return engine.get_decision_log()


# Export
__all__ = [
    'NewsItem',
    'NewsDecision',
    'NewsImpact',
    'NewsDirection',
    'check_news_for_trade',
    'get_current_news',
    'get_news_decision_log',
    'get_news_engine'
]
