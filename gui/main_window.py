#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iTest GUI - PyQt5 单页面主窗口
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QListWidget, QListWidgetItem,
    QTextEdit, QGroupBox, QFormLayout, QDialog, QDialogButtonBox,
    QMessageBox, QProgressBar, QCheckBox, QSplitter, QFrame,
    QSizePolicy, QMenu
)

from config import get_config_manager
from core import ITest
from utils import setup_logger


# ===== Worker Thread =====
class WorkerSignals(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)


class WorkerThread(QThread):
    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self._is_running = True
        self._result = None
    
    def run(self):
        try:
            self._result = self.task_func(*self.args, **self.kwargs)
            if self._is_running:
                # 将结果序列化为 JSON 字符串
                try:
                    result_str = json.dumps(self._result) if self._result is not None else "完成"
                except:
                    result_str = str(self._result) if self._result is not None else "完成"
                self.signals.finished.emit(True, result_str)
        except Exception as e:
            import traceback
            error = f"{str(e)}\n{traceback.format_exc()}"
            self.signals.finished.emit(False, error)
    
    def stop(self):
        self._is_running = False
        self.terminate()


# ===== Dialogs =====
class AddAccountDialog(QDialog):
    def __init__(self, parent=None, account=None):
        super().__init__(parent)
        self.account = account
        self.setWindowTitle("编辑账号" if account else "添加账号")
        self.setMinimumWidth(350)
        self._setup_ui()
        if account:
            self._load_data()
    
    def _setup_ui(self):
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("显示名称（可选）")
        layout.addRow("名称:", self.name_input)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("手机号/学号")
        layout.addRow("用户名*:", self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addRow("密码*:", self.password_input)
        
        self.enabled_check = QCheckBox("启用")
        self.enabled_check.setChecked(True)
        layout.addRow(self.enabled_check)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def _load_data(self):
        self.name_input.setText(self.account.get("name", ""))
        self.username_input.setText(self.account.get("username", ""))
        self.password_input.setText(self.account.get("password", ""))
        self.enabled_check.setChecked(self.account.get("enabled", True))
    
    def get_data(self):
        return {
            "name": self.name_input.text() or self.username_input.text(),
            "username": self.username_input.text(),
            "password": self.password_input.text(),
            "enabled": self.enabled_check.isChecked()
        }


class AddModelDialog(QDialog):
    def __init__(self, parent=None, model=None):
        super().__init__(parent)
        self.model = model
        self.setWindowTitle("编辑模型" if model else "添加 AI 模型")
        self.setMinimumWidth(400)
        self._setup_ui()
        if model:
            self._load_data()
    
    def _setup_ui(self):
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如: Kimi")
        layout.addRow("名称*:", self.name_input)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-...")
        layout.addRow("API Key*:", self.api_key_input)
        
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("例如: moonshot-v1-8k")
        layout.addRow("模型*:", self.model_input)
        
        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("例如: https://api.moonshot.cn/v1")
        layout.addRow("Base URL*:", self.base_url_input)
        
        self.default_check = QCheckBox("设为默认")
        layout.addRow(self.default_check)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def _load_data(self):
        self.name_input.setText(self.model.get("name", ""))
        self.api_key_input.setText(self.model.get("api_key", ""))
        self.model_input.setText(self.model.get("model", ""))
        self.base_url_input.setText(self.model.get("base_url", ""))
        self.default_check.setChecked(self.model.get("is_default", False))
    
    def get_data(self):
        return {
            "name": self.name_input.text(),
            "api_key": self.api_key_input.text(),
            "model": self.model_input.text(),
            "base_url": self.base_url_input.text(),
            "is_default": self.default_check.isChecked()
        }


# ===== Main Window =====
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = get_config_manager()
        self.logger = setup_logger()
        
        self.current_worker: Optional[WorkerThread] = None
        self.exam_data: Dict = {"exams": [], "mocks": []}
        self.train_data: List[Dict] = []
        self.selected_exam: Optional[Dict] = None
        self.selected_is_mock = False
        self.selected_is_train = False
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        self.setWindowTitle("iTest 自动化助手")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # ===== 顶部标题栏 =====
        header = QHBoxLayout()
        
        title = QLabel("iTest 自动化助手")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header.addWidget(title)
        
        header.addStretch()
        
        # 浏览器选择
        header.addWidget(QLabel("浏览器:"))
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Edge", "Chrome", "Firefox"])
        self.browser_combo.setFixedWidth(100)
        header.addWidget(self.browser_combo)
        
        header.addSpacing(20)
        
        # 统计信息
        self.stat_accounts = QLabel("账号: 0")
        self.stat_models = QLabel("模型: 0")
        self.stat_exams = QLabel("考试: 0")
        for label in [self.stat_accounts, self.stat_models, self.stat_exams]:
            label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
            header.addWidget(label)
        
        main_layout.addLayout(header)
        
        # ===== 中间三列区域 =====
        middle = QHBoxLayout()
        middle.setSpacing(15)
        
        # --- 左列：账号管理 ---
        account_group = QGroupBox("账号管理")
        account_layout = QVBoxLayout(account_group)
        
        account_btn_layout = QHBoxLayout()
        self.btn_add_account = QPushButton("+ 添加")
        self.btn_add_account.setStyleSheet(self._btn_style("#3498db"))
        self.btn_add_account.clicked.connect(self._add_account)
        account_btn_layout.addWidget(self.btn_add_account)
        account_btn_layout.addStretch()
        account_layout.addLayout(account_btn_layout)
        
        self.account_list = QListWidget()
        self.account_list.setStyleSheet(self._list_style())
        self.account_list.itemDoubleClicked.connect(self._edit_account)
        self.account_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.account_list.customContextMenuRequested.connect(self._account_context_menu)
        account_layout.addWidget(self.account_list)
        
        middle.addWidget(account_group, stretch=1)
        
        # --- 中列：模型配置 ---
        model_group = QGroupBox("AI 模型")
        model_layout = QVBoxLayout(model_group)
        
        model_btn_layout = QHBoxLayout()
        self.btn_add_model = QPushButton("+ 添加")
        self.btn_add_model.setStyleSheet(self._btn_style("#3498db"))
        self.btn_add_model.clicked.connect(self._add_model)
        model_btn_layout.addWidget(self.btn_add_model)
        model_btn_layout.addStretch()
        model_layout.addLayout(model_btn_layout)
        
        self.model_list = QListWidget()
        self.model_list.setStyleSheet(self._list_style())
        self.model_list.itemDoubleClicked.connect(self._edit_model)
        self.model_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.model_list.customContextMenuRequested.connect(self._model_context_menu)
        model_layout.addWidget(self.model_list)
        
        middle.addWidget(model_group, stretch=1)
        
        # --- 右列：考试列表 + 训练列表 ---
        exam_group = QGroupBox("考试列表")
        exam_layout = QVBoxLayout(exam_group)
        
        exam_btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 刷新考试")
        self.btn_refresh.setStyleSheet(self._btn_style("#9b59b6"))
        self.btn_refresh.clicked.connect(self._refresh_exams)
        exam_btn_layout.addWidget(self.btn_refresh)
        
        self.btn_refresh_train = QPushButton("🔄 刷新训练")
        self.btn_refresh_train.setStyleSheet(self._btn_style("#9b59b6"))
        self.btn_refresh_train.clicked.connect(self._refresh_trains)
        exam_btn_layout.addWidget(self.btn_refresh_train)
        exam_btn_layout.addStretch()
        exam_layout.addLayout(exam_btn_layout)
        
        # 正式考试
        exam_layout.addWidget(QLabel("正式考试:"))
        self.exam_list = QListWidget()
        self.exam_list.setStyleSheet(self._list_style())
        self.exam_list.itemClicked.connect(lambda item: self._on_exam_selected(item, False, False))
        exam_layout.addWidget(self.exam_list, stretch=1)
        
        # 模拟考试
        exam_layout.addWidget(QLabel("模拟考试:"))
        self.mock_list = QListWidget()
        self.mock_list.setStyleSheet(self._list_style())
        self.mock_list.itemClicked.connect(lambda item: self._on_exam_selected(item, True, False))
        exam_layout.addWidget(self.mock_list, stretch=1)
        
        # 训练列表
        exam_layout.addWidget(QLabel("训练任务:"))
        self.train_list = QListWidget()
        self.train_list.setStyleSheet(self._list_style())
        self.train_list.itemClicked.connect(lambda item: self._on_exam_selected(item, False, True))
        exam_layout.addWidget(self.train_list, stretch=1)
        
        middle.addWidget(exam_group, stretch=1)
        
        main_layout.addLayout(middle, stretch=2)
        
        # ===== 底部：日志和控制 =====
        bottom = QHBoxLayout()
        bottom.setSpacing(15)
        
        # 日志区域
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
                border: 1px solid #333;
                border-radius: 5px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        bottom.addWidget(log_group, stretch=3)
        
        # 控制区域
        control_group = QGroupBox("操作控制")
        control_layout = QVBoxLayout(control_group)
        
        # 选中的考试信息
        self.selected_label = QLabel("未选择考试")
        self.selected_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        self.selected_label.setWordWrap(True)
        self.selected_label.setMinimumHeight(50)
        control_layout.addWidget(self.selected_label)
        
        control_layout.addSpacing(10)
        
        # 随机等待开关
        self.enable_wait = QCheckBox("启用随机等待")
        self.enable_wait.setChecked(True)
        self.enable_wait.toggled.connect(self._toggle_wait_input)
        control_layout.addWidget(self.enable_wait)
        
        # 等待时间配置
        wait_layout = QHBoxLayout()
        wait_layout.addWidget(QLabel("等待时间(分钟):"))
        self.wait_min = QLineEdit("10")
        self.wait_min.setFixedWidth(40)
        wait_layout.addWidget(self.wait_min)
        wait_layout.addWidget(QLabel("~"))
        self.wait_max = QLineEdit("15")
        self.wait_max.setFixedWidth(40)
        wait_layout.addWidget(self.wait_max)
        wait_layout.addStretch()
        control_layout.addLayout(wait_layout)
        
        # 自动交卷选项
        self.auto_submit = QCheckBox("自动交卷")
        self.auto_submit.setChecked(True)
        control_layout.addWidget(self.auto_submit)
        
        control_layout.addSpacing(10)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        control_layout.addWidget(self.progress_bar)
        
        control_layout.addSpacing(10)
        
        # 按钮
        self.btn_start = QPushButton("▶ 开始执行")
        self.btn_start.setStyleSheet(self._btn_style("#27ae60", "#229954"))
        self.btn_start.setMinimumHeight(45)
        self.btn_start.clicked.connect(self._start_task)
        control_layout.addWidget(self.btn_start)
        
        self.btn_stop = QPushButton("⏹ 停止")
        self.btn_stop.setStyleSheet(self._btn_style("#e74c3c", "#c0392b"))
        self.btn_stop.setMinimumHeight(45)
        self.btn_stop.clicked.connect(self._stop_task)
        self.btn_stop.setEnabled(False)
        control_layout.addWidget(self.btn_stop)
        
        control_layout.addSpacing(20)
        
        # 缓存信息
        self.cache_label = QLabel("音频缓存: 0 个文件 (0 KB)")
        self.cache_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        control_layout.addWidget(self.cache_label)
        
        # 清除缓存按钮
        self.btn_clear_cache = QPushButton("🗑 清除音频缓存")
        self.btn_clear_cache.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 5px 10px;
                border-radius: 3px;
                border: none;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        self.btn_clear_cache.clicked.connect(self._clear_audio_cache)
        control_layout.addWidget(self.btn_clear_cache)
        
        # 更新缓存信息
        self._update_cache_info()
        
        control_layout.addStretch()
        
        bottom.addWidget(control_group, stretch=1)
        
        main_layout.addLayout(bottom, stretch=1)
    
    def _btn_style(self, color, hover_color=None):
        if hover_color is None:
            hover_color = color
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: #95a5a6;
            }}
        """
    
    def _list_style(self):
        return """
            QListWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #ecf0f1;
            }
        """
    
    def _load_data(self):
        self._refresh_account_list()
        self._refresh_model_list()
        self._update_stats()
    
    def _update_stats(self):
        exam_count = len(self.exam_data.get("exams", [])) + len(self.exam_data.get("mocks", []))
        train_count = len(self.train_data)
        self.stat_accounts.setText(f"账号: {len(self.config_manager.accounts)}")
        self.stat_models.setText(f"模型: {len(self.config_manager.models)}")
        self.stat_exams.setText(f"考试: {exam_count} 训练: {train_count}")
    
    def _refresh_account_list(self):
        self.account_list.clear()
        for acc in self.config_manager.accounts:
            name = acc.get('name', '未命名')
            username = acc.get('username', '')
            enabled = "✓" if acc.get('enabled', True) else "✗"
            item = QListWidgetItem(f"{enabled} {name}\n  {username}")
            item.setData(Qt.UserRole, acc)
            item.setData(Qt.UserRole + 1, acc.get('id'))
            if not acc.get('enabled', True):
                item.setForeground(Qt.gray)
            self.account_list.addItem(item)
    
    def _refresh_model_list(self):
        self.model_list.clear()
        for m in self.config_manager.models:
            name = m.get('name', '未命名')
            model = m.get('model', '')
            is_default = m.get('is_default', False)
            prefix = "★ " if is_default else "  "
            item = QListWidgetItem(f"{prefix}{name}\n  {model}")
            item.setData(Qt.UserRole, m)
            item.setData(Qt.UserRole + 1, m.get('id'))
            if is_default:
                item.setForeground(Qt.darkGreen)
            self.model_list.addItem(item)
    
    def _add_account(self):
        dialog = AddAccountDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if data["username"] and data["password"]:
                self.config_manager.add_account(**data)
                self._refresh_account_list()
                self._update_stats()
                self._log(f"已添加账号: {data['name']}")
    
    def _edit_account(self, item):
        account = item.data(Qt.UserRole)
        if not account:
            return
        dialog = AddAccountDialog(self, account)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            self.config_manager.update_account(account['id'], **data)
            self._refresh_account_list()
            self._log(f"已更新账号: {data['name']}")
    
    def _account_context_menu(self, position):
        item = self.account_list.itemAt(position)
        if not item:
            return
        
        account = item.data(Qt.UserRole)
        menu = QMenu()
        
        edit_action = menu.addAction("编辑")
        delete_action = menu.addAction("删除")
        toggle_action = menu.addAction("启用/禁用")
        
        action = menu.exec_(self.account_list.mapToGlobal(position))
        
        if action == edit_action:
            self._edit_account(item)
        elif action == delete_action:
            reply = QMessageBox.question(self, "确认", f"确定删除账号 {account.get('name')} 吗？")
            if reply == QMessageBox.Yes:
                self.config_manager.delete_account(account['id'])
                self._refresh_account_list()
                self._update_stats()
                self._log(f"已删除账号: {account.get('name')}")
        elif action == toggle_action:
            new_state = not account.get('enabled', True)
            self.config_manager.update_account(account['id'], enabled=new_state)
            self._refresh_account_list()
            state_str = "启用" if new_state else "禁用"
            self._log(f"已{state_str}账号: {account.get('name')}")
    
    def _add_model(self):
        dialog = AddModelDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if data["name"] and data["api_key"]:
                self.config_manager.add_model(**data)
                self._refresh_model_list()
                self._update_stats()
                self._log(f"已添加模型: {data['name']}")
    
    def _edit_model(self, item):
        model = item.data(Qt.UserRole)
        if not model:
            return
        dialog = AddModelDialog(self, model)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            self.config_manager.update_model(model['id'], **data)
            self._refresh_model_list()
            self._update_stats()
            self._log(f"已更新模型: {data['name']}")
    
    def _model_context_menu(self, position):
        item = self.model_list.itemAt(position)
        if not item:
            return
        
        model = item.data(Qt.UserRole)
        menu = QMenu()
        
        edit_action = menu.addAction("编辑")
        delete_action = menu.addAction("删除")
        set_default_action = menu.addAction("设为默认")
        
        action = menu.exec_(self.model_list.mapToGlobal(position))
        
        if action == edit_action:
            self._edit_model(item)
        elif action == delete_action:
            reply = QMessageBox.question(self, "确认", f"确定删除模型 {model.get('name')} 吗？")
            if reply == QMessageBox.Yes:
                self.config_manager.delete_model(model['id'])
                self._refresh_model_list()
                self._update_stats()
                self._log(f"已删除模型: {model.get('name')}")
        elif action == set_default_action:
            self.config_manager.update_model(model['id'], is_default=True)
            self._refresh_model_list()
            self._log(f"已设置默认模型: {model.get('name')}")
    
    def _log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _refresh_exams(self):
        enabled = [a for a in self.config_manager.accounts if a.get("enabled", True)]
        if not enabled:
            QMessageBox.warning(self, "提示", "请至少启用一个账号")
            return
        
        account = enabled[0]
        browser = self.browser_combo.currentText().lower()
        
        self._log(f"使用账号 {account['name']} 获取考试列表...")
        self.btn_refresh.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        
        def fetch():
            itest = None
            try:
                self.signals.log.emit("正在登录...")
                itest = ITest(
                    username=account["username"],
                    password=account["password"],
                    api_key="dummy", model="dummy",
                    base_url="https://api.moonshot.cn/v1",
                    driver_type=browser,
                    account_id=account["id"],
                    reuse_browser=True
                )
                self.signals.progress.emit(40)
                self.signals.log.emit("获取正式考试...")
                exams = itest.get_exams()
                self.signals.progress.emit(70)
                self.signals.log.emit("获取模拟考试...")
                mocks = itest.get_mock()
                self.signals.progress.emit(100)
                self.signals.log.emit("获取完成，保持浏览器开启以便后续操作")
                # 注意：这里不关闭浏览器，以便后续任务复用
                # 浏览器将在程序退出或开始新任务时处理
                return {"exams": exams, "mocks": mocks}
            except Exception as e:
                # 出错时才关闭浏览器
                if itest:
                    try:
                        itest.quit()
                    except:
                        pass
                raise e
        
        self._run_worker(fetch, self._on_exams_loaded)
    
    def _on_exam_selected(self, item, is_mock, is_train=False):
        data = item.data(Qt.UserRole)
        if not data:
            return
        self.selected_exam = data
        self.selected_is_mock = is_mock
        self.selected_is_train = is_train
        
        if is_train:
            name = data.get("name", "未知训练")
            exam_type = "训练任务"
            tag = data.get('tag', '-')
            score = data.get('total_score', '-')
            status = data.get('status', '-')
            detail = f"标签: {tag}\n总分: {score}分\n状态: {status}"
        else:
            name = data.get("examName") or data.get("name", "未知")
            exam_type = "模拟考试" if is_mock else "正式考试"
            
            # 显示更详细的信息
            if is_mock:
                times = data.get('times', '-')
                score = data.get('score', '-')
                detail = f"次数: {times}  最高分: {score}"
            else:
                status = data.get('statusName', '-')
                start = data.get('startDate', '-')
                end = data.get('endDate', '-')
                detail = f"状态: {status}\n时间: {start} ~ {end}"
        
        self.selected_label.setText(f"已选择: [{exam_type}]\n{name}\n{detail}")
        self.selected_label.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 12px;")
        self._log(f"已选择 {exam_type}: {name}")
    
    def _start_task(self):
        if not self.selected_exam:
            QMessageBox.warning(self, "提示", "请先选择一个考试")
            return
        
        enabled = [a for a in self.config_manager.accounts if a.get("enabled", True)]
        if not enabled:
            QMessageBox.warning(self, "提示", "请至少启用一个账号")
            return
        
        # 获取默认模型
        model = None
        for m in self.config_manager.models:
            if m.get("is_default"):
                model = m
                break
        if not model and self.config_manager.models:
            model = self.config_manager.models[0]
        
        if not model:
            QMessageBox.warning(self, "提示", "请配置 AI 模型")
            return
        
        account = enabled[0]
        browser = self.browser_combo.currentText().lower()
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setVisible(True)
        
        def task():
            itest = None
            try:
                import random
                import time
                
                # 获取等待时间配置
                try:
                    wait_min = int(self.wait_min.text() or 10)
                    wait_max = int(self.wait_max.text() or 15)
                except:
                    wait_min, wait_max = 10, 15
                
                # 计算随机等待时间（分钟转秒）
                wait_time = random.randint(wait_min * 60, wait_max * 60)
                wait_min_display = wait_time // 60
                
                self.signals.log.emit("初始化浏览器...")
                self.signals.log.emit(f"使用模型: {model.get('name', 'Unknown')} ({model.get('model', 'Unknown')})")
                self.signals.log.emit(f"API Base: {model.get('base_url', 'Unknown')}")
                # 调试：显示 API Key 的部分信息
                api_key = model.get('api_key', '')
                if api_key:
                    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
                    self.signals.log.emit(f"API Key: {masked_key} (长度: {len(api_key)})")
                else:
                    self.signals.log.emit("⚠️ API Key 为空！")
                try:
                    itest = ITest(
                        username=account["username"],
                        password=account["password"],
                        api_key=model["api_key"],
                        model=model["model"],
                        base_url=model["base_url"],
                        driver_type=browser,
                        account_id=account["id"],
                        reuse_browser=True
                    )
                except Exception as e:
                    # 如果复用失败，强制创建新实例
                    self.signals.log.emit("浏览器复用失败，创建新实例...")
                    from core import ITest as ITestClass
                    # 清除缓存
                    if account["id"] in ITestClass._browser_cache:
                        del ITestClass._browser_cache[account["id"]]
                    itest = ITest(
                        username=account["username"],
                        password=account["password"],
                        api_key=model["api_key"],
                        model=model["model"],
                        base_url=model["base_url"],
                        driver_type=browser,
                        account_id=account["id"],
                        reuse_browser=False
                    )

                self.signals.progress.emit(15)
                self.signals.log.emit("进入考试页面...")
                if self.selected_is_train:
                    # 训练任务
                    itest.to_train_exam(self.selected_exam)
                elif self.selected_is_mock:
                    itest.get_mock()
                    itest.to_mock_exam(self.selected_exam)
                else:
                    itest.get_exams()
                    itest.to_exam(self.selected_exam)
                
                self.signals.progress.emit(30)
                self.signals.log.emit("AI 生成答案...")
                try:
                    ans_data = itest.ai_get_ans()
                except Exception as e:
                    error_msg = str(e)
                    if "401" in error_msg or "Authentication" in error_msg:
                        raise Exception(f"API Key 认证失败，请检查模型配置中的 API Key 是否正确\n原始错误: {error_msg[:200]}")
                    elif "429" in error_msg:
                        raise Exception(f"API 请求过于频繁，请稍后重试\n原始错误: {error_msg[:200]}")
                    else:
                        raise Exception(f"AI 生成答案失败: {error_msg[:200]}")
                
                self.signals.progress.emit(50)
                self.signals.log.emit("填写答案...")
                itest.session.try_click("#success-ok", max_attempt=1, timeout=3)

                itest.write_ans(ans_data.get("ans", []))

                self.signals.progress.emit(70)
                
                # 根据开关决定是否等待
                if self.enable_wait.isChecked():
                    self.signals.log.emit(f"填写完成，等待 {wait_min_display} 分钟后交卷...")
                    
                    # 倒计时等待
                    remaining = wait_time
                    while remaining > 0:
                        if not self.current_worker._is_running:
                            self.signals.log.emit("等待被中断")
                            break
                        mins_left = remaining // 60
                        if remaining % 60 == 0 or remaining == wait_time:
                            self.signals.log.emit(f"距离交卷还有 {mins_left} 分钟...")
                        # 更新进度
                        progress = 70 + int((wait_time - remaining) / wait_time * 25)
                        self.signals.progress.emit(min(progress, 95))
                        time.sleep(1)
                        remaining -= 1
                    
                    self.signals.progress.emit(95)
                else:
                    self.signals.log.emit("随机等待已关闭，直接交卷...")
                    self.signals.progress.emit(90)
                
                # 自动交卷
                if self.auto_submit.isChecked() and self.current_worker._is_running:
                    self.signals.log.emit("正在提交试卷...")
                    itest.submit(sleep_time=3)
                    self.signals.log.emit("✓ 试卷已提交")
                elif not self.auto_submit.isChecked():
                    self.signals.log.emit("自动交卷已关闭，请手动交卷")
                
                self.signals.progress.emit(100)
                return "任务完成！"
            finally:
                if itest:
                    itest.quit()
        
        self._run_worker(task, self._on_task_finished)
    
    def _toggle_wait_input(self, enabled):
        """切换等待时间输入框状态"""
        self.wait_min.setEnabled(enabled)
        self.wait_max.setEnabled(enabled)
    
    def _stop_task(self):
        if self.current_worker:
            self.current_worker.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.btn_refresh.setEnabled(True)
        self._log("任务已停止")
        
        # 关闭浏览器防止占用
        from core import ITest as ITestClass
        for account_id in list(ITestClass._browser_cache.keys()):
            try:
                cached = ITestClass._browser_cache[account_id]
                cached.quit()
            except:
                pass
        ITestClass._browser_cache.clear()
        self._log("浏览器已清理")
    
    def _update_cache_info(self):
        """更新缓存信息显示"""
        try:
            from core.audio_processor import AudioProcessor
            info = AudioProcessor.get_cache_info()
            self.cache_label.setText(f"音频缓存: {info['count']} 个文件 ({info['size']:.1f} KB)")
        except:
            pass
    
    def _clear_audio_cache(self):
        """清除音频缓存"""
        try:
            from core.audio_processor import AudioProcessor
            AudioProcessor.clear_cache()
            self._update_cache_info()
            self._log("✓ 音频缓存已清除")
        except Exception as e:
            self._log(f"清除缓存失败: {e}")
    
    def _run_worker(self, task_func, on_finished=None):
        self.current_worker = WorkerThread(task_func)
        self.signals = self.current_worker.signals
        self.signals.log.connect(self._log)
        self.signals.progress.connect(self.progress_bar.setValue)
        if on_finished:
            self.signals.finished.connect(on_finished)
        else:
            self.signals.finished.connect(self._on_task_finished)
        self.current_worker.start()
    
    def _on_exams_loaded(self, success, result):
        self.btn_refresh.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            try:
                import ast
                # 尝试解析结果
                if isinstance(result, str):
                    try:
                        # 先尝试 JSON (双引号)
                        data = json.loads(result)
                    except json.JSONDecodeError:
                        # 再尝试 Python 字典字符串 (单引号)
                        try:
                            data = ast.literal_eval(result)
                        except:
                            self._log(f"无法解析结果: {result[:200]}")
                            return
                else:
                    data = result
                
                if isinstance(data, dict):
                    self.exam_data = data
                    self._update_exam_list()
                    self._update_stats()
                    total = len(data.get('exams', [])) + len(data.get('mocks', []))
                    self._log(f"✓ 成功加载 {total} 个考试")
                else:
                    self._log(f"数据格式错误: {type(data)}")
            except Exception as e:
                self._log(f"解析失败: {e}")
        else:
            self._log(f"✗ 获取失败: {result[:500]}")
    
    def _update_exam_list(self):
        """更新考试列表显示"""
        self.exam_list.clear()
        self.mock_list.clear()
        
        # 正式考试
        exams = self.exam_data.get("exams", [])
        self._log(f"正式考试数量: {len(exams)}")
        if not exams:
            self._log("暂无正式考试")
        for exam in exams:
            name = exam.get('examName', '未知')
            status = exam.get('statusName', '')
            item = QListWidgetItem(f"📋 {name}\n   状态: {status}")
            item.setData(Qt.UserRole, exam)
            self.exam_list.addItem(item)
        
        # 模拟考试
        mocks = self.exam_data.get("mocks", [])
        self._log(f"模拟考试数量: {len(mocks)}")
        for mock in mocks:
            name = mock.get('name', '未知')
            times = mock.get('times', '-')
            score = mock.get('score', '-')
            item = QListWidgetItem(f"📝 {name}\n   次数:{times}  最高分:{score}")
            item.setData(Qt.UserRole, mock)
            self.mock_list.addItem(item)
    
    def _refresh_trains(self):
        """刷新训练列表"""
        enabled = [a for a in self.config_manager.accounts if a.get("enabled", True)]
        if not enabled:
            QMessageBox.warning(self, "提示", "请至少启用一个账号")
            return
        
        account = enabled[0]
        browser = self.browser_combo.currentText().lower()
        
        self._log(f"使用账号 {account['name']} 获取训练列表...")
        self.btn_refresh_train.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        
        def fetch():
            itest = None
            try:
                self.signals.log.emit("正在登录...")
                itest = ITest(
                    username=account["username"],
                    password=account["password"],
                    api_key="dummy", model="dummy",
                    base_url="https://api.moonshot.cn/v1",
                    driver_type=browser,
                    account_id=account["id"],
                    reuse_browser=True
                )
                self.signals.progress.emit(50)
                self.signals.log.emit("获取训练列表...")
                trains = itest.get_train()
                self.signals.progress.emit(100)
                self.signals.log.emit("获取完成")
                return trains
            except Exception as e:
                if itest:
                    try:
                        itest.quit()
                    except:
                        pass
                raise e
        
        self._run_worker(fetch, self._on_trains_loaded)
    
    def _on_trains_loaded(self, success, result):
        """训练列表加载完成"""
        self.btn_refresh_train.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            try:
                import ast
                if isinstance(result, str):
                    try:
                        data = json.loads(result)
                    except json.JSONDecodeError:
                        try:
                            data = ast.literal_eval(result)
                        except:
                            self._log(f"无法解析结果: {result[:200]}")
                            return
                else:
                    data = result
                
                if isinstance(data, list):
                    self.train_data = data
                    self._update_train_list()
                    self._update_stats()
                    self._log(f"✓ 成功加载 {len(data)} 个训练任务")
            except Exception as e:
                self._log(f"解析失败: {e}")
        else:
            self._log(f"✗ 获取失败: {result[:500]}")
    
    def _update_train_list(self):
        """更新训练列表显示"""
        self.train_list.clear()
        
        for train in self.train_data:
            name = train.get('name', '未知')
            tag = train.get('tag', '')
            score = train.get('total_score', '-')
            status = train.get('status', '')
            icon = "🎯" if status == "开始训练" else "📚"
            item = QListWidgetItem(f"{icon} {name}\n   标签: {tag}  总分: {score}分  状态: {status}")
            item.setData(Qt.UserRole, train)
            self.train_list.addItem(item)
    
    def _on_task_finished(self, success, result):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        # 更新缓存信息
        self._update_cache_info()
        
        if success:
            self._log(f"✓ {result}")
        else:
            self._log(f"✗ 错误: {result[:500]}")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
