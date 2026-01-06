"""
🔧 Booner Trade V3.1.0 - System Routes

Enthält System-bezogene API-Endpunkte:
- Health Check
- Memory Monitoring
- Cleanup
- Backend Restart
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
import logging
import psutil
import os
import sys
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

system_router = APIRouter(prefix="/system", tags=["System"])


@system_router.get("/health")
async def health_check():
    """
    Umfassender Health-Check für alle Systemkomponenten.
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {},
        "version": "3.1.0"
    }
    
    # 1. Database
    try:
        from database_v2 import get_settings_db
        settings_db = await get_settings_db()
        await settings_db.get_settings()
        health["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health["components"]["database"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    # 2. MetaAPI
    try:
        from multi_platform_connector import multi_platform
        platforms_status = {}
        for pname in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO']:
            try:
                acc = await multi_platform.get_account_info(pname)
                platforms_status[pname] = "connected" if acc else "disconnected"
            except:
                platforms_status[pname] = "error"
        
        health["components"]["metaapi"] = {
            "status": "healthy" if any(s == "connected" for s in platforms_status.values()) else "degraded",
            "platforms": platforms_status
        }
    except Exception as e:
        health["components"]["metaapi"] = {"status": "unhealthy", "error": str(e)}
    
    # 3. Memory
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    health["components"]["memory"] = {
        "status": "healthy" if memory_mb < 500 else "warning",
        "usage_mb": round(memory_mb, 2)
    }
    
    # 4. Ollama (optional)
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags", timeout=2) as resp:
                health["components"]["ollama"] = {
                    "status": "healthy" if resp.status == 200 else "unavailable"
                }
    except:
        health["components"]["ollama"] = {"status": "unavailable"}
    
    return health


@system_router.get("/memory")
async def get_memory_stats():
    """
    Detaillierte Memory-Statistiken.
    """
    process = psutil.Process()
    mem_info = process.memory_info()
    
    return {
        "rss_mb": round(mem_info.rss / 1024 / 1024, 2),
        "vms_mb": round(mem_info.vms / 1024 / 1024, 2),
        "percent": process.memory_percent(),
        "system": {
            "total_mb": round(psutil.virtual_memory().total / 1024 / 1024, 2),
            "available_mb": round(psutil.virtual_memory().available / 1024 / 1024, 2),
            "percent": psutil.virtual_memory().percent
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@system_router.get("/cleanup")
async def cleanup_memory():
    """
    Führt Garbage Collection und Memory-Cleanup durch.
    """
    import gc
    
    before = psutil.Process().memory_info().rss / 1024 / 1024
    
    # Garbage Collection
    gc.collect()
    
    after = psutil.Process().memory_info().rss / 1024 / 1024
    
    return {
        "before_mb": round(before, 2),
        "after_mb": round(after, 2),
        "freed_mb": round(before - after, 2),
        "success": True
    }


@system_router.post("/restart-backend")
async def restart_backend():
    """
    Startet das Backend neu (für Server-Umgebungen).
    """
    import subprocess
    
    logger.warning("🔄 Backend-Neustart angefordert!")
    
    # Für Supervisor-Umgebung
    try:
        subprocess.Popen(
            ["sudo", "supervisorctl", "restart", "backend"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return {"status": "ok", "message": "Backend wird neu gestartet..."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@system_router.get("/info")
async def get_system_info():
    """
    Allgemeine System-Informationen.
    """
    return {
        "version": "3.2.7",
        "platform": sys.platform,
        "python_version": sys.version,
        "pid": os.getpid(),
        "cwd": os.getcwd(),
        "uptime_seconds": psutil.Process().create_time(),
        "cpu_count": psutil.cpu_count(),
        "features": {
            "spread_adjustment": True,
            "bayesian_learning": True,
            "4_pillar_engine": True,
            "imessage_bridge": True,
            "ai_managed_sl_tp": True,
            "portfolio_risk_check": True,  # V3.2.7
            "strategy_logging": True  # V3.2.7
        }
    }


@system_router.get("/strategy-logs")
async def get_strategy_logs(lines: int = 100):
    """
    V3.2.7: Hole die Strategie-Entscheidungs-Logs.
    Diese werden bei jedem Trade-Signal gespeichert.
    """
    import json
    import os
    from pathlib import Path
    
    # V3.2.8: Relativer Pfad für Mac-Kompatibilität
    base_dir = Path(__file__).parent.parent  # routes -> backend
    log_file = base_dir / 'logs' / 'strategy_decisions.log'
    
    # Erstelle Verzeichnis falls nicht existiert
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logs = []
    
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                for line in all_lines[-lines:]:
                    try:
                        entry = json.loads(line.strip())
                        logs.append(entry)
                    except:
                        pass
        except Exception as e:
            logger.error(f"Error reading strategy logs: {e}")
    
    # Statistiken berechnen
    strategy_counts = {}
    for log in logs:
        strat = log.get('strategy', 'unknown')
        strategy_counts[strat] = strategy_counts.get(strat, 0) + 1
    
    return {
        "total_entries": len(logs),
        "strategy_distribution": strategy_counts,
        "recent_decisions": logs[-20:],  # Letzte 20 Entscheidungen
        "log_file": str(log_file)
    }


@system_router.get("/logs")
async def get_logs(lines: int = 200, filter: Optional[str] = None):
    """
    V3.2.2: Hole die letzten Log-Zeilen für Debug-Zwecke.
    
    Args:
        lines: Anzahl der letzten Zeilen (default: 200)
        filter: Optional - Filter nach Stichwort (z.B. "strategy", "4-Pillar", "Signal")
    """
    import subprocess
    import os
    from pathlib import Path
    
    logs = {
        "backend": [],
        "strategy_decisions": [],
        "trade_executions": [],
        "errors": [],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        # V3.2.8: Relativer Pfad für Mac-Kompatibilität
        base_dir = Path(__file__).parent.parent  # routes -> backend
        
        # Backend Logs - Prüfe sowohl relative als auch absolute Pfade
        log_paths = [
            base_dir / 'logs' / 'backend.log',  # Relativ für Mac
        ]
        
        # Füge Supervisor-Logs nur hinzu wenn sie existieren (Server-Umgebung)
        supervisor_logs = [
            Path("/var/log/supervisor/backend.out.log"),
            Path("/var/log/supervisor/backend.err.log")
        ]
        for sl in supervisor_logs:
            if sl.exists():
                log_paths.append(sl)
        
        all_lines = []
        for log_path in log_paths:
            if log_path.exists():
                try:
                    # Lese letzte N Zeilen
                    result = subprocess.run(
                        ["tail", "-n", str(lines), str(log_path)],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.stdout:
                        all_lines.extend(result.stdout.strip().split('\n'))
                except Exception as e:
                    logger.warning(f"Could not read {log_path}: {e}")
        
        # Filtere und kategorisiere Logs
        for line in all_lines[-lines:]:
            if not line.strip():
                continue
                
            # Optional Filter anwenden
            if filter and filter.lower() not in line.lower():
                continue
            
            logs["backend"].append(line)
            
            # Kategorisiere nach Typ
            line_lower = line.lower()
            if "strategy" in line_lower or "4-pillar" in line_lower or "adx" in line_lower or "v3.2.2" in line_lower:
                logs["strategy_decisions"].append(line)
            if "execute" in line_lower or "trade" in line_lower or "signal" in line_lower:
                logs["trade_executions"].append(line)
            if "error" in line_lower or "❌" in line or "failed" in line_lower:
                logs["errors"].append(line)
        
        # Begrenze Ausgabe
        logs["backend"] = logs["backend"][-lines:]
        logs["strategy_decisions"] = logs["strategy_decisions"][-50:]
        logs["trade_executions"] = logs["trade_executions"][-50:]
        logs["errors"] = logs["errors"][-30:]
        
        logs["total_lines"] = len(logs["backend"])
        logs["strategy_count"] = len(logs["strategy_decisions"])
        logs["trade_count"] = len(logs["trade_executions"])
        logs["error_count"] = len(logs["errors"])
        
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        logs["error"] = str(e)
    
    return logs


@system_router.get("/strategy-stats")
async def get_strategy_stats():
    """
    V3.2.2: Statistiken über verwendete Strategien aus der Trade-Historie.
    Hilft bei der Diagnose, warum bestimmte Strategien nicht verwendet werden.
    """
    try:
        from database_v2 import db_manager
        
        # Hole alle Trades
        trades = await db_manager.trades_db.get_trades(status=None)  # Alle Trades
        
        strategy_stats = {}
        total_trades = 0
        
        for trade in trades:
            strategy = trade.get('strategy', 'unknown')
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {
                    'count': 0,
                    'profit': 0.0,
                    'last_trade': None
                }
            
            strategy_stats[strategy]['count'] += 1
            strategy_stats[strategy]['profit'] += trade.get('profit_loss', 0) or 0
            
            trade_time = trade.get('opened_at') or trade.get('timestamp')
            if trade_time:
                strategy_stats[strategy]['last_trade'] = trade_time
            
            total_trades += 1
        
        # Berechne Prozentsätze
        for strategy in strategy_stats:
            strategy_stats[strategy]['percentage'] = round(
                (strategy_stats[strategy]['count'] / total_trades * 100) if total_trades > 0 else 0, 
                1
            )
        
        return {
            "total_trades": total_trades,
            "strategies": strategy_stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analysis": {
                "most_used": max(strategy_stats.keys(), key=lambda k: strategy_stats[k]['count']) if strategy_stats else None,
                "most_profitable": max(strategy_stats.keys(), key=lambda k: strategy_stats[k]['profit']) if strategy_stats else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting strategy stats: {e}")
        return {"error": str(e)}


# Export router
__all__ = ['system_router']
