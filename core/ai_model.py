#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 模型交互模块
"""

import json
from typing import List, Union, Dict

try:
    from openai import OpenAI
    from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
except ImportError:
    OpenAI = None

from loguru import logger


class Kimi:
    """Kimi/DeepSeek AI 客户端基类"""
    
    def __init__(self, api_key: str, model: str = "deepseek-chat", 
                 base_url: str = "https://api.deepseek.com/v1"):
        if OpenAI is None:
            raise ImportError("请安装 openai 库: pip install openai")
        
        self.model = model
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key, base_url=self.base_url)
    
    def create_chat(self, sys_prompt: List[str], question: str, is_json: bool = False) -> str:
        """
        单次聊天
        
        Args:
            sys_prompt: 系统提示词列表
            question: 用户问题
            is_json: 是否要求返回JSON格式
        
        Returns:
            AI 回复内容
        """
        message = [
            *[ChatCompletionSystemMessageParam(
                content=i,
                role="system"
            ) for i in sys_prompt],
            ChatCompletionUserMessageParam(
                content=question,
                role="user"
            )
        ]
        
        params = {
            "model": self.model,
            "messages": message,
        }
        
        if is_json:
            params['response_format'] = {"type": "json_object"}
        
        completion = self.client.chat.completions.create(**params)
        content = completion.choices[0].message.content
        logger.info(f"AI回答: {content[:200]}..." if len(content) > 200 else f"AI回答: {content}")
        return content


class ItestKimi(Kimi):
    """专用于 iTest 的 AI 客户端"""
    
    MAIN_SYSPROMPT = """你需要以一个大学生的身份,你正在做一篇试卷,需要以 JSON 格式返回数据。
请确保你的响应是有效的 JSON 对象。你需要严格按照以下格式完成题目,有写作,翻译，选择，排序题,
写作和翻译需要返回文章内容,选择题需要以列表的形式按照顺序返回答案, 需要完整输出json,不要断开"""
    
    WRITE_SYSPROMPT = """
输入样例: 
    试卷html文件，请完成所有题目，并按照要求输出所有题目的答案
输出样例:
{
    "ans": [
    { //选择题示例
        "qid": "10106878", // 题目的qid
        "qsubindex": "1", // 选择题的选项
        "ans": "A", // 你认为的答案
        "value": 2, // 根据css获取
        "type": "select",
        "css": "input[qid='10106878'][qsubindex='1'][value='2']" // css选择器
    },
    { // 写作题
        "qid": "10106877",
        "ans": "写作答案",
        "type": "write",
        "css": "textarea[qid='10106877']"
    },
    {
        "qid": "10125372",
        "qsubindex": "1",
        "ans": "A",
        "type": "input",
        "css": "input[qid='10106878'][qsubindex='1']"
    }
]
}
"""
    
    def __init__(self, api_key: str, model: str = "deepseek-chat",
                 base_url: str = "https://api.deepseek.com/v1"):
        super().__init__(api_key, model=model, base_url=base_url)
    
    def write(self, question: str, mp3_str: str) -> List[Dict]:
        """
        生成考试答案
        
        Args:
            question: 试卷HTML内容
            mp3_str: 听力文本
        
        Returns:
            包含答案的JSON字典
        """
        content_str = self.create_chat(
            [self.MAIN_SYSPROMPT, self.WRITE_SYSPROMPT, f"听力转文字内容: {mp3_str}"],
            question,
            is_json=True
        )
        ans = json.loads(content_str)
        logger.success(f"AI生成答案完成，共 {len(ans.get('ans', []))} 道题")
        return ans
