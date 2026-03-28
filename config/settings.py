#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器
"""

import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from .default_config import (
    ACCOUNTS_FILE, MODELS_FILE, GUI_CONFIG_FILE,
    DEFAULT_CONFIG, DEFAULT_MODELS
)


class ConfigManager:
    """配置管理器 - 单例模式"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._config = self._load_config()
        self._accounts = self._load_accounts()
        self._models = self._load_models()
    
    # ========== 配置管理 ==========
    
    def _load_config(self) -> dict:
        """加载主配置"""
        if os.path.exists(GUI_CONFIG_FILE):
            try:
                with open(GUI_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # 合并默认配置
                    config = DEFAULT_CONFIG.copy()
                    config.update(loaded)
                    return config
            except Exception as e:
                print(f"加载配置失败: {e}")
        return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """保存主配置"""
        with open(GUI_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)
    
    @property
    def config(self) -> dict:
        return self._config
    
    def get(self, key: str, default=None):
        """获取配置项"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置配置项"""
        self._config[key] = value
        self.save_config()
    
    # ========== 账号管理 ==========
    
    def _load_accounts(self) -> List[dict]:
        """加载账号列表"""
        if os.path.exists(ACCOUNTS_FILE):
            try:
                with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载账号失败: {e}")
        return []
    
    def save_accounts(self):
        """保存账号列表"""
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._accounts, f, ensure_ascii=False, indent=2)
    
    @property
    def accounts(self) -> List[dict]:
        return self._accounts
    
    def add_account(self, name: str, username: str, password: str, enabled: bool = True) -> dict:
        """添加账号"""
        account = {
            "id": int(time.time() * 1000),
            "name": name,
            "username": username,
            "password": password,
            "enabled": enabled,
            "created_at": datetime.now().isoformat()
        }
        self._accounts.append(account)
        self.save_accounts()
        return account
    
    def update_account(self, account_id: int, **kwargs) -> bool:
        """更新账号"""
        for acc in self._accounts:
            if acc["id"] == account_id:
                acc.update(kwargs)
                self.save_accounts()
                return True
        return False
    
    def delete_account(self, account_id: int):
        """删除账号"""
        self._accounts = [acc for acc in self._accounts if acc["id"] != account_id]
        self.save_accounts()
    
    def get_enabled_accounts(self) -> List[dict]:
        """获取启用的账号"""
        return [acc for acc in self._accounts if acc.get("enabled", True)]
    
    # ========== 模型管理 ==========
    
    def _load_models(self) -> List[dict]:
        """加载模型配置"""
        if os.path.exists(MODELS_FILE):
            try:
                with open(MODELS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载模型配置失败: {e}")
        return DEFAULT_MODELS.copy()
    
    def save_models(self):
        """保存模型配置"""
        with open(MODELS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._models, f, ensure_ascii=False, indent=2)
    
    @property
    def models(self) -> List[dict]:
        return self._models
    
    def add_model(self, name: str, base_url: str, model: str, 
                  api_key: str, is_default: bool = False) -> dict:
        """添加模型"""
        if is_default:
            for m in self._models:
                m["is_default"] = False
        
        model_config = {
            "id": f"model-{int(time.time() * 1000)}",
            "name": name,
            "base_url": base_url,
            "model": model,
            "api_key": api_key,
            "is_default": is_default
        }
        self._models.append(model_config)
        self.save_models()
        return model_config
    
    def update_model(self, model_id: str, **kwargs) -> bool:
        """更新模型配置"""
        if kwargs.get("is_default"):
            for m in self._models:
                m["is_default"] = False
        
        for m in self._models:
            if m["id"] == model_id:
                m.update(kwargs)
                self.save_models()
                return True
        return False
    
    def delete_model(self, model_id: str):
        """删除模型配置"""
        self._models = [m for m in self._models if m["id"] != model_id]
        self.save_models()
    
    def get_default_model(self) -> Optional[dict]:
        """获取默认模型"""
        for m in self._models:
            if m.get("is_default"):
                return m
        return self._models[0] if self._models else None
    
    def get_model_by_id(self, model_id: str) -> Optional[dict]:
        """根据ID获取模型"""
        for m in self._models:
            if m["id"] == model_id:
                return m
        return None


# 全局配置管理器实例
_config_manager = None

def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
