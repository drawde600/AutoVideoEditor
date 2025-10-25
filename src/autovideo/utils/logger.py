"""Logging configuration and setup."""

import logging
import logging.config
import yaml
from pathlib import Path
from typing import Optional


def setup_logging(
    config_path: str = "config/logging.yaml",
    default_level: int = logging.INFO,
    verbosity: str = "detailed",
    log_file: Optional[str] = None
) -> logging.Logger:
    """Setup logging configuration from YAML file.

    Args:
        config_path: Path to logging YAML configuration file
        default_level: Default logging level if config not found
        verbosity: Verbosity level (minimal, moderate, detailed, verbose)
        log_file: Optional log file path override

    Returns:
        Configured logger instance
    """
    # Map verbosity to logging levels
    level_map = {
        'minimal': logging.ERROR,
        'moderate': logging.WARNING,
        'detailed': logging.INFO,
        'verbose': logging.DEBUG
    }
    console_level = level_map.get(verbosity, logging.INFO)

    # Create logger
    logger = logging.getLogger("autovideo")
    logger.setLevel(logging.DEBUG)  # Capture all, filter at handler level
    logger.handlers = []  # Clear existing handlers

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file specified)
    if log_file:
        # Create log directory if needed
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Try to load YAML config if it exists (optional enhancement)
    if Path(config_path).exists():
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                if config:
                    # Override with YAML config
                    config['handlers']['console']['level'] = console_level
                    if log_file and 'file' in config['handlers']:
                        config['handlers']['file']['filename'] = log_file
                    logging.config.dictConfig(config)
                    logger = logging.getLogger("autovideo")
        except Exception as e:
            # Fall back to simple config
            logger.warning(f"Could not load logging config from {config_path}: {e}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"autovideo.{name}")
