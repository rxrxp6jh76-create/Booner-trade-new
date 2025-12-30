"""
📡 Booner Trade V3.1.0 - Signals Routes

Enthält alle signal-bezogenen API-Endpunkte:
- Signal Status
- 4-Pillar Confidence Engine
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

signals_router = APIRouter(prefix="/signals", tags=["Signals"])


@signals_router.get("/status")
async def get_signals_status():
    """
    Get signal status for all commodities with 4-Pillar Confidence scores.
    V3.0.0: Includes pillar breakdown and signal generation.
    """
    try:
        import database as db
        from commodity_processor import COMMODITIES
        
        results = {}
        
        for commodity_id in COMMODITIES.keys():
            try:
                # Get market data
                market_data = await db.market_data.find_one({"commodity": commodity_id})
                
                if market_data:
                    # Calculate 4-Pillar confidence
                    confidence = 0
                    pillar_scores = {}
                    signal = "HOLD"
                    
                    try:
                        from booner_intelligence_engine import get_booner_engine
                        engine = get_booner_engine()
                        
                        # Get indicators
                        indicators = {
                            'rsi': market_data.get('rsi', 50),
                            'macd': market_data.get('macd', 0),
                            'adx': market_data.get('adx', 25),
                            'atr': market_data.get('atr', 0),
                            'bollinger_upper': market_data.get('bollinger_upper', 0),
                            'bollinger_lower': market_data.get('bollinger_lower', 0),
                            'bollinger_width': market_data.get('bollinger_width', 0),
                            'price': market_data.get('price', 0)
                        }
                        
                        # Analyze with 4-Pillar engine
                        analysis = await engine.analyze_asset(commodity_id, indicators)
                        
                        confidence = analysis.confidence_score
                        pillar_scores = {
                            'base_signal': analysis.pillar_scores.get('base_signal', 0),
                            'trend_confluence': analysis.pillar_scores.get('trend_confluence', 0),
                            'volatility': analysis.pillar_scores.get('volatility', 0),
                            'sentiment': analysis.pillar_scores.get('sentiment', 0)
                        }
                        
                        # Determine signal
                        if confidence >= 70:
                            rsi = indicators.get('rsi', 50)
                            if rsi > 60:
                                signal = "SELL"
                            elif rsi < 40:
                                signal = "BUY"
                            else:
                                signal = "HOLD"
                        
                    except Exception as e:
                        logger.debug(f"4-Pillar analysis not available for {commodity_id}: {e}")
                        # Fallback: Simple RSI-based confidence
                        rsi = market_data.get('rsi', 50)
                        if rsi:
                            if rsi > 70 or rsi < 30:
                                confidence = 70
                                signal = "SELL" if rsi > 70 else "BUY"
                            elif rsi > 60 or rsi < 40:
                                confidence = 50
                            else:
                                confidence = 30
                    
                    results[commodity_id] = {
                        'commodity': commodity_id,
                        'name': COMMODITIES[commodity_id].get('name', commodity_id),
                        'price': market_data.get('price'),
                        'confidence': confidence,
                        'pillar_scores': pillar_scores,
                        'signal': signal,
                        'indicators': {
                            'rsi': market_data.get('rsi'),
                            'macd': market_data.get('macd'),
                            'adx': market_data.get('adx'),
                            'atr': market_data.get('atr')
                        },
                        'timestamp': market_data.get('timestamp')
                    }
                else:
                    results[commodity_id] = {
                        'commodity': commodity_id,
                        'name': COMMODITIES[commodity_id].get('name', commodity_id),
                        'confidence': 0,
                        'signal': 'NO_DATA',
                        'pillar_scores': {}
                    }
                    
            except Exception as e:
                logger.warning(f"Error processing {commodity_id}: {e}")
                results[commodity_id] = {
                    'commodity': commodity_id,
                    'confidence': 0,
                    'signal': 'ERROR',
                    'error': str(e)
                }
        
        # Summary stats
        total = len(results)
        green = len([r for r in results.values() if r.get('signal') in ['BUY', 'SELL']])
        yellow = len([r for r in results.values() if r.get('confidence', 0) > 40 and r.get('signal') == 'HOLD'])
        
        return {
            "signals": results,
            "summary": {
                "total": total,
                "green_signals": green,
                "yellow_signals": yellow,
                "red_signals": total - green - yellow
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching signals status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@signals_router.get("/{commodity}")
async def get_signal_for_commodity(commodity: str):
    """Get signal for a specific commodity"""
    try:
        result = await get_signals_status()
        
        if commodity in result.get("signals", {}):
            return result["signals"][commodity]
        else:
            raise HTTPException(status_code=404, detail=f"Commodity {commodity} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching signal for {commodity}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export
__all__ = ['signals_router']
