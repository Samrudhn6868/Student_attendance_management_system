"""Application profiling and instrumentation tools."""

import cProfile
import pstats
import io
import time
import functools
from typing import Callable, Any
import json
import os
from datetime import datetime


class PerformanceProfiler:
    """Profile application performance using cProfile."""
    
    def __init__(self, output_dir='reports/profiles'):
        """Initialize profiler with output directory."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def profile_function(self, func: Callable, *args, **kwargs) -> tuple:
        """
        Profile a specific function.
        
        Args:
            func: Function to profile
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        
        Returns:
            Tuple of (result, stats_string)
        """
        profiler = cProfile.Profile()
        profiler.enable()
        
        result = func(*args, **kwargs)
        
        profiler.disable()
        
        # Capture stats
        stats_stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stats_stream)
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # Top 20 functions
        
        return result, stats_stream.getvalue()
    
    def profile_to_file(self, func: Callable, filename: str, *args, **kwargs) -> Any:
        """
        Profile function and save stats to file.
        
        Args:
            func: Function to profile
            filename: Output filename
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        
        Returns:
            Function result
        """
        profiler = cProfile.Profile()
        profiler.enable()
        
        result = func(*args, **kwargs)
        
        profiler.disable()
        
        # Save stats
        filepath = os.path.join(self.output_dir, filename)
        profiler.dump_stats(filepath)
        
        # Also save human-readable version
        txt_filepath = filepath.replace('.prof', '.txt')
        with open(txt_filepath, 'w') as f:
            stats = pstats.Stats(profiler, stream=f)
            stats.sort_stats('cumulative')
            stats.print_stats()
        
        return result
    
    def profile_decorator(self, output_file: str = None):
        """
        Decorator to profile a function.
        
        Usage:
            @profiler.profile_decorator('my_function.prof')
            def my_function():
                pass
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if output_file:
                    return self.profile_to_file(func, output_file, *args, **kwargs)
                else:
                    result, stats = self.profile_function(func, *args, **kwargs)
                    print(f"\n=== Profile for {func.__name__} ===")
                    print(stats)
                    return result
            return wrapper
        return decorator


class TimingInstrumentor:
    """Instrument functions with timing measurements."""
    
    def __init__(self, log_file='reports/timing.json'):
        """Initialize instrumentor with log file."""
        self.log_file = log_file
        self.timings = []
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    def time_function(self, func: Callable) -> Callable:
        """
        Decorator to time function execution.
        
        Usage:
            @instrumentor.time_function
            def my_function():
                pass
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            
            duration = end_time - start_time
            
            timing_data = {
                'function': func.__name__,
                'module': func.__module__,
                'duration_seconds': duration,
                'timestamp': datetime.now().isoformat(),
                'args_count': len(args),
                'kwargs_count': len(kwargs)
            }
            
            self.timings.append(timing_data)
            
            # Log if slow
            if duration > 1.0:
                print(f"SLOW: {func.__name__} took {duration:.3f}s")
            
            return result
        return wrapper
    
    def save_timings(self):
        """Save timing data to JSON file."""
        with open(self.log_file, 'w') as f:
            json.dump(self.timings, f, indent=2)
    
    def get_statistics(self) -> dict:
        """Get timing statistics."""
        if not self.timings:
            return {}
        
        durations = [t['duration_seconds'] for t in self.timings]
        
        return {
            'total_calls': len(self.timings),
            'total_time': sum(durations),
            'mean_time': sum(durations) / len(durations),
            'min_time': min(durations),
            'max_time': max(durations),
            'slowest_call': max(self.timings, key=lambda x: x['duration_seconds'])
        }


class MemoryProfiler:
    """Profile memory usage of functions."""
    
    @staticmethod
    def memory_usage():
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return None
    
    def profile_memory(self, func: Callable) -> Callable:
        """
        Decorator to profile memory usage.
        
        Usage:
            @memory_profiler.profile_memory
            def my_function():
                pass
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            mem_before = self.memory_usage()
            result = func(*args, **kwargs)
            mem_after = self.memory_usage()
            
            if mem_before is not None and mem_after is not None:
                mem_diff = mem_after - mem_before
                print(f"{func.__name__} memory: {mem_before:.2f}MB -> {mem_after:.2f}MB "
                      f"(Δ {mem_diff:+.2f}MB)")
            
            return result
        return wrapper


class RequestLogger:
    """Log Flask request performance."""
    
    def __init__(self, app=None, log_file='reports/requests.json'):
        """Initialize request logger."""
        self.log_file = log_file
        self.requests = []
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app."""
        @app.before_request
        def before_request():
            from flask import g, request
            g.start_time = time.perf_counter()
            g.request_path = request.path
            g.request_method = request.method
        
        @app.after_request
        def after_request(response):
            from flask import g
            
            if hasattr(g, 'start_time'):
                duration = time.perf_counter() - g.start_time
                
                request_data = {
                    'path': getattr(g, 'request_path', 'unknown'),
                    'method': getattr(g, 'request_method', 'unknown'),
                    'status_code': response.status_code,
                    'duration_seconds': duration,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.requests.append(request_data)
                
                # Log slow requests
                if duration > 1.0:
                    print(f"SLOW REQUEST: {g.request_method} {g.request_path} "
                          f"took {duration:.3f}s")
            
            return response
    
    def save_logs(self):
        """Save request logs to file."""
        with open(self.log_file, 'w') as f:
            json.dump(self.requests, f, indent=2)
    
    def get_statistics(self) -> dict:
        """Get request statistics."""
        if not self.requests:
            return {}
        
        durations = [r['duration_seconds'] for r in self.requests]
        paths = [r['path'] for r in self.requests]
        status_codes = [r['status_code'] for r in self.requests]
        
        return {
            'total_requests': len(self.requests),
            'total_time': sum(durations),
            'mean_time': sum(durations) / len(durations),
            'min_time': min(durations),
            'max_time': max(durations),
            'unique_paths': len(set(paths)),
            'status_code_distribution': {
                code: status_codes.count(code) 
                for code in set(status_codes)
            },
            'slowest_request': max(self.requests, key=lambda x: x['duration_seconds'])
        }


# Global instances
profiler = PerformanceProfiler()
instrumentor = TimingInstrumentor()
memory_profiler = MemoryProfiler()


# Example usage decorators
def profile(output_file: str = None):
    """Shortcut decorator for profiling."""
    return profiler.profile_decorator(output_file)


def timed(func: Callable) -> Callable:
    """Shortcut decorator for timing."""
    return instrumentor.time_function(func)


def memory_tracked(func: Callable) -> Callable:
    """Shortcut decorator for memory tracking."""
    return memory_profiler.profile_memory(func)


if __name__ == '__main__':
    # Example usage
    @timed
    def example_function():
        """Example function to demonstrate profiling."""
        import time
        time.sleep(0.1)
        return sum(range(1000000))
    
    result = example_function()
    print(f"Result: {result}")
    
    # Save timings
    instrumentor.save_timings()
    
    # Print statistics
    stats = instrumentor.get_statistics()
    print("\nTiming Statistics:")
    print(json.dumps(stats, indent=2))
