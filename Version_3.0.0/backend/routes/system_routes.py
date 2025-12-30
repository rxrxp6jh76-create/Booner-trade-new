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
        "version": "3.1.0",
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
            "ai_managed_sl_tp": True
        }
    }


# Export router
__all__ = ['system_router']
