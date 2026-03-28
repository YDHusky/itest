#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iTest 自动化助手 - 主入口
现在使用 SiliconUI 界面
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接导入 SiliconUI 版本
from gui.main_window import main

if __name__ == "__main__":
    sys.exit(main())
