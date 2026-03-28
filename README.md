# iTest 自动化助手

自动化完成 Unipus iTest 英语考试。

## 功能特点

- 自动登录、获取考试/训练/模拟考试列表
- 听力音频自动转文字（带缓存机制）
- AI 自动生成答案
- 自动填写答案并提交
- 支持随机等待后交卷
- 单页面 GUI，操作直观

## 快速开始

```bash
pip install -r requirements.txt
python main_gui.py
```

## 使用说明

1. **添加账号**：在"账号管理"区域点击"添加"
2. **配置模型**：在"AI 模型"区域点击"添加"，填入 API Key
3. **获取考试**：在"考试列表"区域点击"刷新考试"或"刷新训练"
4. **执行考试**：选择考试/训练后点击"开始执行"

## 配置说明

支持 Kimi、DeepSeek 等 OpenAI 兼容接口：

| 服务商 | Base URL | 模型示例 |
|--------|----------|----------|
| Kimi | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |

## 项目结构

```
itest/
├── main_gui.py          # 程序入口
├── config/              # 配置管理
├── core/                # 核心功能
│   ├── itest_core.py    # iTest 核心类
│   ├── ai_model.py      # AI 模型交互
│   └── audio_processor.py # 音频处理
├── gui/                 # GUI 界面
├── data/                # 数据存储
├── cache/               # 音频缓存
└── model/               # Vosk 语音识别模型
```

## 数据存储

- `data/accounts.json` - 账号数据
- `data/models.json` - 模型配置
- `cache/audio/` - 音频转录缓存

## 许可证

MIT License
