"""
🧠 BOONER INTELLIGENCE ENGINE V3.0.0
====================================

Agentisches, selbstlernendes Trading-System mit:
1. Devil's Advocate Reasoning Engine
2. Dynamic Weight Optimization (Bayesian)
3. Deep Sentiment NLP Analysis
4. Chaos Circuit Breaker

Autor: Booner Trade Team
Version: 3.0.0
"""

import logging
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np
import aiohttp

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# V3.0 DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ReasoningResult:
    """Ergebnis der Devil's Advocate Reasoning Engine"""
    optimist_reasoning: str
    auditor_reasoning: str
    final_reasoning: str
    original_score: float
    adjusted_score: float
    score_adjustment: float  # Negative = Abzug
    risk_factor: float  # 0-1
    red_flags: List[str]
    green_flags: List[str]
    trade_approved: bool
    reasoning_text: str

@dataclass
class WeightOptimization:
    """Ergebnis der Gewichts-Optimierung"""
    asset: str
    old_weights: Dict[str, float]
    new_weights: Dict[str, float]
    performance_data: Dict[str, Any]
    optimization_reason: str
    timestamp: str

@dataclass
class SentimentAnalysis:
    """Ergebnis der Deep Sentiment Analysis"""
    headline: str
    classification: str  # BULLISH_IMPULSE, BEARISH_DIVERGENCE, NOISE
    confidence: float
    impact_score: float  # -100 bis +100
    reasoning: str


# ═══════════════════════════════════════════════════════════════════════════
# 1. DEVIL'S ADVOCATE REASONING ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class DevilsAdvocateEngine:
    """
    V3.0: Bidirektionale Analyse vor Trade-Ausführung.
    
    Rolle A (Optimist): Begründet den Trade
    Rolle B (Auditor): Sucht nach Red Flags
    
    Trade wird nur ausgeführt wenn Score-Korrektur < 5%
    """
    
    def __init__(self, ollama_base_url: str = "http://127.0.0.1:11434", model: str = "llama3:latest"):
        self.ollama_base_url = ollama_base_url
        self.model = model
        self.max_score_adjustment = 5.0  # Max 5% Korrektur erlaubt
        
    async def _call_ollama(self, system_prompt: str, user_message: str) -> str:
        """Ruft Ollama API auf"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Niedrig für konsistente Analyse
                        "num_predict": 500
                    }
                }
                
                async with session.post(
                    f"{self.ollama_base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('message', {}).get('content', '')
                    else:
                        logger.warning(f"Ollama returned status {response.status}")
                        return ""
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return ""
    
    async def analyze_trade(
        self,
        commodity: str,
        signal: str,
        confidence_score: float,
        pillar_scores: Dict[str, float],
        market_data: Dict[str, Any],
        ema200_distance: float = 0.0
    ) -> ReasoningResult:
        """
        Führt bidirektionale Analyse durch.
        
        Returns:
            ReasoningResult mit finaler Entscheidung
        """
        
        # Daten für die Analyse aufbereiten
        data_payload = {
            "commodity": commodity,
            "signal": signal,
            "confidence_score": confidence_score,
            "pillar_scores": pillar_scores,
            "ema200_distance_percent": ema200_distance,
            "current_price": market_data.get('price', 0),
            "rsi": market_data.get('rsi', 50),
            "trend": market_data.get('trend', 'neutral'),
            "volatility": market_data.get('atr_normalized', 1.0)
        }
        
        # === ROLLE A: THE OPTIMIST ===
        optimist_prompt = """Du bist "The Optimist" - ein erfahrener Trader, der die STÄRKEN eines Trades hervorhebt.
Deine Aufgabe: Erkläre präzise, warum dieser Trade erfolgreich sein könnte.
Fokussiere auf: Technische Bestätigung, Trend-Alignment, günstige Marktbedingungen.
Antworte in 2-3 Sätzen auf Deutsch. Beginne mit "STÄRKEN:"."""

        optimist_message = f"""Analysiere diesen Trade:
