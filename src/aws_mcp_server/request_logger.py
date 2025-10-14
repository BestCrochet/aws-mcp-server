"""Request logging for AWS MCP Server.

This module provides structured JSON logging for all MCP requests, tool calls,
and outputs. Logs are written to requests.log in JSON format suitable for Splunk ingestion.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from functools import wraps
import inspect

logger = logging.getLogger(__name__)


class RequestLogger:
    """Handles structured JSON logging of MCP server requests and responses."""

    def __init__(self, log_file: str = "requests.log"):
        """Initialize the request logger.
        
        Args:
            log_file: Path to the log file (default: requests.log)
        """
        self.log_file = Path(log_file)
        
        # Ensure the log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Request logger initialized. Logging to: {self.log_file.absolute()}")

    def log_request(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        output: Any,
        status: str,
        duration_ms: float,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log a complete request/response cycle as a single JSON entry.
        
        Args:
            tool_name: Name of the MCP tool being called
            input_params: Input parameters passed to the tool
            output: Output returned from the tool
            status: Status of the operation (success, error, warning)
            duration_ms: Duration of the operation in milliseconds
            error: Error message if applicable
            metadata: Additional metadata to include in the log
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "mcp_tool_call",
            "tool_name": tool_name,
            "input": self._sanitize_for_json(input_params),
            "output": self._sanitize_for_json(output),
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "error": error,
            "metadata": metadata or {},
        }
        
        # Write to log file as a single JSON line (JSONL format)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                json.dump(log_entry, f, ensure_ascii=False, default=str)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to write to request log: {e}")

    def _sanitize_for_json(self, obj: Any) -> Any:
        """Sanitize objects for JSON serialization.
        
        Args:
            obj: Object to sanitize
            
        Returns:
            JSON-serializable version of the object
        """
        if obj is None:
            return None
        
        # Handle dictionaries
        if isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
        
        # Handle lists and tuples
        if isinstance(obj, (list, tuple)):
            return [self._sanitize_for_json(item) for item in obj]
        
        # Handle primitive types
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        # Try to convert to dict if it has __dict__
        if hasattr(obj, "__dict__"):
            return self._sanitize_for_json(obj.__dict__)
        
        # Fall back to string representation
        return str(obj)

    def wrap_tool(self, func):
        """Decorator to wrap MCP tool functions with logging.
        
        Args:
            func: The tool function to wrap
            
        Returns:
            Wrapped function with logging
        """
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tool_name = func.__name__
            start_time = time.time()
            
            # Extract input parameters (excluding Context)
            input_params = {}
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            for param_name, param_value in bound_args.arguments.items():
                # Skip the Context parameter
                if param_name == "ctx":
                    continue
                input_params[param_name] = param_value
            
            # Execute the tool
            error = None
            status = "success"
            output = None
            
            try:
                output = await func(*args, **kwargs)
            except Exception as e:
                error = str(e)
                status = "error"
                output = {"error": error}
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                # Extract metadata
                metadata = {
                    "server": "aws-mcp-server",
                    "function": tool_name,
                }
                
                # Log the complete request/response
                self.log_request(
                    tool_name=tool_name,
                    input_params=input_params,
                    output=output,
                    status=status,
                    duration_ms=duration_ms,
                    error=error,
                    metadata=metadata,
                )
            
            return output
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tool_name = func.__name__
            start_time = time.time()
            
            # Extract input parameters
            input_params = {}
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            for param_name, param_value in bound_args.arguments.items():
                if param_name == "ctx":
                    continue
                input_params[param_name] = param_value
            
            # Execute the tool
            error = None
            status = "success"
            output = None
            
            try:
                output = func(*args, **kwargs)
            except Exception as e:
                error = str(e)
                status = "error"
                output = {"error": error}
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                metadata = {
                    "server": "aws-mcp-server",
                    "function": tool_name,
                }
                
                self.log_request(
                    tool_name=tool_name,
                    input_params=input_params,
                    output=output,
                    status=status,
                    duration_ms=duration_ms,
                    error=error,
                    metadata=metadata,
                )
            
            return output
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper


# Global request logger instance
_request_logger: Optional[RequestLogger] = None


def get_request_logger() -> RequestLogger:
    """Get or create the global request logger instance.
    
    Returns:
        The global RequestLogger instance
    """
    global _request_logger
    if _request_logger is None:
        _request_logger = RequestLogger()
    return _request_logger


def log_mcp_request(
    tool_name: str,
    input_params: Dict[str, Any],
    output: Any,
    status: str,
    duration_ms: float,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Convenience function to log an MCP request.
    
    Args:
        tool_name: Name of the MCP tool being called
        input_params: Input parameters passed to the tool
        output: Output returned from the tool
        status: Status of the operation (success, error, warning)
        duration_ms: Duration of the operation in milliseconds
        error: Error message if applicable
        metadata: Additional metadata to include in the log
    """
    logger_instance = get_request_logger()
    logger_instance.log_request(
        tool_name=tool_name,
        input_params=input_params,
        output=output,
        status=status,
        duration_ms=duration_ms,
        error=error,
        metadata=metadata,
    )
