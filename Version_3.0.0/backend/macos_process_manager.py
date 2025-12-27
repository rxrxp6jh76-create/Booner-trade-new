"""
🍎 macOS PROCESS MANAGER - V2.5.0
==================================

Spezielle Optimierungen für MacBook Air M4 (Apple Silicon):

1. CPU Throttle Management - Verhindert Überhitzung auf fanless Mac
2. Process Hard-Kill - SIGKILL für Zombie Wine/MT5 Prozesse
3. Memory Management - Cleanup nach jedem Zyklus
4. Socket Timeouts - Verhindert Hängen bei MT5 Connection Drops
5. Non-Blocking Architecture - GUI bleibt responsive

Autor: AI Trading System V2.5.0
"""

import os
import sys
import gc
import time
import signal
import logging
import asyncio
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from functools import wraps

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# PSUTIL IMPORT (mit Fallback)
# ═══════════════════════════════════════════════════════════════════════════

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("⚠️ psutil nicht verfügbar - Process Management eingeschränkt")


# ═══════════════════════════════════════════════════════════════════════════
# CPU THROTTLE MANAGER (Thermal Management für M4)
# ═══════════════════════════════════════════════════════════════════════════

class CPUThrottleManager:
    """
    Verhindert CPU-Spikes auf dem fanless MacBook Air M4.
    Fügt strategische Pausen ein, um Thermal Throttling zu vermeiden.
    """
    
    # Konfiguration
    DEFAULT_SLEEP_INTERVAL = 0.1  # 100ms Standard-Pause
    HIGH_LOAD_SLEEP = 0.3         # 300ms bei hoher Last
    LOW_LOAD_SLEEP = 0.05         # 50ms bei niedriger Last
    
    # CPU Thresholds
    HIGH_CPU_THRESHOLD = 70       # % CPU → längere Pause
    CRITICAL_CPU_THRESHOLD = 85   # % CPU → noch längere Pause
    
    _last_cpu_check = 0
    _cpu_usage = 0
    
    @classmethod
    def get_optimal_sleep(cls) -> float:
        """
        Berechnet optimale Sleep-Zeit basierend auf CPU-Auslastung.
        """
        if not PSUTIL_AVAILABLE:
            return cls.DEFAULT_SLEEP_INTERVAL
        
        try:
            # CPU nur alle 2 Sekunden prüfen (um Overhead zu reduzieren)
            now = time.time()
            if now - cls._last_cpu_check > 2:
                cls._cpu_usage = psutil.cpu_percent(interval=0.1)
                cls._last_cpu_check = now
            
            if cls._cpu_usage >= cls.CRITICAL_CPU_THRESHOLD:
                logger.debug(f"🌡️ CPU kritisch: {cls._cpu_usage}% → Sleep {cls.HIGH_LOAD_SLEEP * 2}s")
                return cls.HIGH_LOAD_SLEEP * 2
            elif cls._cpu_usage >= cls.HIGH_CPU_THRESHOLD:
                logger.debug(f"🌡️ CPU hoch: {cls._cpu_usage}% → Sleep {cls.HIGH_LOAD_SLEEP}s")
                return cls.HIGH_LOAD_SLEEP
            else:
                return cls.DEFAULT_SLEEP_INTERVAL
                
        except Exception as e:
            logger.debug(f"CPU Check Fehler: {e}")
            return cls.DEFAULT_SLEEP_INTERVAL
    
    @classmethod
    def throttle(cls):
        """
        Fügt eine adaptive Pause ein basierend auf CPU-Last.
        Sollte am Ende jeder Main-Loop aufgerufen werden.
        """
        sleep_time = cls.get_optimal_sleep()
        time.sleep(sleep_time)
    
    @classmethod
    async def async_throttle(cls):
        """Async Version für asyncio Loops"""
        sleep_time = cls.get_optimal_sleep()
        await asyncio.sleep(sleep_time)
    
    @classmethod
    def get_system_stats(cls) -> Dict:
        """Gibt aktuelle System-Statistiken zurück"""
        if not PSUTIL_AVAILABLE:
            return {'available': False}
        
        try:
            return {
                'available': True,
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'memory_available_gb': psutil.virtual_memory().available / (1024**3),
                'swap_percent': psutil.swap_memory().percent if hasattr(psutil, 'swap_memory') else 0
            }
        except Exception as e:
            return {'available': False, 'error': str(e)}


# ═══════════════════════════════════════════════════════════════════════════
# PROCESS KILLER (macOS SIGKILL für Zombie Prozesse)
# ═══════════════════════════════════════════════════════════════════════════

