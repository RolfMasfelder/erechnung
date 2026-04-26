# Logging configuration for Django project
import logging.config
import os
from pathlib import Path


# Constants for handler classes
ROTATING_FILE_HANDLER = "logging.handlers.RotatingFileHandler"

# Create logs directory if it doesn't exist
LOG_DIR = os.environ.get("LOG_DIR", os.path.join(Path(__file__).resolve().parent.parent, "logs"))
os.makedirs(LOG_DIR, exist_ok=True)

# Log files paths
GENERAL_LOG = os.path.join(LOG_DIR, "django.log")
ERROR_LOG = os.path.join(LOG_DIR, "error.log")
SECURITY_LOG = os.path.join(LOG_DIR, "security.log")
INVOICE_LOG = os.path.join(LOG_DIR, "invoice.log")

# Log level from environment or default to INFO
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Define logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "filters": ["require_debug_true"],
            "file": {
                "level": "INFO",
                "class": ROTATING_FILE_HANDLER,
                "filename": GENERAL_LOG,
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 10,
                "formatter": "verbose",
            },
            "error_file": {
                "level": "ERROR",
                "class": ROTATING_FILE_HANDLER,
                "filename": ERROR_LOG,
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 10,
                "formatter": "verbose",
            },
            "security_file": {
                "level": "INFO",
                "class": ROTATING_FILE_HANDLER,
                "filename": SECURITY_LOG,
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 10,
                "formatter": "verbose",
            },
            "invoice_file": {
                "level": "INFO",
                "class": ROTATING_FILE_HANDLER,
                "filename": INVOICE_LOG,
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 10,
                "formatter": "verbose",
            },
            "backupCount": 10,
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file", "mail_admins"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "django.server": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.request": {
            "handlers": ["error_file", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["security_file", "mail_admins"],
            "level": "INFO",
            "propagate": False,
        },
        "invoice_app": {
            "handlers": ["console", "invoice_file", "error_file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}

# Apply the configuration
logging.config.dictConfig(LOGGING_CONFIG)