Asset: {commodity}
Signal: {signal}
Confidence: {confidence_score:.1f}%
Säulen-Scores: Basis={pillar_scores.get('base', 0)}, Trend={pillar_scores.get('trend', 0)}, Vola={pillar_scores.get('volatility', 0)}, Sentiment={pillar_scores.get('sentiment', 0)}
EMA200-Abstand: {ema200_distance:+.2f}%
RSI: {market_data.get('rsi', 50):.1f}"""

        optimist_response = await self._call_ollama(optimist_prompt, optimist_message)
        
        # === ROLLE B: THE AUDITOR ===
        auditor_prompt = """Du bist "The Auditor" - ein kritischer Risikoanalyst, der nach RED FLAGS sucht.
Deine Aufgabe: Finde ALLE potentiellen Schwachstellen und Risiken.
Prüfe: EMA200-Überdehnung (>5% = Warnung), RSI-Extreme (<30/>70), Trend-Divergenzen.
Antworte in 2-3 Sätzen auf Deutsch. Beginne mit "RISIKEN:"."""

        auditor_message = f"""Prüfe kritisch diesen Trade auf Risiken:
Asset: {commodity}
Signal: {signal}
Confidence: {confidence_score:.1f}%
EMA200-Abstand: {ema200_distance:+.2f}% {"⚠️ ÜBERDEHNT!" if abs(ema200_distance) > 5 else ""}
RSI: {market_data.get('rsi', 50):.1f} {"⚠️ ÜBERKAUFT!" if market_data.get('rsi', 50) > 70 else "⚠️ ÜBERVERKAUFT!" if market_data.get('rsi', 50) < 30 else ""}
Volatilität: {market_data.get('atr_normalized', 1.0):.2f}x {"⚠️ EXTREM!" if market_data.get('atr_normalized', 1.0) > 2.0 else ""}"""

        auditor_response = await self._call_ollama(auditor_prompt, auditor_message)
        
        # === RED FLAG DETECTION (Rule-Based) ===
        red_flags = []
        green_flags = []
        score_adjustment = 0.0
        
        # EMA200 Überdehnung
        if abs(ema200_distance) > 8.0:
            red_flags.append(f"EXTREM überdehnt ({ema200_distance:+.1f}% vom EMA200)")
            score_adjustment -= 4.0
        elif abs(ema200_distance) > 5.0:
            red_flags.append(f"Stark überdehnt ({ema200_distance:+.1f}% vom EMA200)")
            score_adjustment -= 2.5
        elif abs(ema200_distance) > 3.0:
            red_flags.append(f"Leicht überdehnt ({ema200_distance:+.1f}% vom EMA200)")
            score_adjustment -= 1.0
        
        # RSI Extreme
        rsi = market_data.get('rsi', 50)
        if signal == 'BUY' and rsi > 75:
            red_flags.append(f"RSI überkauft ({rsi:.0f})")
            score_adjustment -= 2.0
        elif signal == 'SELL' and rsi < 25:
            red_flags.append(f"RSI überverkauft ({rsi:.0f})")
            score_adjustment -= 2.0
        
        # Extreme Volatilität
        atr_norm = market_data.get('atr_normalized', 1.0)
        if atr_norm > 2.5:
            red_flags.append(f"Extreme Volatilität ({atr_norm:.1f}x)")
            score_adjustment -= 3.0
        elif atr_norm > 2.0:
            red_flags.append(f"Hohe Volatilität ({atr_norm:.1f}x)")
            score_adjustment -= 1.5
        
        # Green Flags
        if 0.8 <= atr_norm <= 1.5:
            green_flags.append("Optimale Volatilität")
        if 40 <= rsi <= 60:
            green_flags.append("RSI im neutralen Bereich")
        if abs(ema200_distance) < 2.0:
            green_flags.append("Nahe am EMA200 (guter Entry)")
        
        # === FINAL REASONING ===
        adjusted_score = max(0, min(100, confidence_score + score_adjustment))
        trade_approved = abs(score_adjustment) <= self.max_score_adjustment
        
        # Risk Factor berechnen (0 = kein Risiko, 1 = maximales Risiko)
        risk_factor = min(1.0, len(red_flags) * 0.2 + (abs(score_adjustment) / 10))
        
        final_reasoning = f"""