class ProcessKiller:
    """
    macOS-spezifischer Process Killer mit SIGKILL.
    Beendet hängende Python/Wine/MT5 Prozesse.
    """
    
    # Prozessnamen die beendet werden sollen
    TARGET_PROCESS_NAMES = [
        'wine',
        'wine64',
        'wineserver',
        'terminal64.exe',
        'metatrader',
        'mt5',
        'MetaTrader',
    ]
    
    # Prozesse die NICHT beendet werden sollen
    PROTECTED_PROCESSES = [
        'kernel_task',
        'launchd',
        'WindowServer',
        'loginwindow',
    ]
    
    @classmethod
    def find_zombie_processes(cls) -> List[Dict]:
        """
        Findet alle Zombie/hängenden Prozesse.
        """
        if not PSUTIL_AVAILABLE:
            return []
        
        zombies = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    name = info.get('name', '').lower()
                    status = info.get('status', '')
                    
                    # Prüfe auf Zombie-Status
                    is_zombie = status in ['zombie', 'stopped']
                    
                    # Prüfe auf bekannte problematische Prozesse
                    is_target = any(target.lower() in name for target in cls.TARGET_PROCESS_NAMES)
                    
                    # Prüfe auf hängende Python-Prozesse (hohe CPU ohne Aktivität)
                    is_hanging_python = (
                        'python' in name and 
                        info.get('cpu_percent', 0) < 1 and 
                        info.get('memory_percent', 0) > 5
                    )
                    
                    if is_zombie or is_target or is_hanging_python:
                        zombies.append({
                            'pid': info['pid'],
                            'name': info['name'],
                            'status': status,
                            'reason': 'zombie' if is_zombie else ('target' if is_target else 'hanging')
                        })
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error(f"Fehler beim Finden von Zombie-Prozessen: {e}")
        
        return zombies
    
    @classmethod
    def kill_process(cls, pid: int, force: bool = True) -> bool:
        """
        Beendet einen Prozess mit SIGKILL (macOS).
        
        Args:
            pid: Process ID
            force: True = SIGKILL, False = SIGTERM erst versuchen
            
        Returns:
            True wenn erfolgreich
        """
        if not PSUTIL_AVAILABLE:
            # Fallback mit os.kill
            try:
                os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
                logger.info(f"🔪 Prozess {pid} beendet (os.kill)")
                return True
            except Exception as e:
                logger.error(f"Fehler beim Beenden von Prozess {pid}: {e}")
                return False
        
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            
            # Geschützte Prozesse nicht beenden
            if any(protected in name.lower() for protected in cls.PROTECTED_PROCESSES):
                logger.warning(f"⚠️ Prozess {name} ({pid}) ist geschützt")
                return False
            
            if force:
                # Direktes SIGKILL
                proc.kill()
                logger.info(f"🔪 Prozess {name} ({pid}) mit SIGKILL beendet")
            else:
                # Erst SIGTERM, dann SIGKILL
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except psutil.TimeoutExpired:
                    proc.kill()
                    logger.info(f"🔪 Prozess {name} ({pid}) mit SIGKILL beendet (nach SIGTERM Timeout)")
            
            return True
            
        except psutil.NoSuchProcess:
            logger.debug(f"Prozess {pid} existiert nicht mehr")
            return True
        except psutil.AccessDenied:
            logger.error(f"Keine Berechtigung zum Beenden von Prozess {pid}")
            return False
        except Exception as e:
            logger.error(f"Fehler beim Beenden von Prozess {pid}: {e}")
            return False
    
    @classmethod
    def kill_all_zombies(cls) -> Dict:
        """
        Beendet alle gefundenen Zombie-Prozesse.
        
        Returns:
            Statistik über beendete Prozesse
        """
        zombies = cls.find_zombie_processes()
        
        result = {
            'found': len(zombies),
            'killed': 0,
            'failed': 0,
            'details': []
        }
        
        for zombie in zombies:
            if cls.kill_process(zombie['pid'], force=True):
                result['killed'] += 1
                result['details'].append(f"✅ {zombie['name']} ({zombie['pid']})")
            else:
                result['failed'] += 1
                result['details'].append(f"❌ {zombie['name']} ({zombie['pid']})")
        
        logger.info(f"🧹 Zombie Cleanup: {result['killed']}/{result['found']} beendet")
        return result
    
    @classmethod
    def force_reload(cls) -> Dict:
        """
        Force Reload für macOS:
        1. Beende alle Zombie-Prozesse
        2. Garbage Collection
        3. Memory Cleanup
        
        Returns:
            Status-Dictionary
        """
        result = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'zombies': {},
            'memory_freed': 0,
            'gc_collected': 0
        }
        
        # 1. Zombie-Prozesse beenden
        result['zombies'] = cls.kill_all_zombies()
        
        # 2. Garbage Collection
        gc.collect()
        result['gc_collected'] = gc.get_count()
        
        # 3. Memory Stats
        if PSUTIL_AVAILABLE:
            try:
                mem = psutil.virtual_memory()
                result['memory_available_mb'] = mem.available / (1024**2)
                result['memory_percent'] = mem.percent
            except:
                pass
        
        logger.info(f"🔄 Force Reload abgeschlossen: {result}")
        return result


