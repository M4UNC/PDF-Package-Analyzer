#!/usr/bin/env python3
"""
Utility functions for PDF analysis.
"""

import threading
import queue
from typing import Dict, Any, Callable


def run_with_timeout(func: Callable, timeout_seconds: int, *args, **kwargs) -> Dict[str, Any]:
    """Run a function with timeout using threading approach."""
    result_queue = queue.Queue()
    exception_queue = queue.Queue()
    
    def worker():
        try:
            result = func(*args, **kwargs)
            result_queue.put(result)
        except Exception as e:
            exception_queue.put(e)
    
    # Start the worker thread
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    
    # Wait for completion or timeout
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        # Thread is still running, timeout occurred
        return {
            "success": False,
            "error": f"Operation timed out after {timeout_seconds} seconds",
            "timeout": True
        }
    else:
        # Thread completed, check for results
        if not result_queue.empty():
            return result_queue.get()
        elif not exception_queue.empty():
            exception = exception_queue.get()
            return {
                "success": False,
                "error": f"Operation failed: {str(exception)}",
                "timeout": False
            }
        else:
            return {
                "success": False,
                "error": "Operation completed but no result returned",
                "timeout": False
            }
