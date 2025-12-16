"""
Advanced Market Analysis Module
Technische Indikatoren, News-Integration, Multi-Strategie-Analyse
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
import os
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """Erweiterte Marktanalyse mit technischen Indikatoren, News, Economic Data und mehr"""
    
    def __init__(self):
        self.news_api_key = os.getenv('NEWS_API_KEY', '')
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_KEY', '')
        self.finnhub_key = os.getenv('FINNHUB_API_KEY', '')
        
        # Cache für API-Calls (Rate Limiting)
        self.news_cache = {}
        self.economic_cache = {}
        self.sentiment_cache = {}
    
    async def fetch_news_sentiment(self, commodity: str) -> Dict:
        """Hole News und analysiere Sentiment - MULTI-SOURCE"""
        try:
            # Cache Check (5 Minuten)
            cache_key = f"news_{commodity}"
            if cache_key in self.news_cache:
                cache_time, cache_data = self.news_cache[cache_key]
                if (datetime.now() - cache_time).seconds < 300:
                    return cache_data
            
            # Priorität: Yahoo Finance > Finnhub > NewsAPI > Alpha Vantage
            result = None
            
            # 0. Yahoo Finance (IMMER verfügbar, keine API-Key nötig!)
            result = await self._fetch_yahoo_finance_news(commodity)
            if result and result.get('articles', 0) > 0:
                self.news_cache[cache_key] = (datetime.now(), result)
                return result
            
            # 1. Finnhub (falls konfiguriert)
            if self.finnhub_key:
                result = await self._fetch_finnhub_news(commodity)
                if result and result.get('articles', 0) > 0:
                    self.news_cache[cache_key] = (datetime.now(), result)
                    return result
            
            # 2. NewsAPI (falls konfiguriert)
            if self.news_api_key:
                result = await self._fetch_newsapi(commodity)
                if result and result.get('articles', 0) > 0:
                    self.news_cache[cache_key] = (datetime.now(), result)
                    return result
            
            # 3. Alpha Vantage News Sentiment
            if self.alpha_vantage_key:
                result = await self._fetch_alpha_vantage_sentiment(commodity)
                if result and result.get('articles', 0) > 0:
                    self.news_cache[cache_key] = (datetime.now(), result)
                    return result
            
            # Fallback: Neutral
            logger.info(f"Keine News-Daten für {commodity} verfügbar")
            return {"sentiment": "neutral", "score": 0, "articles": 0, "source": "none"}
            
        except Exception as e:
            logger.error(f"News fetch error für {commodity}: {e}")
            return {"sentiment": "neutral", "score": 0, "articles": 0, "source": "error"}
    
    async def _fetch_yahoo_finance_news(self, commodity: str) -> Dict:
        """Hole News von Google News RSS (KOSTENLOS, keine Limits!)"""
        try:
            import feedparser
            
            # Map commodity zu Suchbegriffen
            search_terms = {
                "GOLD": "gold prices",
                "SILVER": "silver prices",
                "WTI_CRUDE": "crude oil prices",
                "BRENT_CRUDE": "brent oil prices",
                "PLATINUM": "platinum prices",
                "PALLADIUM": "palladium prices",
                "NATURAL_GAS": "natural gas prices",
                "WHEAT": "wheat prices",
                "CORN": "corn prices",
                "SOYBEANS": "soybean prices",
                "SUGAR": "sugar prices",
                "COFFEE": "coffee prices",
                "COTTON": "cotton prices",
                "COCOA": "cocoa prices"
            }
            
            search_term = search_terms.get(commodity, commodity.lower())
            
            # Google News RSS Feed
            url = f"https://news.google.com/rss/search?q={search_term.replace(' ', '%20')}&hl=en-US&gl=US&ceid=US:en"
            
            # Parse RSS Feed
            feed = feedparser.parse(url)
            
            if not feed.entries or len(feed.entries) == 0:
                return {"sentiment": "neutral", "score": 0, "articles": 0, "source": "google_no_news"}
            
            # Sentiment-Analyse - ERWEITERT mit Event-Wörtern
            positive_words = ['surge', 'rally', 'rise', 'gain', 'up', 'bullish', 'high', 'jump', 'climb', 'strong', 'boost', 'soar', 'higher', 'demand', 'shortage', 'disruption', 'cut', 'opec']
            negative_words = ['fall', 'drop', 'decline', 'loss', 'down', 'bearish', 'low', 'plunge', 'weak', 'crash', 'slump', 'tumble', 'lower', 'glut', 'oversupply', 'surplus', 'recession']
            
            # SPEZIELLE EVENT-WÖRTER (starkes Gewicht)
            event_words_bullish = ['explosion', 'attack', 'war', 'conflict', 'strike', 'hurricane', 'disaster', 'sanctions']  # Für Rohstoffe oft bullish
            event_words_bearish = ['peace', 'deal', 'agreement', 'recovery', 'resolution']
            
            sentiment_score = 0
            article_count = 0
            
            for entry in feed.entries[:15]:  # Top 15 News
                title = entry.get('title', '').lower()
                summary = entry.get('summary', '').lower()
                text = title + " " + summary
                
                article_count += 1
                
                # Standard-Wörter (Gewicht: 1)
                for word in positive_words:
                    if word in text:
                        sentiment_score += 1
                for word in negative_words:
                    if word in text:
                        sentiment_score -= 1
                
                # Event-Wörter (Gewicht: 2 - stärkerer Einfluss!)
                for word in event_words_bullish:
                    if word in text:
                        sentiment_score += 2
                        logger.info(f"🚨 EVENT erkannt: '{word}' in '{title[:80]}...'")
                for word in event_words_bearish:
                    if word in text:
                        sentiment_score -= 2
                        logger.info(f"🚨 EVENT erkannt: '{word}' in '{title[:80]}...'")
            
            # Normalisiere Score
            normalized_score = sentiment_score / max(article_count, 1) if article_count > 0 else 0
            sentiment = "bullish" if normalized_score > 0.3 else "bearish" if normalized_score < -0.3 else "neutral"
            
            logger.info(f"📰 Google News für {commodity}: {article_count} Artikel, Sentiment: {sentiment} ({normalized_score:.2f})")
            
            return {
                "sentiment": sentiment,
                "score": normalized_score,
                "articles": article_count,
                "source": "google_news"
            }
            
        except Exception as e:
            logger.error(f"Google News error für {commodity}: {e}")
            return {"sentiment": "neutral", "score": 0, "articles": 0, "source": "google_error"}
    
    async def _fetch_finnhub_news(self, commodity: str) -> Dict:
        """Hole News von Finnhub.io (kostenlos, 60 calls/min)"""
        try:
            # Verwende "general" Kategorie für alle Commodities (breiter)
            category = "general"
            
            # Finnhub Market News API
            url = f"https://finnhub.io/api/v1/news?category={category}&token={self.finnhub_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        articles = await response.json()
                        
                        if not articles:
                            return {"sentiment": "neutral", "score": 0, "articles": 0, "source": "finnhub"}
                        
                        # Sentiment-Analyse basierend auf Headlines
                        positive_words = ['surge', 'rally', 'rise', 'gain', 'up', 'bullish', 'high', 'jump', 'climb', 'strong', 'boost', 'soar']
                        negative_words = ['fall', 'drop', 'decline', 'loss', 'down', 'bearish', 'low', 'plunge', 'weak', 'crash', 'slump', 'tumble']
                        
                        sentiment_score = 0
                        relevant_count = 0
                        
                        for article in articles[:20]:  # Top 20
                            headline = article.get('headline', '').lower()
                            summary = article.get('summary', '').lower()
                            text = headline + " " + summary
                            
                            # Prüfe ob relevant für Commodity
                            if commodity.lower().replace('_', ' ') in text or any(word in text for word in ['commodit', 'metal', 'oil', 'gold', 'silver']):
                                relevant_count += 1
                                for word in positive_words:
                                    if word in text:
                                        sentiment_score += 1
                                for word in negative_words:
                                    if word in text:
                                        sentiment_score -= 1
                        
                        if relevant_count == 0:
                            return {"sentiment": "neutral", "score": 0, "articles": 0, "source": "finnhub"}
                        
                        # Normalisiere Score
                        normalized_score = sentiment_score / max(relevant_count, 1)
                        sentiment = "bullish" if normalized_score > 0.3 else "bearish" if normalized_score < -0.3 else "neutral"
                        
                        logger.info(f"📰 Finnhub News für {commodity}: {relevant_count} relevante Artikel, Sentiment: {sentiment} ({normalized_score:.2f})")
                        
                        return {
                            "sentiment": sentiment,
                            "score": normalized_score,
                            "articles": relevant_count,
                            "source": "finnhub"
                        }
                    else:
                        logger.warning(f"Finnhub returned status {response.status}")
                        return {"sentiment": "neutral", "score": 0, "articles": 0, "source": "finnhub_error"}
                        
        except Exception as e:
            logger.error(f"Finnhub error: {e}")
            return {"sentiment": "neutral", "score": 0, "articles": 0, "source": "finnhub_error"}
    
    async def _fetch_alpha_vantage_sentiment(self, commodity: str) -> Dict:
        """Hole News Sentiment von Alpha Vantage"""
        try:
            # Map commodity to tickers/topics
            ticker_map = {
                "GOLD": "GOLD",
                "SILVER": "SILVER",
                "WTI_CRUDE": "USO",  # US Oil Fund
                "BRENT_CRUDE": "BNO",  # Brent Oil ETF
                "WHEAT": "WEAT",
                "CORN": "CORN"
            }
            
            ticker = ticker_map.get(commodity, commodity)
            
            url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={self.alpha_vantage_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        feed = data.get('feed', [])
                        if not feed:
                            return {"sentiment": "neutral", "score": 0, "articles": 0, "source": "alphavantage"}
                        
                        # Alpha Vantage hat bereits Sentiment-Scores
                        total_sentiment = 0
                        count = 0
                        
                        for article in feed[:20]:
                            ticker_sentiment = article.get('ticker_sentiment', [])
                            for ts in ticker_sentiment:
                                if ts.get('ticker') == ticker:
                                    sentiment_score = float(ts.get('ticker_sentiment_score', 0))
                                    total_sentiment += sentiment_score
                                    count += 1
                        
                        if count == 0:
                            return {"sentiment": "neutral", "score": 0, "articles": 0, "source": "alphavantage"}
                        
                        avg_sentiment = total_sentiment / count
                        sentiment = "bullish" if avg_sentiment > 0.15 else "bearish" if avg_sentiment < -0.15 else "neutral"
                        
                        logger.info(f"📰 Alpha Vantage Sentiment für {commodity}: {count} Artikel, Sentiment: {sentiment} ({avg_sentiment:.2f})")
                        
                        return {
                            "sentiment": sentiment,
                            "score": avg_sentiment,
                            "articles": count,
                            "source": "alphavantage"
                        }
                    else:
                        return {"sentiment": "neutral", "score": 0, "articles": 0, "source": "alphavantage_error"}
                        
        except Exception as e:
            logger.error(f"Alpha Vantage error: {e}")
            return {"sentiment": "neutral", "score": 0, "articles": 0, "source": "alphavantage_error"}
    
    async def _fetch_newsapi(self, commodity: str) -> Dict:
        """Hole News von NewsAPI.org"""
        try:
            # Map commodity to search terms
            search_terms = {
                "GOLD": "gold prices OR gold market",
                "SILVER": "silver prices OR silver market",
                "WTI_CRUDE": "oil prices OR crude oil OR WTI",
                "BRENT_CRUDE": "brent oil OR oil prices",
                "PLATINUM": "platinum prices",
                "PALLADIUM": "palladium prices",
                "WHEAT": "wheat prices OR grain market",
                "CORN": "corn prices OR grain market",
                "SOYBEANS": "soybean prices",
                "COFFEE": "coffee prices"
            }
            
            query = search_terms.get(commodity, commodity)
            url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=20"
            
            headers = {"X-Api-Key": self.news_api_key}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        articles = data.get('articles', [])
                        
                        # Einfache Sentiment-Analyse basierend auf Keywords
                        positive_words = ['surge', 'rally', 'rise', 'gain', 'up', 'bullish', 'high', 'jump', 'climb', 'strong']
                        negative_words = ['fall', 'drop', 'decline', 'loss', 'down', 'bearish', 'low', 'plunge', 'weak', 'crash']
                        
                        sentiment_score = 0
                        for article in articles[:10]:  # Nur die neuesten 10
                            title = article.get('title', '').lower()
                            description = article.get('description', '').lower()
                            text = title + " " + description
                            
                            for word in positive_words:
                                if word in text:
                                    sentiment_score += 1
                            for word in negative_words:
                                if word in text:
                                    sentiment_score -= 1
                        
                        # Normalisiere Score
                        if len(articles) > 0:
                            normalized_score = sentiment_score / len(articles[:10])
                        else:
                            normalized_score = 0
                        
                        sentiment = "bullish" if normalized_score > 0.3 else "bearish" if normalized_score < -0.3 else "neutral"
                        
                        logger.info(f"📰 News für {commodity}: {len(articles)} Artikel, Sentiment: {sentiment} ({normalized_score:.2f})")
                        
                        return {
                            "sentiment": sentiment,
                            "score": normalized_score,
                            "articles": len(articles)
                        }
                    else:
                        logger.warning(f"NewsAPI returned status {response.status}")
                        return {"sentiment": "neutral", "score": 0, "articles": 0}
                        
        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
            return {"sentiment": "neutral", "score": 0, "articles": 0}
    
    def calculate_technical_indicators(self, price_history: List[Dict]) -> Dict:
        """Berechne alle technischen Indikatoren"""
        try:
            if not price_history or len(price_history) < 50:
                logger.warning("Nicht genug Preisdaten für Indikatoren")
                return self._default_indicators()
            
            # Konvertiere zu DataFrame
            df = pd.DataFrame(price_history)
            
            # Stelle sicher, dass wir die richtigen Spalten haben
            if 'close' not in df.columns and 'price' in df.columns:
                df['close'] = df['price']
            if 'high' not in df.columns:
                df['high'] = df['close']
            if 'low' not in df.columns:
                df['low'] = df['close']
            
            close = df['close']
            high = df['high']
            low = df['low']
            
            # RSI (14 periods)
            rsi_indicator = RSIIndicator(close=close, window=14)
            rsi = rsi_indicator.rsi().iloc[-1]
            
            # MACD
            macd_indicator = MACD(close=close)
            macd = macd_indicator.macd().iloc[-1]
            macd_signal = macd_indicator.macd_signal().iloc[-1]
            macd_diff = macd_indicator.macd_diff().iloc[-1]
            
            # Moving Averages
            sma_20 = SMAIndicator(close=close, window=20).sma_indicator().iloc[-1]
            sma_50 = SMAIndicator(close=close, window=50).sma_indicator().iloc[-1]
            ema_12 = EMAIndicator(close=close, window=12).ema_indicator().iloc[-1]
            ema_26 = EMAIndicator(close=close, window=26).ema_indicator().iloc[-1]
            
            # Bollinger Bands
            bb_indicator = BollingerBands(close=close, window=20, window_dev=2)
            bb_upper = bb_indicator.bollinger_hband().iloc[-1]
            bb_middle = bb_indicator.bollinger_mavg().iloc[-1]
            bb_lower = bb_indicator.bollinger_lband().iloc[-1]
            
            # ATR (Average True Range) - Volatilität
            atr_indicator = AverageTrueRange(high=high, low=low, close=close, window=14)
            atr = atr_indicator.average_true_range().iloc[-1]
            
            # Stochastic Oscillator
            stoch_indicator = StochasticOscillator(high=high, low=low, close=close)
            stoch_k = stoch_indicator.stoch().iloc[-1]
            stoch_d = stoch_indicator.stoch_signal().iloc[-1]
            
            current_price = close.iloc[-1]
            
            return {
                "rsi": float(rsi) if not np.isnan(rsi) else 50.0,
                "macd": float(macd) if not np.isnan(macd) else 0.0,
                "macd_signal": float(macd_signal) if not np.isnan(macd_signal) else 0.0,
                "macd_diff": float(macd_diff) if not np.isnan(macd_diff) else 0.0,
                "sma_20": float(sma_20) if not np.isnan(sma_20) else current_price,
                "sma_50": float(sma_50) if not np.isnan(sma_50) else current_price,
                "ema_12": float(ema_12) if not np.isnan(ema_12) else current_price,
                "ema_26": float(ema_26) if not np.isnan(ema_26) else current_price,
                "bb_upper": float(bb_upper) if not np.isnan(bb_upper) else current_price * 1.02,
                "bb_middle": float(bb_middle) if not np.isnan(bb_middle) else current_price,
                "bb_lower": float(bb_lower) if not np.isnan(bb_lower) else current_price * 0.98,
                "atr": float(atr) if not np.isnan(atr) else current_price * 0.02,
                "stoch_k": float(stoch_k) if not np.isnan(stoch_k) else 50.0,
                "stoch_d": float(stoch_d) if not np.isnan(stoch_d) else 50.0,
                "current_price": float(current_price)
            }
            
        except Exception as e:
            logger.error(f"Fehler bei Indikator-Berechnung: {e}")
            return self._default_indicators()
    
    def _default_indicators(self) -> Dict:
        """Standard-Indikatoren wenn Berechnung fehlschlägt"""
        return {
            "rsi": 50.0,
            "macd": 0.0,
            "macd_signal": 0.0,
            "macd_diff": 0.0,
            "sma_20": 0.0,
            "sma_50": 0.0,
            "ema_12": 0.0,
            "ema_26": 0.0,
            "bb_upper": 0.0,
            "bb_middle": 0.0,
            "bb_lower": 0.0,
            "atr": 0.0,
            "stoch_k": 50.0,
            "stoch_d": 50.0,
            "current_price": 0.0
        }
    
    def generate_multi_strategy_signal(self, indicators: Dict, news: Dict, economic: Dict = None, market_sentiment: Dict = None, sr_levels: Dict = None) -> Dict:
        """Multi-Strategie-Analyse: Kombiniere ALLE verfügbaren Signale"""
        
        signals = []
        scores = []
        
        economic = economic or {"total_events": 0, "high_impact": 0}
        market_sentiment = market_sentiment or {"sentiment": "neutral"}
        sr_levels = sr_levels or {"support": 0, "resistance": 0, "current_price": 0}
        
        logger.info("="*70)
        logger.info("🔍 DETAILLIERTE SIGNAL-ANALYSE - ALLE INDIKATOREN")
        logger.info("="*70)
        
        # 1. RSI Strategy
        rsi = indicators.get('rsi', 50)
        logger.info(f"📊 1. RSI-Indikator: {rsi:.2f}")
        if rsi < 30:
            signal_text = "RSI: Überverkauft (BUY)"
            signal_score = 2.0
            logger.info(f"   ✅ {signal_text} | Score: +{signal_score}")
            signals.append(signal_text)
            scores.append(signal_score)
        elif rsi < 40:
            signal_text = "RSI: Leicht überverkauft (BUY)"
            signal_score = 1.0
            logger.info(f"   ✅ {signal_text} | Score: +{signal_score}")
            signals.append(signal_text)
            scores.append(signal_score)
        elif rsi > 70:
            signal_text = "RSI: Überkauft (SELL)"
            signal_score = -2.0
            logger.info(f"   🔴 {signal_text} | Score: {signal_score}")
            signals.append(signal_text)
            scores.append(signal_score)
        elif rsi > 60:
            signal_text = "RSI: Leicht überkauft (SELL)"
            signal_score = -1.0
            logger.info(f"   🔴 {signal_text} | Score: {signal_score}")
            signals.append(signal_text)
            scores.append(signal_score)
        else:
            signal_text = "RSI: Neutral"
            signal_score = 0.0
            logger.info(f"   ⚪ {signal_text} | Score: {signal_score}")
            signals.append(signal_text)
            scores.append(signal_score)
        
        # 2. MACD Strategy
        macd_diff = indicators.get('macd_diff', 0)
        logger.info(f"📊 2. MACD-Differenz: {macd_diff:.4f}")
        if macd_diff > 0:
            signal_text = "MACD: Bullish Crossover (BUY)"
            signal_score = 1.5
            logger.info(f"   ✅ {signal_text} | Score: +{signal_score}")
            signals.append(signal_text)
            scores.append(signal_score)
        elif macd_diff < 0:
            signal_text = "MACD: Bearish Crossover (SELL)"
            signal_score = -1.5
            logger.info(f"   🔴 {signal_text} | Score: {signal_score}")
            signals.append(signal_text)
            scores.append(signal_score)
        else:
            signal_text = "MACD: Neutral"
            signal_score = 0.0
            logger.info(f"   ⚪ {signal_text} | Score: {signal_score}")
            signals.append(signal_text)
            scores.append(signal_score)
        
        # 3. Moving Average Strategy
        current_price = indicators.get('current_price', 0)
        sma_20 = indicators.get('sma_20', 0)
        sma_50 = indicators.get('sma_50', 0)
        
        logger.info(f"📊 3. Moving Averages: Preis={current_price:.2f}, SMA20={sma_20:.2f}, SMA50={sma_50:.2f}")
        
        if current_price > 0 and sma_20 > 0 and sma_50 > 0:
            if sma_20 > sma_50 and current_price > sma_20:
                signal_text = "MA: Starker Uptrend (BUY)"
                signal_score = 1.5
                logger.info(f"   ✅ {signal_text} | Score: +{signal_score}")
                signals.append(signal_text)
                scores.append(signal_score)
            elif sma_20 < sma_50 and current_price < sma_20:
                signal_text = "MA: Starker Downtrend (SELL)"
                signal_score = -1.5
                logger.info(f"   🔴 {signal_text} | Score: {signal_score}")
                signals.append(signal_text)
                scores.append(signal_score)
            elif current_price > sma_20:
                signal_text = "MA: Über SMA20 (BUY)"
                signal_score = 0.5
                logger.info(f"   ✅ {signal_text} | Score: +{signal_score}")
                signals.append(signal_text)
                scores.append(signal_score)
            elif current_price < sma_20:
                signal_text = "MA: Unter SMA20 (SELL)"
                signal_score = -0.5
                logger.info(f"   🔴 {signal_text} | Score: {signal_score}")
                signals.append(signal_text)
                scores.append(signal_score)
        
        # 4. Bollinger Bands Strategy
        bb_upper = indicators.get('bb_upper', 0)
        bb_lower = indicators.get('bb_lower', 0)
        
        logger.info(f"📊 4. Bollinger Bands: Lower={bb_lower:.2f}, Upper={bb_upper:.2f}, Preis={current_price:.2f}")
        
        if current_price > 0 and bb_upper > 0 and bb_lower > 0:
            if current_price <= bb_lower:
                signal_text = "BB: Preis am unteren Band (BUY)"
                signal_score = 1.5
                logger.info(f"   ✅ {signal_text} | Score: +{signal_score}")
                signals.append(signal_text)
                scores.append(signal_score)
            elif current_price >= bb_upper:
                signal_text = "BB: Preis am oberen Band (SELL)"
                signal_score = -1.5
                logger.info(f"   🔴 {signal_text} | Score: {signal_score}")
                signals.append(signal_text)
                scores.append(signal_score)
            else:
                logger.info(f"   ⚪ Bollinger Bands: Neutral (Preis innerhalb der Bänder)")
        
        # 5. Stochastic Strategy
        stoch_k = indicators.get('stoch_k', 50)
        logger.info(f"📊 5. Stochastic Oscillator: {stoch_k:.2f}")
        if stoch_k < 20:
            signal_text = "Stochastic: Überverkauft (BUY)"
            signal_score = 1.0
            logger.info(f"   ✅ {signal_text} | Score: +{signal_score}")
            signals.append(signal_text)
            scores.append(signal_score)
        elif stoch_k > 80:
            signal_text = "Stochastic: Überkauft (SELL)"
            signal_score = -1.0
            logger.info(f"   🔴 {signal_text} | Score: {signal_score}")
            signals.append(signal_text)
            scores.append(signal_score)
        else:
            logger.info(f"   ⚪ Stochastic: Neutral")
        
        # 6. News Sentiment (Multi-Source)
        news_sentiment = news.get('sentiment', 'neutral')
        news_score = news.get('score', 0)
        news_source = news.get('source', 'none')
        news_articles = news.get('articles', 0)
        
        logger.info(f"📰 6. News Sentiment: {news_sentiment.upper()} | Score: {news_score:.2f} | Artikel: {news_articles} | Quelle: {news_source}")
        
        if news_sentiment == 'bullish':
            signal_text = f"News: Positiv ({news_articles} Artikel via {news_source})"
            signal_score = news_score * 2.5
            logger.info(f"   ✅ {signal_text} | Score: +{signal_score:.2f} (Gewichtet: News x2.5)")
            signals.append(signal_text)
            scores.append(signal_score)
        elif news_sentiment == 'bearish':
            signal_text = f"News: Negativ ({news_articles} Artikel via {news_source})"
            signal_score = news_score * 2.5
            logger.info(f"   🔴 {signal_text} | Score: {signal_score:.2f} (Gewichtet: News x2.5)")
            signals.append(signal_text)
            scores.append(signal_score)
        else:
            signal_text = "News: Neutral"
            signal_score = 0.0
            logger.info(f"   ⚪ {signal_text} | Score: {signal_score}")
            signals.append(signal_text)
            scores.append(signal_score)
        
        # 7. Economic Calendar Impact
        high_impact_events = economic.get('high_impact', 0)
        total_events = economic.get('total_events', 0)
        logger.info(f"📅 7. Economic Calendar: {total_events} Events gesamt, {high_impact_events} High-Impact")
        if high_impact_events > 0:
            signal_text = f"📅 Economic Events: {high_impact_events} High-Impact heute"
            signal_score = -0.5 * high_impact_events
            logger.info(f"   🔴 {signal_text} | Score: {signal_score} (Vorsicht)")
            signals.append(signal_text)
            scores.append(signal_score)
        else:
            logger.info(f"   ⚪ Keine kritischen Economic Events heute")
        
        # 8. Market Sentiment (Fear & Greed)
        overall_sentiment = market_sentiment.get('sentiment', 'neutral')
        market_rsi = market_sentiment.get('rsi', 50)
        logger.info(f"🌍 8. Market Sentiment: {overall_sentiment.upper()} | Market RSI: {market_rsi:.2f}")
        if overall_sentiment == 'greedy':
            signal_text = "Market: Greedy (Chance für Contrarian)"
            signal_score = 0.5
            logger.info(f"   ✅ {signal_text} | Score: +{signal_score}")
            signals.append(signal_text)
            scores.append(signal_score)
        elif overall_sentiment == 'fearful':
            signal_text = "Market: Fearful (Vorsicht)"
            signal_score = -0.5
            logger.info(f"   🔴 {signal_text} | Score: {signal_score}")
            signals.append(signal_text)
            scores.append(signal_score)
        else:
            logger.info(f"   ⚪ Market Sentiment: Neutral")
        
        # 9. Support/Resistance Levels
        if sr_levels.get('current_price', 0) > 0:
            current = sr_levels['current_price']
            support = sr_levels.get('support', 0)
            resistance = sr_levels.get('resistance', 0)
            
            logger.info(f"📊 9. Support/Resistance: Support={support:.2f}, Resistance={resistance:.2f}, Aktuell={current:.2f}")
            
            if support > 0 and current <= support * 1.02:  # Nahe Support
                signal_text = f"S/R: Nahe Support ({support:.2f})"
                signal_score = 1.0
                logger.info(f"   ✅ {signal_text} | Score: +{signal_score}")
                signals.append(signal_text)
                scores.append(signal_score)
            elif resistance > 0 and current >= resistance * 0.98:  # Nahe Resistance
                signal_text = f"S/R: Nahe Resistance ({resistance:.2f})"
                signal_score = -1.0
                logger.info(f"   🔴 {signal_text} | Score: {signal_score}")
                signals.append(signal_text)
                scores.append(signal_score)
            else:
                logger.info(f"   ⚪ S/R: Preis weder nahe Support noch Resistance")
        else:
            logger.info(f"📊 9. Support/Resistance: Keine Daten verfügbar")
        
        # Gesamtscore berechnen
        total_score = sum(scores)
        
        logger.info("="*70)
        logger.info(f"📊 GESAMT-SCORE: {total_score:.2f} (aus {len(scores)} Signalen)")
        logger.info(f"   Einzelne Scores: {[round(s, 2) for s in scores]}")
        logger.info("="*70)
        
        # Signal-Entscheidung
        if total_score >= 3.0:
            final_signal = "BUY"
            confidence = min(100, abs(total_score) * 15)
            logger.info(f"🎯 FINALE ENTSCHEIDUNG: BUY | Konfidenz: {confidence:.1f}%")
        elif total_score <= -3.0:
            final_signal = "SELL"
            confidence = min(100, abs(total_score) * 15)
            logger.info(f"🎯 FINALE ENTSCHEIDUNG: SELL | Konfidenz: {confidence:.1f}%")
        else:
            final_signal = "HOLD"
            confidence = 0
            logger.info(f"🎯 FINALE ENTSCHEIDUNG: HOLD | Score zu niedrig ({total_score:.2f})")
        
        logger.info("="*70)
        
        return {
            "signal": final_signal,
            "confidence": round(confidence, 1),
            "total_score": round(total_score, 2),
            "signals": signals,
            "indicators": indicators,
            "news": news
        }
    
    async def fetch_economic_calendar(self) -> Dict:
        """Hole Economic Calendar Events (Finnhub)"""
        try:
            cache_key = "economic_calendar"
            if cache_key in self.economic_cache:
                cache_time, cache_data = self.economic_cache[cache_key]
                if (datetime.now() - cache_time).seconds < 3600:  # 1 Stunde Cache
                    return cache_data
            
            # Finnhub Economic Calendar
            today = datetime.now().strftime('%Y-%m-%d')
            url = f"https://finnhub.io/api/v1/calendar/economic?from={today}&to={today}&token={self.finnhub_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        events = data.get('economicCalendar', [])
                        
                        # Filter wichtige Events
                        important_events = [e for e in events if e.get('impact', '') in ['high', 'medium']]
                        
                        result = {
                            "total_events": len(events),
                            "high_impact": len([e for e in important_events if e.get('impact') == 'high']),
                            "events": important_events[:10]  # Top 10
                        }
                        
                        self.economic_cache[cache_key] = (datetime.now(), result)
                        logger.info(f"📅 Economic Calendar: {result['total_events']} Events, {result['high_impact']} High-Impact")
                        
                        return result
            
            return {"total_events": 0, "high_impact": 0, "events": []}
            
        except Exception as e:
            logger.error(f"Economic calendar error: {e}")
            return {"total_events": 0, "high_impact": 0, "events": []}
    
    async def fetch_market_sentiment(self) -> Dict:
        """Hole allgemeines Markt-Sentiment (Fear & Greed Index approximation)"""
        try:
            # Verwende Finnhub Aggregate Indicators
            url = f"https://finnhub.io/api/v1/stock/metric?symbol=SPY&metric=all&token={self.finnhub_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        metric = data.get('metric', {})
                        
                        # RSI und andere Metriken
                        rsi_14 = metric.get('rsi', 50)
                        
                        # Interpretiere als Markt-Sentiment
                        if rsi_14 > 70:
                            sentiment = "fearful"  # Überkauft = Euphorie/Angst vor Korrektur
                        elif rsi_14 < 30:
                            sentiment = "greedy"  # Überverkauft = Chance
                        else:
                            sentiment = "neutral"
                        
                        return {
                            "sentiment": sentiment,
                            "rsi": rsi_14,
                            "source": "finnhub"
                        }
            
            return {"sentiment": "neutral", "rsi": 50, "source": "none"}
            
        except Exception as e:
            logger.error(f"Market sentiment error: {e}")
            return {"sentiment": "neutral", "rsi": 50, "source": "error"}
    
    def calculate_support_resistance(self, price_history: List[Dict]) -> Dict:
        """Berechne Support und Resistance Levels"""
        try:
            if len(price_history) < 20:
                return {"support": 0, "resistance": 0}
            
            df = pd.DataFrame(price_history)
            prices = df['close'].values if 'close' in df.columns else df['price'].values
            
            # Verwende lokale Minima/Maxima
            from scipy.signal import argrelextrema
            
            # Finde lokale Maxima (Resistance)
            maxima_idx = argrelextrema(prices, np.greater, order=5)[0]
            # Finde lokale Minima (Support)
            minima_idx = argrelextrema(prices, np.less, order=5)[0]
            
            resistance = np.mean(prices[maxima_idx]) if len(maxima_idx) > 0 else prices[-1]
            support = np.mean(prices[minima_idx]) if len(minima_idx) > 0 else prices[-1]
            
            return {
                "support": float(support),
                "resistance": float(resistance),
                "current_price": float(prices[-1])
            }
            
        except Exception as e:
            logger.error(f"Support/Resistance calculation error: {e}")
            return {"support": 0, "resistance": 0, "current_price": 0}
    
    async def analyze_commodity(self, commodity_id: str, price_history: List[Dict]) -> Dict:
        """Vollständige ERWEITERTE Analyse eines Rohstoffs"""
        
        # 1. Technische Indikatoren berechnen
        indicators = self.calculate_technical_indicators(price_history)
        
        # 2. News-Sentiment holen (Multi-Source)
        news = await self.fetch_news_sentiment(commodity_id)
        
        # 3. Economic Calendar holen
        economic = await self.fetch_economic_calendar()
        
        # 4. Markt-Sentiment holen
        market_sentiment = await self.fetch_market_sentiment()
        
        # 5. Support/Resistance berechnen
        sr_levels = self.calculate_support_resistance(price_history)
        
        # 6. Multi-Strategie-Signal generieren (erweitert)
        analysis = self.generate_multi_strategy_signal(
            indicators, 
            news, 
            economic=economic,
            market_sentiment=market_sentiment,
            sr_levels=sr_levels
        )
        
        # Füge zusätzliche Daten hinzu
        analysis['economic_events'] = economic
        analysis['market_sentiment'] = market_sentiment
        analysis['support_resistance'] = sr_levels
        
        logger.info(f"📊 Erweiterte Analyse {commodity_id}: {analysis['signal']} (Konfidenz: {analysis['confidence']}%, Score: {analysis['total_score']})")
        
        return analysis


# Singleton instance
market_analyzer = MarketAnalyzer()
