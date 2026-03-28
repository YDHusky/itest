#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置
"""

import sys
from pathlib import Path

from loguru import logger

from config import LOG_FILE


def setup_logger(log_file: str = None, level: str = "INFO"):
    """
    设置日志
    
    Args:
        log_file: 日志文件路径，默认使用 config.LOG_FILE
        level: 日志级别
    """
    log_file = log_file or LOG_FILE
    
    # 确保日志目录存在
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台处理器
    logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>"
    )
    
    # 添加文件处理器
    logger.add(
        log_file,
        rotation="1 day",
        retention="7 days",
        encoding="utf-8",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    return logger


def get_logger():
    """获取日志器"""
    return logger
