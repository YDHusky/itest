#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辅助函数
"""

from datetime import datetime


def lighten_color(color: str, amount: int = 20) -> str:
    """
    使颜色变亮
    
    Args:
        color: 十六进制颜色值，如 "#4CAF50"
        amount: 增加量 (0-255)
    
    Returns:
        变亮后的颜色值
    """
    color = color.lstrip('#')
    rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
    rgb = tuple(min(255, c + amount) for c in rgb)
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def darken_color(color: str, amount: int = 20) -> str:
    """
    使颜色变暗
    
    Args:
        color: 十六进制颜色值，如 "#4CAF50"
        amount: 减少量 (0-255)
    
    Returns:
        变暗后的颜色值
    """
    color = color.lstrip('#')
    rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
    rgb = tuple(max(0, c - amount) for c in rgb)
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def format_time(dt: datetime = None, fmt: str = "%H:%M:%S") -> str:
    """
    格式化时间
    
    Args:
        dt: datetime对象，默认当前时间
        fmt: 格式字符串
    
    Returns:
        格式化后的时间字符串
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀
    
    Returns:
        截断后的文本
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def safe_json_loads(text: str, default=None):
    """
    安全地解析JSON
    
    Args:
        text: JSON字符串
        default: 解析失败时的默认值
    
    Returns:
        解析后的对象或默认值
    """
    import json
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def ensure_list(obj):
    """
    确保对象是列表
    
    Args:
        obj: 任意对象
    
    Returns:
        列表
    """
    if obj is None:
        return []
    if isinstance(obj, (list, tuple)):
        return list(obj)
    return [obj]
