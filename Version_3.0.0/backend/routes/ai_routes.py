"""
🧠 Booner Trade V3.1.0 - AI Routes

Enthält alle KI-bezogenen API-Endpunkte:
- Bayesian Self-Learning
- Spread-Analyse
- Pillar-Effizienz
- Weight-Optimierung
- Auditor Log
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

ai_router = APIRouter(prefix="/ai", tags=["AI Intelligence"])


@ai_router.get("/weight-history")
async def get_weight_history(asset: str = "GOLD", limit: int = 30):
    """
    Liefert die Historie der Gewichts-Änderungen für ein Asset.
    """
    try:
        from database_v2 import get_trades_db
        trades_db = await get_trades_db()
        
        query = """
            SELECT * FROM pillar_weights_history 
            WHERE asset = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        cursor = await trades_db._conn.execute(query, (asset, limit))
        rows = await cursor.fetchall()
        
        if rows:
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        
        # Fallback: Demo-Daten
        return [
            {
                "asset": asset,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "base_signal_weight": 25,
                "trend_confluence_weight": 25,
                "volatility_weight": 25,
                "sentiment_weight": 25,
                "win_rate": 55,
                "trades_analyzed": 0
            }
        ]
        
    except Exception as e:
        logger.error(f"Error fetching weight history: {e}")
        return []


@ai_router.get("/pillar-efficiency")
async def get_pillar_efficiency(asset: str = "GOLD"):
    """
    Liefert die Effizienz-Scores für jede Säule.
    """
    try:
        from booner_intelligence_engine import get_booner_engine
        engine = get_booner_engine()
        efficiency = await engine.analyze_pillar_efficiency(asset)
        return efficiency
    except ImportError:
        return {
            'base_signal': 50,
            'trend_confluence': 50,
            'volatility': 50,
            'sentiment': 50
        }
    except Exception as e:
        logger.error(f"Error getting pillar efficiency: {e}")
        return {
            'base_signal': 50,
            'trend_confluence': 50,
            'volatility': 50,
            'sentiment': 50,
            'error': str(e)
        }


@ai_router.get("/auditor-log")
async def get_auditor_log(limit: int = 10):
    """
    Liefert das Auditor-Log der letzten Entscheidungen.
    """
    try:
        from booner_intelligence_engine import get_booner_engine
        engine = get_booner_engine()
        
        logs = []
        for entry in list(engine.auditor_log)[-limit:]:
            logs.append({
                'timestamp': entry.timestamp,
                'asset': entry.asset,
                'original_action': entry.original_action,
                'final_action': entry.final_action,
                'blocked': entry.blocked,
                'red_flags': entry.red_flags,
                'auditor_reasoning': entry.auditor_reasoning,
                'confidence': entry.confidence_score
            })
        
        return logs[::-1]  # Neueste zuerst
        
    except ImportError:
        return []
    except Exception as e:
        logger.error(f"Error getting auditor log: {e}")
        return []


@ai_router.get("/spread-analysis")
async def get_spread_analysis(asset: str = None, limit: int = 20):
    """
    V3.1.0: Liefert Spread-Analyse-Daten für das Frontend.
    """
    try:
        from database_v2 import get_trades_db
        trades_db = await get_trades_db()
        
        if asset:
            query = """
                SELECT * FROM trade_settings 
                WHERE symbol = ? AND spread IS NOT NULL
                ORDER BY created_at DESC
                LIMIT ?
            """
            cursor = await trades_db._conn.execute(query, (asset, limit))
        else:
            query = """
                SELECT * FROM trade_settings 
                WHERE spread IS NOT NULL
                ORDER BY created_at DESC
                LIMIT ?
            """
            cursor = await trades_db._conn.execute(query, (limit,))
        
        rows = await cursor.fetchall()
        
        if rows:
            columns = [desc[0] for desc in cursor.description]
            result = []
            
            for row in rows:
                entry = dict(zip(columns, row))
                spread_percent = entry.get('spread_percent', 0) or 0
                
                if spread_percent < 0.1:
                    entry['spread_status'] = 'EXCELLENT'
                elif spread_percent < 0.3:
                    entry['spread_status'] = 'ACCEPTABLE'
                elif spread_percent < 0.5:
                    entry['spread_status'] = 'HIGH'
                else:
                    entry['spread_status'] = 'EXTREME'
                
                if entry.get('sl_percent') and entry.get('spread_percent'):
                    entry['sl_adjustment_percent'] = entry['spread_percent'] * 1.5
                
                result.append(entry)
            
            return result
        
        return []
        
    except Exception as e:
        logger.error(f"Error fetching spread analysis: {e}")
        return []


