"""
Memory optimization utilities for Lotus Electronics Chatbot
"""
import gc
import psutil
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process()
    memory_info = process.memory_info()
    return memory_info.rss / 1024 / 1024  # Convert to MB

def log_memory_usage(func_name=""):
    """Log current memory usage"""
    memory_mb = get_memory_usage()
    logger.info(f"💾 Memory usage {func_name}: {memory_mb:.1f} MB")
    return memory_mb

def memory_monitor(func):
    """Decorator to monitor memory usage of functions"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Log memory before
        memory_before = log_memory_usage(f"before {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Log memory after and cleanup
            memory_after = log_memory_usage(f"after {func.__name__}")
            memory_diff = memory_after - memory_before
            
            if memory_diff > 0:
                logger.info(f"🔺 Memory increased by {memory_diff:.1f} MB in {func.__name__}")
            
            # Force garbage collection if memory usage is high
            if memory_after > 500:  # 500MB threshold
                logger.warning(f"⚠️ High memory usage ({memory_after:.1f} MB), running garbage collection")
                gc.collect()
                memory_after_gc = get_memory_usage()
                logger.info(f"🗑️ Memory after GC: {memory_after_gc:.1f} MB (freed {memory_after - memory_after_gc:.1f} MB)")
    
    return wrapper

def cleanup_memory():
    """Force garbage collection and log memory usage"""
    memory_before = get_memory_usage()
    gc.collect()
    memory_after = get_memory_usage()
    freed = memory_before - memory_after
    logger.info(f"🗑️ Manual cleanup: freed {freed:.1f} MB (was {memory_before:.1f} MB, now {memory_after:.1f} MB)")
    return freed

def check_memory_limit(limit_mb=2000):
    """Check if memory usage exceeds limit"""
    memory_mb = get_memory_usage()
    if memory_mb > limit_mb:
        logger.warning(f"⚠️ Memory usage ({memory_mb:.1f} MB) exceeds limit ({limit_mb} MB)")
        cleanup_memory()
        return True
    return False

class MemoryTracker:
    """Context manager for tracking memory usage"""
    
    def __init__(self, operation_name="operation"):
        self.operation_name = operation_name
        self.start_memory = 0
    
    def __enter__(self):
        self.start_memory = log_memory_usage(f"starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_memory = log_memory_usage(f"finished {self.operation_name}")
        memory_diff = end_memory - self.start_memory
        
        if memory_diff > 50:  # 50MB threshold
            logger.warning(f"🔺 High memory usage in {self.operation_name}: +{memory_diff:.1f} MB")
            cleanup_memory()