# ═══════════════════════════════════════════════════════════════════════════
# MEMORY MANAGER (Verhindert Memory Leaks)
# ═══════════════════════════════════════════════════════════════════════════

class MemoryManager:
    """
    Memory Management für lange Sessions.
    Verhindert "Black Screen" durch Memory Leaks.
    """
    
    # Thresholds
    WARNING_MEMORY_PERCENT = 80
    CRITICAL_MEMORY_PERCENT = 90
    
    _large_objects = []  # Tracking von großen Objekten
    
    @classmethod
    def track_large_object(cls, obj: Any, name: str = "unknown"):
        """Registriert ein großes Objekt für späteren Cleanup"""
        cls._large_objects.append({
            'ref': id(obj),
            'name': name,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    @classmethod
    def cleanup_tracked_objects(cls):
        """Bereinigt alle getrackten Objekte"""
        cls._large_objects.clear()
        gc.collect()
        logger.debug("🧹 Tracked objects cleaned up")
    
    @classmethod
    def check_memory_health(cls) -> Dict:
        """
        Prüft Memory-Gesundheit und gibt Warnung aus.
        """
        if not PSUTIL_AVAILABLE:
            return {'healthy': True, 'available': False}
        
        try:
            mem = psutil.virtual_memory()
            
            result = {
                'healthy': True,
                'percent': mem.percent,
                'available_mb': mem.available / (1024**2),
                'warning': None
            }
            
            if mem.percent >= cls.CRITICAL_MEMORY_PERCENT:
                result['healthy'] = False
                result['warning'] = f"🚨 KRITISCH: Memory bei {mem.percent}%!"
                logger.warning(result['warning'])
                # Automatischer Cleanup
                cls.emergency_cleanup()
                
            elif mem.percent >= cls.WARNING_MEMORY_PERCENT:
                result['warning'] = f"⚠️ WARNUNG: Memory bei {mem.percent}%"
                logger.warning(result['warning'])
            
            return result
            
        except Exception as e:
            return {'healthy': True, 'error': str(e)}
    
    @classmethod
    def emergency_cleanup(cls):
        """
        Notfall-Cleanup bei kritischem Memory.
        """
        logger.warning("🚨 Emergency Memory Cleanup gestartet...")
        
        # 1. Tracked Objects löschen
        cls.cleanup_tracked_objects()
        
        # 2. Aggressives GC
        for _ in range(3):
            gc.collect()
        
        # 3. Cache leeren (falls vorhanden)
        try:
            import importlib
            import sys
            
            # __pycache__ Einträge löschen
            modules_to_reload = [m for m in sys.modules.keys() if 'trading' in m or 'bot' in m]
            for mod in modules_to_reload:
                if mod in sys.modules and hasattr(sys.modules[mod], '__cached__'):
                    try:
                        del sys.modules[mod].__cached__
                    except:
                        pass
        except:
            pass
        
        logger.info("🧹 Emergency Cleanup abgeschlossen")
    
    @classmethod
    def get_memory_stats(cls) -> Dict:
        """Gibt detaillierte Memory-Statistiken zurück"""
        if not PSUTIL_AVAILABLE:
            return {'available': False}
        
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory() if hasattr(psutil, 'swap_memory') else None
            
            return {
                'available': True,
                'total_gb': mem.total / (1024**3),
                'available_gb': mem.available / (1024**3),
                'used_gb': mem.used / (1024**3),
                'percent': mem.percent,
                'swap_percent': swap.percent if swap else 0,
                'gc_counts': gc.get_count()
            }
        except Exception as e:
            return {'available': False, 'error': str(e)}


# ═══════════════════════════════════════════════════════════════════════════
# TIMEOUT WRAPPER (Verhindert Hängen bei MT5 Calls)
# ═══════════════════════════════════════════════════════════════════════════

class TimeoutWrapper:
    """
    Socket Timeout Wrapper für MT5 Calls.
    Verhindert endloses Warten bei dropped connections.
    """
    
    DEFAULT_TIMEOUT = 30  # Sekunden
    
    @classmethod
    def with_timeout(cls, timeout: int = None):
        """
        Decorator für synchrone Funktionen mit Timeout.
        
        Usage:
            @TimeoutWrapper.with_timeout(10)
            def my_function():
                ...
        """
        timeout = timeout or cls.DEFAULT_TIMEOUT
        
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(func, *args, **kwargs)
                    try:
                        return future.result(timeout=timeout)
                    except FuturesTimeoutError:
                        logger.error(f"⏰ Timeout ({timeout}s) für {func.__name__}")
                        raise TimeoutError(f"Function {func.__name__} timed out after {timeout}s")
            return wrapper
        return decorator
    
    @classmethod
    async def async_with_timeout(cls, coro, timeout: int = None, default: Any = None):
        """
        Async Timeout Wrapper.
        
        Usage:
            result = await TimeoutWrapper.async_with_timeout(
                my_async_function(),
                timeout=10,
                default=None
            )
        """
        timeout = timeout or cls.DEFAULT_TIMEOUT
        
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"⏰ Async Timeout ({timeout}s)")
            return default
    
    @classmethod
    def wrap_mt5_call(cls, func: Callable, timeout: int = 15):
        """
        Spezieller Wrapper für MT5 API Calls.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(func, *args, **kwargs)
                    return future.result(timeout=timeout)
            except FuturesTimeoutError:
                logger.error(f"⏰ MT5 Call Timeout: {func.__name__}")
                # Trigger Force Reload bei MT5 Timeout
                ProcessKiller.force_reload()
                return None
            except Exception as e:
                logger.error(f"MT5 Call Error: {e}")
                return None
        return wrapper


# ═══════════════════════════════════════════════════════════════════════════
# LATENCY TRACKER (für Self-Learning)
# ═══════════════════════════════════════════════════════════════════════════

class LatencyTracker:
    """
    Trackt Latenz nach Tageszeit für Self-Learning.
    Blockiert automatisch Zeiten mit hoher Latenz.
    """
    
    _latency_history = {}  # {hour: [latency_ms, ...]}
    _blocked_hours = set()
    
    HIGH_LATENCY_THRESHOLD_MS = 5000  # 5 Sekunden
    BLOCK_AFTER_N_HIGH_LATENCY = 3
    
    @classmethod
    def record_latency(cls, latency_ms: float):
        """Speichert Latenz für aktuelle Stunde"""
        hour = datetime.now().hour
        
        if hour not in cls._latency_history:
            cls._latency_history[hour] = []
        
        cls._latency_history[hour].append(latency_ms)
        
        # Nur letzte 20 Werte behalten
        if len(cls._latency_history[hour]) > 20:
            cls._latency_history[hour] = cls._latency_history[hour][-20:]
        
        # Prüfe ob Hour blockiert werden soll
        high_latency_count = sum(
            1 for l in cls._latency_history[hour][-10:] 
            if l > cls.HIGH_LATENCY_THRESHOLD_MS
        )
        
        if high_latency_count >= cls.BLOCK_AFTER_N_HIGH_LATENCY:
            cls._blocked_hours.add(hour)
            logger.warning(f"⏰ Stunde {hour}:00 blockiert wegen hoher Latenz")
    
    @classmethod
    def is_hour_blocked(cls, hour: int = None) -> bool:
        """Prüft ob eine Stunde blockiert ist"""
        hour = hour if hour is not None else datetime.now().hour
        return hour in cls._blocked_hours
    
    @classmethod
    def get_stats(cls) -> Dict:
        """Gibt Latenz-Statistiken zurück"""
        stats = {}
        for hour, latencies in cls._latency_history.items():
            if latencies:
                stats[hour] = {
                    'avg_ms': sum(latencies) / len(latencies),
                    'max_ms': max(latencies),
                    'count': len(latencies),
                    'blocked': hour in cls._blocked_hours
                }
        return stats


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    'CPUThrottleManager',
    'ProcessKiller', 
    'MemoryManager',
    'TimeoutWrapper',
    'LatencyTracker',
    'PSUTIL_AVAILABLE'
]
