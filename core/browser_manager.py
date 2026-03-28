#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器实例管理器
确保每个账号同时只有一个浏览器实例
"""

import threading
from typing import Dict, Optional
from loguru import logger


class BrowserManager:
    """浏览器管理器 - 单例模式"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # 存储每个账号的浏览器实例
        # key: account_id, value: (itest_instance, thread_id)
        self._browsers: Dict[int, tuple] = {}
        self._lock = threading.RLock()
    
    def register_browser(self, account_id: int, itest_instance) -> bool:
        """
        注册浏览器实例
        
        Args:
            account_id: 账号ID
            itest_instance: ITest实例
        
        Returns:
            是否注册成功
        """
        with self._lock:
            if account_id in self._browsers:
                existing_instance, _ = self._browsers[account_id]
                if existing_instance is not None:
                    logger.warning(f"账号 {account_id} 已有浏览器实例，先关闭旧实例")
                    try:
                        existing_instance.quit()
                    except Exception as e:
                        logger.error(f"关闭旧浏览器实例失败: {e}")
            
            import threading
            thread_id = threading.current_thread().ident
            self._browsers[account_id] = (itest_instance, thread_id)
            logger.info(f"账号 {account_id} 注册浏览器实例成功，线程ID: {thread_id}")
            return True
    
    def unregister_browser(self, account_id: int) -> bool:
        """
        注销浏览器实例
        
        Args:
            account_id: 账号ID
        
        Returns:
            是否注销成功
        """
        with self._lock:
            if account_id in self._browsers:
                del self._browsers[account_id]
                logger.info(f"账号 {account_id} 注销浏览器实例成功")
                return True
            return False
    
    def get_browser(self, account_id: int) -> Optional[object]:
        """
        获取账号的浏览器实例
        
        Args:
            account_id: 账号ID
        
        Returns:
            ITest实例或None
        """
        with self._lock:
            if account_id in self._browsers:
                instance, _ = self._browsers[account_id]
                return instance
            return None
    
    def has_browser(self, account_id: int) -> bool:
        """
        检查账号是否有浏览器实例
        
        Args:
            account_id: 账号ID
        
        Returns:
            是否存在
        """
        with self._lock:
            return account_id in self._browsers
    
    def close_browser(self, account_id: int) -> bool:
        """
        关闭账号的浏览器实例
        
        Args:
            account_id: 账号ID
        
        Returns:
            是否成功关闭
        """
        with self._lock:
            if account_id in self._browsers:
                instance, _ = self._browsers[account_id]
                try:
                    if instance:
                        instance.quit()
                    del self._browsers[account_id]
                    logger.info(f"账号 {account_id} 浏览器实例已关闭")
                    return True
                except Exception as e:
                    logger.error(f"关闭浏览器实例失败: {e}")
                    return False
            return False
    
    def close_all_browsers(self):
        """关闭所有浏览器实例"""
        with self._lock:
            account_ids = list(self._browsers.keys())
            for account_id in account_ids:
                self.close_browser(account_id)
            logger.info("所有浏览器实例已关闭")
    
    def force_close_account(self, account_id: int) -> bool:
        """
        强制关闭账号的所有浏览器实例（用于异常恢复）
        
        Args:
            account_id: 账号ID
        
        Returns:
            是否成功
        """
        with self._lock:
            closed = False
            if account_id in self._browsers:
                instance, _ = self._browsers[account_id]
                try:
                    if instance and hasattr(instance, 'session'):
                        instance.session.quit()
                except:
                    pass
                del self._browsers[account_id]
                closed = True
            return closed


# 全局浏览器管理器实例
def get_browser_manager() -> BrowserManager:
    """获取浏览器管理器实例"""
    return BrowserManager()
