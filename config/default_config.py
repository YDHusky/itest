#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
默认配置
"""

import os

# 基础路径配置
BASE_DIR = "./"
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# 文件路径
ACCOUNTS_FILE = os.path.join(DATA_DIR, 'accounts.json')
MODELS_FILE = os.path.join(DATA_DIR, 'models.json')
GUI_CONFIG_FILE = os.path.join(DATA_DIR, 'gui_config.json')
LOG_FILE = os.path.join(LOGS_DIR, 'itest_gui.log')

# 默认配置
DEFAULT_CONFIG = {
    "driver_type": "edge",
    "sleep_time": 10,
    "headless": False,
    "auto_submit": False,
    "save_logs": True,
    "theme": "light",
    "window": {
        "width": 1500,
        "height": 950
    }
}

# 默认模型配置
DEFAULT_MODELS = [
    {
        "id": "kimi-default",
        "name": "Kimi K2.5",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "kimi-k2.5",
        "api_key": "",
        "is_default": True
    },
    {
        "id": "deepseek-default",
        "name": "DeepSeek Chat",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "api_key": "",
        "is_default": False
    },
    {
        "id": "deepseek-reasoner",
        "name": "DeepSeek Reasoner",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-reasoner",
        "api_key": "",
        "is_default": False
    }
]

# 浏览器选项
BROWSER_OPTIONS = ["edge", "chrome", "firefox"]

# iTest 基础URL
ITEST_BASE_URL = "https://sso.unipus.cn/sso/login?service=https%3A%2F%2Fitestcloud.unipus.cn%2Futest%2Fitest%2Flogin%3F_rp%3D%252Fitest%253Fx%253D1742213323268"
