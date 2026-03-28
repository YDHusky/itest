#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置模块
"""

from .settings import ConfigManager, get_config_manager
from .default_config import (
    DEFAULT_CONFIG, DEFAULT_MODELS, LOG_FILE,
    DATA_DIR, LOGS_DIR, CONFIG_DIR
)

__all__ = [
    'ConfigManager', 'get_config_manager',
    'DEFAULT_CONFIG', 'DEFAULT_MODELS',
    'LOG_FILE', 'DATA_DIR', 'LOGS_DIR', 'CONFIG_DIR'
]