@ai_router.get("/learning-stats")
async def get_learning_stats(days: int = 30):
    """
    V3.1.0: Liefert Statistiken über das Bayesian Self-Learning System.
    """
    try:
        from booner_intelligence_engine import get_booner_engine
        engine = get_booner_engine()
        stats = await engine.get_learning_statistics(days)
        return stats
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Error from engine: {e}")
    
    # Fallback
    return {
        'total_optimizations': 0,
        'avg_win_rate': 0,
        'assets_optimized': [],
        'weight_drift': {},
        'pillar_performance': {
            'base_signal': {'avg_contribution': 25, 'win_correlation': 0.5},
            'trend_confluence': {'avg_contribution': 25, 'win_correlation': 0.5},
            'volatility': {'avg_contribution': 25, 'win_correlation': 0.5},
            'sentiment': {'avg_contribution': 25, 'win_correlation': 0.5}
        },
        'learning_rate': 0.05,
        'min_weight': 5.0,
        'max_weight': 60.0
    }


@ai_router.post("/learn-from-trade")
async def learn_from_trade(trade_data: dict):
    """
    V3.1.0: Trigger Bayesian Learning von einem abgeschlossenen Trade.
    """
    try:
        from booner_intelligence_engine import get_booner_engine
        engine = get_booner_engine()
        
        was_profitable = trade_data.get('profit_loss', 0) > 0
        
        result = await engine.learn_from_trade_result(
            trade_data=trade_data,
            was_profitable=was_profitable
        )
        
        return {
            "status": "ok",
            "learned": True,
            "was_profitable": was_profitable,
            "weight_changes": result.get('weight_changes', {}),
            "commodity": result.get('commodity')
        }
        
    except ImportError:
        return {"status": "error", "message": "Booner Intelligence Engine nicht verfügbar"}
    except Exception as e:
        logger.error(f"Error in learning from trade: {e}")
        return {"status": "error", "message": str(e)}


@ai_router.get("/pillar-efficiency-detailed")
async def get_pillar_efficiency_detailed(asset: str = "GOLD"):
    """
    V3.1.0: Detaillierte Säulen-Effizienz mit Trend-Daten.
    """
    try:
        from booner_intelligence_engine import get_booner_engine
        engine = get_booner_engine()
        
        efficiency = await engine.analyze_pillar_efficiency(asset)
        weight_history = await engine.get_weight_history(asset, limit=10)
        
        # Generiere Empfehlung
        best_pillar = max(efficiency, key=efficiency.get)
        worst_pillar = min(efficiency, key=efficiency.get)
        
        pillar_names = {
            'base_signal': 'Basis-Signal',
            'trend_confluence': 'Trend-Konfluenz',
            'volatility': 'Volatilität',
            'sentiment': 'Sentiment'
        }
        
        if efficiency[best_pillar] > 65:
            recommendation = f"Stärke: {pillar_names.get(best_pillar, best_pillar)} ({efficiency[best_pillar]:.0f}%). Mehr Gewicht empfohlen."
        elif efficiency[worst_pillar] < 40:
            recommendation = f"Schwäche: {pillar_names.get(worst_pillar, worst_pillar)} ({efficiency[worst_pillar]:.0f}%). Weniger Gewicht empfohlen."
        else:
            recommendation = "Alle Säulen im Normalbereich. Keine Anpassung nötig."
        
        return {
            "asset": asset,
            "efficiency": efficiency,
            "weight_history": weight_history,
            "recommendation": recommendation
        }
        
    except ImportError:
        return {
            "asset": asset,
            "efficiency": {
                'base_signal': 50,
                'trend_confluence': 55,
                'volatility': 45,
                'sentiment': 40
            },
            "weight_history": [],
            "recommendation": "Engine nicht verfügbar"
        }
    except Exception as e:
        logger.error(f"Error getting detailed efficiency: {e}")
        return {"error": str(e)}


@ai_router.post("/trigger-optimization")
async def trigger_optimization(asset: str = None):
    """
    Manueller Trigger für Gewichts-Optimierung.
    """
    try:
        from booner_intelligence_engine import get_booner_engine
        engine = get_booner_engine()
        
        if asset:
            result = await engine.optimize_weights_for_asset(asset)
        else:
            result = await engine.optimize_all_weights()
        
        return {
            "status": "ok",
            "optimized": True,
            "result": result
        }
        
    except ImportError:
        return {"status": "error", "message": "Booner Intelligence Engine nicht verfügbar"}
    except Exception as e:
        logger.error(f"Error triggering optimization: {e}")
        return {"status": "error", "message": str(e)}


# Export router
__all__ = ['ai_router']
