import json
from typing import List, Union

from openai import OpenAI
from openai.types import ResponseFormatJSONObject
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from loguru import logger
from openai.types.chat.completion_create_params import ResponseFormat


class Kimi:
    # model = "kimi-latest"
    # base_url = "https://api.moonshot.cn/v1"
    # model = "kimi-latest"
    # base_url = "https://api.moonshot.cn/v1"
    model = "deepseek-chat"
    base_url = "https://api.deepseek.com/v1"
    client: OpenAI

    def __init__(self, api_key, model="deepseek-chat", base_url="https://api.deepseek.com/v1"):
        self.model = model
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key, base_url=self.base_url)

    def create_chat(self, sys_prompt: List[str], question, is_json=False):
        """
        单次聊天
        :param is_json:
        :param sys_prompt:
        :param question:
        :return:
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
            params['response_format'] = {
                "type": "json_object"
            }
        completion = self.client.chat.completions.create(
            **params
        )
        content = completion.choices[0].message.content
        logger.info(f"Kimi回答: {content}")
        return content


class ItestKimi(Kimi):
    main_sysprompt = """你需要以一个大学生的身份,你正在做一篇试卷,需要以 JSON 格式返回数据。请确保你的响应是有效的 JSON 对象。你需要严格按照以下格式完成题目,有写作,翻译，选择，排序题,写作和翻译需要返回文章内容,选择题需要以列表的形式按照顺序返回答案"""
    write_sysprompt = """
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
            "css": "input[qid='10106878'][qsubindex='1'][value='2']" // css选择器,需要根据实际情况能定位到css
        },
        { // 写作题
            "qid": "10106877", // 题目的qid
            "ans": "写作答案",
            "type": "write",
            "css": "textarea[qid='10106877']"
        },
        {
            "qid": "10125372", // 题目的qid,
            "qsubindex": "1",
            "ans": "A", // 包含validaterole="1_[^A-Z]"的答案
            "type": "input",
            "css": "input[qid='10106878'][qsubindex='1']" // css选择器,需要根据实际情况能定位到css
        }
    ]
    }
    """

    def __init__(self, api_key, model="deepseek-chat", base_url="https://api.deepseek.com/v1"):
        super().__init__(api_key, model=model, base_url=base_url)

    def write(self, question, mp3_str):
        content_str = self.create_chat([self.main_sysprompt, self.write_sysprompt, f"听力转文字内容: {mp3_str}"],
                                       question, is_json=True)
        ans = json.loads(content_str)
        logger.success(f"{ans}")
        return ans
