"""
Centralized logging configuration following industry standards.

This module provides a comprehensive logging setup with:
- Structured JSON logging for production
- Human-readable console logging for development
- Log rotation and retention policies
- Different log levels for different components
- Request ID tracking for distributed tracing
- Security-conscious logging (no sensitive data)
"""

import logging
import logging.config
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import json
import uuid
from contextvars import ContextVar

# Context variable for request tracking
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdFilter(logging.Filter):
    """Add request ID to log records for tracing."""

    def filter(self, record):
        record.request_id = request_id_var.get("")
        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": getattr(record, "request_id", ""),
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry)


class ColoredConsoleFormatter(logging.Formatter):
    """Colored console formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET

        # Format the message
        formatted = super().format(record)

        # Add color if terminal supports it
        if hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
            formatted = f"{color}{formatted}{reset}"

        return formatted


def setup_logging(
    environment: str = None, log_level: str = None, log_dir: str = "logs"
) -> None:
    """
    Setup logging configuration based on environment.

    Args:
        environment: 'development', 'production', or 'testing'
        log_level: Override default log level
        log_dir: Directory for log files
    """

    # Determine environment
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development").lower()

    # Determine log level
    if log_level is None:
        log_level = os.getenv(
            "LOG_LEVEL", "INFO" if environment == "production" else "DEBUG"
        )

    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Base configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {
                "()": RequestIdFilter,
            },
        },
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "console": {
                "()": ColoredConsoleFormatter,
                "format": "%(asctime)s | %(levelname)-8s | %(name)-20s | %(request_id)-8s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "file": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)-20s | %(request_id)-8s | %(funcName)s:%(lineno)d | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {},
        "loggers": {},
        "root": {
            "level": log_level,
            "handlers": [],
        },
    }

    # Console handler (always present)
    config["handlers"]["console"] = {
        "class": "logging.StreamHandler",
        "level": log_level,
        "formatter": "json" if environment == "production" else "console",
        "filters": ["request_id"],
        "stream": "ext://sys.stdout",
    }
    config["root"]["handlers"].append("console")

    # File handlers for non-testing environments
    if environment != "testing":
        # Application log file with rotation
        config["handlers"]["app_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "json" if environment == "production" else "file",
            "filters": ["request_id"],
            "filename": str(log_path / "app.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8",
        }
        config["root"]["handlers"].append("app_file")

        # Error log file (ERROR and above only)
        config["handlers"]["error_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "json" if environment == "production" else "file",
            "filters": ["request_id"],
            "filename": str(log_path / "error.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 10,
            "encoding": "utf-8",
        }
        config["root"]["handlers"].append("error_file")

    # Configure specific loggers
    config["loggers"].update(
        {
            # FastAPI and Uvicorn
            "uvicorn": {
                "level": "INFO",
                "handlers": [],
                "propagate": True,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": [],
                "propagate": True,
            },
            "fastapi": {
                "level": "INFO",
                "handlers": [],
                "propagate": True,
            },
            # Application modules
            "main": {
                "level": log_level,
                "handlers": [],
                "propagate": True,
            },
            "agents": {
                "level": log_level,
                "handlers": [],
                "propagate": True,
            },
            "tools": {
                "level": log_level,
                "handlers": [],
                "propagate": True,
            },
            "task": {
                "level": log_level,
                "handlers": [],
                "propagate": True,
            },
            # CrewAI (reduce verbosity in production)
            "crewai": {
                "level": "WARNING" if environment == "production" else "INFO",
                "handlers": [],
                "propagate": True,
            },
            # OpenAI (reduce verbosity)
            "openai": {
                "level": "WARNING",
                "handlers": [],
                "propagate": True,
            },
            "httpx": {
                "level": "WARNING",
                "handlers": [],
                "propagate": True,
            },
        }
    )

    # Apply configuration
    logging.config.dictConfig(config)

    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "extra_fields": {
                "environment": environment,
                "log_level": log_level,
                "log_dir": str(log_path),
            }
        },
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


def set_request_id(request_id: str = None) -> str:
    """Set request ID for current context. Returns the set request ID."""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> str:
    """Get current request ID."""
    return request_id_var.get("")


def log_function_call(logger: logging.Logger):
    """Decorator to log function calls with parameters and execution time."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            import inspect

            start_time = time.time()
            func_name = func.__name__

            # Get function signature for logging (be careful with sensitive data)
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Filter out sensitive parameters
            safe_args = {}
            for param_name, param_value in bound_args.arguments.items():
                if any(
                    sensitive in param_name.lower()
                    for sensitive in ["password", "token", "key", "secret"]
                ):
                    safe_args[param_name] = "[REDACTED]"
                elif isinstance(param_value, str) and len(param_value) > 100:
                    safe_args[param_name] = f"[STRING:{len(param_value)} chars]"
                else:
                    safe_args[param_name] = param_value

            logger.debug(
                f"Calling {func_name}",
                extra={"extra_fields": {"function_args": safe_args}},
            )

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                logger.debug(
                    f"Completed {func_name}",
                    extra={
                        "extra_fields": {
                            "execution_time_seconds": round(execution_time, 3),
                            "success": True,
                        }
                    },
                )
                return result

            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Error in {func_name}: {str(e)}",
                    extra={
                        "extra_fields": {
                            "execution_time_seconds": round(execution_time, 3),
                            "success": False,
                            "error_type": type(e).__name__,
                        }
                    },
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


# Initialize logging on import if not already configured
if not logging.getLogger().handlers:
    setup_logging()