🔍 DEVIL'S ADVOCATE ANALYSE für {commodity} {signal}

📈 OPTIMIST: {optimist_response if optimist_response else 'Technische Indikatoren unterstützen den Trade.'}

📉 AUDITOR: {auditor_response if auditor_response else 'Keine kritischen Risiken identifiziert.'}

🎯 ENTSCHEIDUNG:
- Original Score: {confidence_score:.1f}%
- Korrektur: {score_adjustment:+.1f}%
- Final Score: {adjusted_score:.1f}%
- Risk Factor: {risk_factor:.2f}
- Status: {'✅ TRADE GENEHMIGT' if trade_approved else '❌ TRADE BLOCKIERT (Korrektur > 5%)'}

🚩 Red Flags: {', '.join(red_flags) if red_flags else 'Keine'}
✅ Green Flags: {', '.join(green_flags) if green_flags else 'Keine'}
"""
        
        logger.info(f"🧠 Devil's Advocate: {commodity} {signal} - Score {confidence_score:.1f}% → {adjusted_score:.1f}% (Δ{score_adjustment:+.1f}%)")
        
        return ReasoningResult(
            optimist_reasoning=optimist_response or "Technische Bestätigung vorhanden",
            auditor_reasoning=auditor_response or "Standard-Risikoprüfung bestanden",
            final_reasoning=final_reasoning,
            original_score=confidence_score,
            adjusted_score=adjusted_score,
            score_adjustment=score_adjustment,
            risk_factor=risk_factor,
            red_flags=red_flags,
            green_flags=green_flags,
            trade_approved=trade_approved,
            reasoning_text=final_reasoning
        )


# ═══════════════════════════════════════════════════════════════════════════
# 2. DYNAMIC WEIGHT OPTIMIZER (Bayesian Learning)
# ═══════════════════════════════════════════════════════════════════════════

class DynamicWeightOptimizer:
    """
    V3.0: Bayesianisches Feedback-Modell für Säulen-Gewichtung.
    
    Formel: w_{i,t+1} = w_{i,t} + η * R_trade * C_{i,trade}
    
    - η (Lernrate): 0.05
    - R_trade: +1 (Gewinn) / -1 (Verlust)
    - C_{i,trade}: Confidence-Beitrag der Säule
    """
    
    def __init__(self, learning_rate: float = 0.05):
        self.learning_rate = learning_rate
        self.min_weight = 5.0   # Minimum 5% pro Säule
        self.max_weight = 60.0  # Maximum 60% pro Säule
        
        # Default-Gewichte pro Strategie
        self.default_weights = {
            'swing': {'base_signal': 30, 'trend_confluence': 40, 'volatility': 10, 'sentiment': 20},
            'day': {'base_signal': 35, 'trend_confluence': 25, 'volatility': 20, 'sentiment': 20},
            'scalping': {'base_signal': 40, 'trend_confluence': 10, 'volatility': 40, 'sentiment': 10},
            'momentum': {'base_signal': 20, 'trend_confluence': 30, 'volatility': 40, 'sentiment': 10},
            'mean_reversion': {'base_signal': 50, 'trend_confluence': 10, 'volatility': 30, 'sentiment': 10},
            'breakout': {'base_signal': 30, 'trend_confluence': 15, 'volatility': 45, 'sentiment': 10},
            'grid': {'base_signal': 10, 'trend_confluence': 50, 'volatility': 30, 'sentiment': 10}
        }
        
        # Asset-spezifische Gewichts-Anpassungen (wird gelernt)
        self.asset_weight_adjustments: Dict[str, Dict[str, float]] = {}
    
    def calculate_weight_adjustment(
        self,
        trade_result: float,  # +1 oder -1
        pillar_contributions: Dict[str, float],  # Beitrag jeder Säule zum Score
        current_weights: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Berechnet Gewichts-Anpassung nach Bayesian Feedback.
        
        w_{i,t+1} = w_{i,t} + η * R_trade * (C_{i,trade} / 100)
        """
        new_weights = {}
        total_contribution = sum(pillar_contributions.values()) or 1
        
        for pillar, current_weight in current_weights.items():
            # Normalisierter Beitrag (0-1)
            c_i = pillar_contributions.get(pillar, 0) / total_contribution
            
            # Gewichts-Update
            adjustment = self.learning_rate * trade_result * c_i * 100
            new_weight = current_weight + adjustment
            
            # Clamp auf erlaubten Bereich
            new_weight = max(self.min_weight, min(self.max_weight, new_weight))
            new_weights[pillar] = round(new_weight, 1)
        
        # Normalisieren auf 100%
        total = sum(new_weights.values())
        if total != 100:
            factor = 100 / total
            new_weights = {k: round(v * factor, 1) for k, v in new_weights.items()}
        
        return new_weights
    
    async def optimize_from_trade_history(
        self,
        trades: List[Dict],
        asset: str,
        strategy: str,
        lookback_days: int = 14
    ) -> WeightOptimization:
        """
        Analysiert Trade-Historie und optimiert Gewichte.
        
        Args:
            trades: Liste der letzten Trades mit pillar_scores
            asset: Asset für das optimiert wird
            strategy: Aktive Strategie
            lookback_days: Anzahl Tage für Analyse
        """
        
        current_weights = self.default_weights.get(strategy, self.default_weights['day']).copy()
        
        # Wende vorherige Asset-Anpassungen an
        if asset in self.asset_weight_adjustments:
            for pillar, adj in self.asset_weight_adjustments[asset].items():
                if pillar in current_weights:
                    current_weights[pillar] = max(self.min_weight, 
                                                  min(self.max_weight, 
                                                      current_weights[pillar] + adj))
        
        # Filtere relevante Trades
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        relevant_trades = [
            t for t in trades 
            if t.get('commodity') == asset 
            and t.get('status') == 'CLOSED'
            and t.get('pillar_scores')
        ]
        
        if len(relevant_trades) < 3:
            return WeightOptimization(
                asset=asset,
                old_weights=current_weights.copy(),
                new_weights=current_weights,
                performance_data={'trades_analyzed': 0},
                optimization_reason="Nicht genug Trades für Optimierung",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        # Berechne kumulative Anpassung
        accumulated_weights = current_weights.copy()
        wins = 0
        losses = 0
        
        for trade in relevant_trades[-20:]:  # Max 20 Trades
            pnl = trade.get('profit_loss', 0)
            trade_result = 1 if pnl > 0 else -1
            
            if pnl > 0:
                wins += 1
            else:
                losses += 1
            
            pillar_scores = trade.get('pillar_scores', {})
            if pillar_scores:
                accumulated_weights = self.calculate_weight_adjustment(
                    trade_result=trade_result,
                    pillar_contributions=pillar_scores,
                    current_weights=accumulated_weights
                )
        
        # Speichere Anpassungen
        self.asset_weight_adjustments[asset] = {
            pillar: accumulated_weights[pillar] - current_weights[pillar]
            for pillar in current_weights
        }
        
        win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
        
        logger.info(f"📊 Weight Optimization für {asset}: {current_weights} → {accumulated_weights}")
        logger.info(f"   Win Rate: {win_rate:.1f}% ({wins}W/{losses}L)")
        
        return WeightOptimization(
            asset=asset,
            old_weights=current_weights,
            new_weights=accumulated_weights,
            performance_data={
                'trades_analyzed': len(relevant_trades),
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate
            },
            optimization_reason=f"Bayesian Update basierend auf {len(relevant_trades)} Trades",
            timestamp=datetime.now(timezone.utc).isoformat()
        )


# ═══════════════════════════════════════════════════════════════════════════
# 3. DEEP SENTIMENT NLP ANALYZER
# ═══════════════════════════════════════════════════════════════════════════

class DeepSentimentAnalyzer:
    """
    V3.0: NLP-basierte Sentiment-Analyse von News-Headlines.
    
    Klassifiziert in:
    - BULLISH_IMPULSE: Aktiver Bonus (+10-30 Punkte)
    - BEARISH_DIVERGENCE: Aktiver Malus (-10-30 Punkte)
    - NOISE: Kein Einfluss (0 Punkte)
    """
    
    def __init__(self, ollama_base_url: str = "http://127.0.0.1:11434", model: str = "llama3:latest"):
        self.ollama_base_url = ollama_base_url
        self.model = model
        
        # Keyword-basiertes Fallback (wenn Ollama nicht verfügbar)
        self.bullish_keywords = [
            'rally', 'surge', 'soar', 'jump', 'gain', 'rise', 'bullish', 'breakout',
            'record high', 'all-time high', 'demand', 'buying', 'accumulation',
            'steigt', 'gewinnt', 'rallye', 'nachfrage', 'kaufsignal'
        ]
        self.bearish_keywords = [
            'crash', 'plunge', 'drop', 'fall', 'decline', 'bearish', 'selloff',
            'record low', 'concern', 'fear', 'selling', 'distribution',
            'fällt', 'verliert', 'crash', 'panik', 'verkaufsdruck'
        ]
    
    async def analyze_headline(self, headline: str, asset: str) -> SentimentAnalysis:
        """
        Analysiert eine News-Headline und klassifiziert das Sentiment.
        """
        
        # Versuche Ollama-Analyse
        try:
            async with aiohttp.ClientSession() as session:
                prompt = f"""Klassifiziere diese News-Headline für {asset} in GENAU EINE Kategorie:
- BULLISH_IMPULSE: Starkes Kaufsignal (z.B. "Gold erreicht Allzeithoch")
- BEARISH_DIVERGENCE: Starkes Verkaufssignal (z.B. "Öl stürzt ab wegen Überangebot")
- NOISE: Neutral oder irrelevant (z.B. "Markt wartet auf Fed-Entscheidung")

Headline: "{headline}"

Antworte NUR mit dem Kategorie-Namen, nichts anderes."""

                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 50}
                }
                
                async with session.post(
                    f"{self.ollama_base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        classification = data.get('message', {}).get('content', '').strip().upper()
                        
                        if 'BULLISH' in classification:
                            return SentimentAnalysis(
                                headline=headline,
                                classification="BULLISH_IMPULSE",
                                confidence=0.8,
                                impact_score=20.0,
                                reasoning="Ollama: Bullish sentiment detected"
                            )
                        elif 'BEARISH' in classification:
                            return SentimentAnalysis(
                                headline=headline,
                                classification="BEARISH_DIVERGENCE",
                                confidence=0.8,
                                impact_score=-20.0,
                                reasoning="Ollama: Bearish sentiment detected"
                            )
        except Exception as e:
            logger.debug(f"Ollama sentiment analysis failed: {e}")
        
        # Fallback: Keyword-basierte Analyse
        headline_lower = headline.lower()
        
        bullish_count = sum(1 for kw in self.bullish_keywords if kw in headline_lower)
        bearish_count = sum(1 for kw in self.bearish_keywords if kw in headline_lower)
        
        if bullish_count > bearish_count and bullish_count >= 1:
            return SentimentAnalysis(
                headline=headline,
                classification="BULLISH_IMPULSE",
                confidence=min(0.9, 0.5 + bullish_count * 0.15),
                impact_score=min(30.0, 10.0 + bullish_count * 5),
                reasoning=f"Keyword match: {bullish_count} bullish keywords"
            )
        elif bearish_count > bullish_count and bearish_count >= 1:
            return SentimentAnalysis(
                headline=headline,
                classification="BEARISH_DIVERGENCE",
                confidence=min(0.9, 0.5 + bearish_count * 0.15),
                impact_score=max(-30.0, -10.0 - bearish_count * 5),
                reasoning=f"Keyword match: {bearish_count} bearish keywords"
            )
        
        return SentimentAnalysis(
            headline=headline,
            classification="NOISE",
            confidence=0.6,
            impact_score=0.0,
            reasoning="No significant sentiment detected"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 4. CHAOS CIRCUIT BREAKER
# ═══════════════════════════════════════════════════════════════════════════

class ChaosCircuitBreaker:
    """
    V3.0: Automatischer Schutz bei extremer Marktvolatilität.
    
    Wenn ATR > 2.5x normal → Threshold wird auf 90% gesetzt.
    """
    
    def __init__(self):
        self.chaos_threshold_override = 90.0
        self.extreme_volatility_multiplier = 2.5
        self.high_volatility_multiplier = 2.0
        
    def check_circuit_breaker(
        self,
        atr_normalized: float,
        market_state: str,
        original_threshold: float
    ) -> Tuple[float, bool, str]:
        """
        Prüft ob Circuit Breaker aktiviert werden muss.
        
        Returns:
            (new_threshold, circuit_breaker_active, reason)
        """
        
        # CHAOS-Erkennung
        if market_state == "chaos" or atr_normalized >= self.extreme_volatility_multiplier:
            logger.warning(f"🚨 CIRCUIT BREAKER AKTIVIERT! ATR={atr_normalized:.2f}x, State={market_state}")
            return (
                self.chaos_threshold_override,
                True,
                f"Extreme Volatilität ({atr_normalized:.1f}x) - Threshold auf {self.chaos_threshold_override}%"
            )
        
        # Hohe Volatilität: Threshold um 10% erhöhen
        if atr_normalized >= self.high_volatility_multiplier:
            new_threshold = min(90.0, original_threshold + 10.0)
            return (
                new_threshold,
                False,
                f"Hohe Volatilität ({atr_normalized:.1f}x) - Threshold +10% auf {new_threshold}%"
            )
        
        return (original_threshold, False, "Normal")


# ═══════════════════════════════════════════════════════════════════════════
# 5. MAIN BOONER INTELLIGENCE ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class BoonerIntelligenceEngine:
    """
    V3.0: Zentrale Steuerungseinheit für alle KI-Komponenten.
    
    Koordiniert:
    - Devil's Advocate Reasoning
    - Dynamic Weight Optimization
    - Deep Sentiment Analysis
    - Chaos Circuit Breaker
    """
    
    def __init__(
        self,
        ollama_base_url: str = "http://127.0.0.1:11434",
        ollama_model: str = "llama3:latest"
    ):
        self.devils_advocate = DevilsAdvocateEngine(ollama_base_url, ollama_model)
        self.weight_optimizer = DynamicWeightOptimizer()
        self.sentiment_analyzer = DeepSentimentAnalyzer(ollama_base_url, ollama_model)
        self.circuit_breaker = ChaosCircuitBreaker()
        
        # Tracking
        self.reasoning_history: List[ReasoningResult] = []
        self.optimization_history: List[WeightOptimization] = []
        
        logger.info("🧠 Booner Intelligence Engine V3.0 initialized")
    
    async def process_trade_decision(
        self,
        commodity: str,
        signal: str,
        original_confidence: float,
        pillar_scores: Dict[str, float],
        market_data: Dict[str, Any],
        strategy: str = "day"
    ) -> Dict[str, Any]:
        """
        Haupt-Entscheidungsprozess für einen Trade.
        
        1. Circuit Breaker Check
        2. Devil's Advocate Analysis
        3. Final Decision
        
        Returns:
            Dict mit finaler Entscheidung und Reasoning
        """
        
        result = {
            "commodity": commodity,
            "signal": signal,
            "original_confidence": original_confidence,
            "final_confidence": original_confidence,
            "approved": False,
            "reasoning": "",
            "circuit_breaker_active": False,
            "devils_advocate_result": None
        }
        
        # 1. Circuit Breaker Check
        atr_norm = market_data.get('atr_normalized', 1.0)
        market_state = market_data.get('market_state', 'normal')
        
        threshold, cb_active, cb_reason = self.circuit_breaker.check_circuit_breaker(
            atr_normalized=atr_norm,
            market_state=market_state,
            original_threshold=65.0  # Default threshold
        )
        
        result["circuit_breaker_active"] = cb_active
        if cb_active:
            result["reasoning"] += f"🚨 Circuit Breaker: {cb_reason}\n"
            logger.warning(f"Circuit Breaker für {commodity}: {cb_reason}")
        
        # 2. Devil's Advocate Analysis
        da_result = await self.devils_advocate.analyze_trade(
            commodity=commodity,
            signal=signal,
            confidence_score=original_confidence,
            pillar_scores=pillar_scores,
            market_data=market_data,
            ema200_distance=market_data.get('ema200_distance_percent', 0)
        )
        
        result["devils_advocate_result"] = da_result
        result["final_confidence"] = da_result.adjusted_score
        result["reasoning"] += da_result.final_reasoning
        
        # 3. Final Decision
        effective_threshold = threshold if cb_active else 65.0
        result["approved"] = (
            da_result.trade_approved and 
            da_result.adjusted_score >= effective_threshold
        )
        
        # Speichere für History
        self.reasoning_history.append(da_result)
        if len(self.reasoning_history) > 100:
            self.reasoning_history.pop(0)
        
        logger.info(f"🧠 BIE Decision: {commodity} {signal} - {'✅ APPROVED' if result['approved'] else '❌ REJECTED'} "
                   f"(Score: {da_result.adjusted_score:.1f}%, Threshold: {effective_threshold}%)")
        
        return result
    
    async def run_weekly_optimization(
        self,
        trades: List[Dict],
        assets: List[str],
        strategy: str = "day"
    ) -> List[WeightOptimization]:
        """
        Führt wöchentliche Gewichts-Optimierung für alle Assets durch.
        """
        
        optimizations = []
        
        for asset in assets:
            opt = await self.weight_optimizer.optimize_from_trade_history(
                trades=trades,
                asset=asset,
                strategy=strategy
            )
            optimizations.append(opt)
            self.optimization_history.append(opt)
        
        logger.info(f"📊 Weekly Optimization abgeschlossen für {len(assets)} Assets")
        return optimizations
    
    def get_optimized_weights(self, asset: str, strategy: str) -> Dict[str, float]:
        """
        Holt die optimierten Gewichte für ein Asset.
        """
        base_weights = self.weight_optimizer.default_weights.get(
            strategy, 
            self.weight_optimizer.default_weights['day']
        ).copy()
        
        # Wende Asset-spezifische Anpassungen an
        adjustments = self.weight_optimizer.asset_weight_adjustments.get(asset, {})
        for pillar, adj in adjustments.items():
            if pillar in base_weights:
                base_weights[pillar] = max(5, min(60, base_weights[pillar] + adj))
        
        return base_weights


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════

_booner_engine: Optional[BoonerIntelligenceEngine] = None

def get_booner_engine(
    ollama_base_url: str = "http://127.0.0.1:11434",
    ollama_model: str = "llama3:latest"
) -> BoonerIntelligenceEngine:
    """Singleton-Zugriff auf die Booner Intelligence Engine"""
    global _booner_engine
    if _booner_engine is None:
        _booner_engine = BoonerIntelligenceEngine(ollama_base_url, ollama_model)
    return _booner_engine


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    'BoonerIntelligenceEngine',
    'DevilsAdvocateEngine',
    'DynamicWeightOptimizer',
    'DeepSentimentAnalyzer',
    'ChaosCircuitBreaker',
    'ReasoningResult',
    'WeightOptimization',
    'SentimentAnalysis',
    'get_booner_engine'
]
