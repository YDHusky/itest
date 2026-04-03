#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iTest 核心功能类 - 支持浏览器实例复用
"""

import json
import os
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Optional

from PyQt5.QtWidgets import QInputDialog

try:
    from husky_spider_utils import SeleniumSession
    from selenium.webdriver.common.by import By
    HAS_SELENIUM = True
except ImportError:
    SeleniumSession = None
    By = None
    HAS_SELENIUM = False

try:
    from parsel import Selector
    HAS_PARSEL = True
except ImportError:
    Selector = None
    HAS_PARSEL = False

from loguru import logger

from .ai_model import ItestKimi
from .audio_processor import AudioProcessor


class ITestError(Exception):
    """iTest 异常基类"""
    pass


class ITest:
    """iTest 自动化核心类 - 支持浏览器复用"""
    
    BASE_URL = "https://sso.unipus.cn/sso/login?service=https%3A%2F%2Fitestcloud.unipus.cn%2Futest%2Fitest%2Flogin%3F_rp%3D%252Fitest%253Fx%253D1742213323268"
    
    # 类级别的浏览器实例缓存
    _browser_cache: Dict[int, 'ITest'] = {}
    
    def __init__(self, username: str, password: str, api_key: str,
                 model: str = "deepseek-chat",
                 base_url: str = "https://api.deepseek.com/v1",
                 driver_type: str = "edge",
                 account_id: int = None,
                 reuse_browser: bool = True):
        """
        初始化 iTest
        
        Args:
            username: 用户名
            password: 密码
            api_key: AI API密钥
            model: AI模型名称
            base_url: AI API基础URL
            driver_type: 浏览器类型 (edge/chrome/firefox)
            account_id: 账号ID，用于浏览器实例管理
            reuse_browser: 是否复用浏览器实例
        """
        if not HAS_SELENIUM:
            raise ITestError("缺少依赖，请安装: pip install husky_spider_utils selenium")
        
        self.username = username
        self.password = password
        self.driver_type = driver_type
        self.account_id = account_id or hash(username)
        self.is_logged_in = False
        
        # 检查是否可以复用浏览器
        if reuse_browser and self.account_id in ITest._browser_cache:
            cached = ITest._browser_cache[self.account_id]
            if cached.is_logged_in and cached.driver_type == driver_type:
                logger.info(f"复用账号 {self.account_id} 的浏览器实例")
                self._reuse_from(cached, api_key, model, base_url)
                return
        
        # 创建新浏览器实例
        logger.info(f"为账号 {self.account_id} 创建新的浏览器实例")
        self._create_new_browser(api_key, model, base_url)
        
        # 缓存实例
        ITest._browser_cache[self.account_id] = self
    
    def _reuse_from(self, cached: 'ITest', api_key: str = None, model: str = None, base_url: str = None):
        """从缓存实例复用，更新 AI 配置"""
        self.session = cached.session
        self.audio_processor = cached.audio_processor
        self.is_logged_in = True
        self._current_audio_context = {'type': None, 'id': None}
        
        # 总是使用新的 AI 配置（创建 AI 客户端开销很小）
        if api_key and model and base_url:
            self.ai_client = ItestKimi(api_key=api_key, model=model, base_url=base_url)
            logger.info("AI 客户端已创建（使用最新配置）")
        else:
            self.ai_client = cached.ai_client
            logger.debug("使用缓存的 AI 客户端")
    
    def _create_new_browser(self, api_key: str, model: str, base_url: str):
        """创建新浏览器实例"""
        # 先关闭可能存在的旧实例
        if self.account_id in ITest._browser_cache:
            old = ITest._browser_cache[self.account_id]
            try:
                old._close_session_only()
            except:
                pass
        
        # 初始化会话
        self.session = SeleniumSession(self.BASE_URL, driver_type=self.driver_type)
        
        # 初始化 AI 客户端
        self.ai_client = ItestKimi(api_key=api_key, model=model, base_url=base_url)
        
        # 初始化音频处理器
        self.audio_processor = AudioProcessor()
        
        # 当前考试/训练上下文（用于音频缓存）
        self._current_audio_context = {'type': None, 'id': None}
        
        # 登录
        self.login()
    
    def login(self):
        """登录 iTest"""
        logger.info(f"正在登录: {self.username}")
        try:
            self.session.send_key("input[name='username']", self.username)
            self.session.send_key("input[name='password']", self.password)
            self.session.click(".help-block input[type='checkbox']")
            self.session.click("#login")
            self.is_logged_in = True
            logger.success("登录成功")
        except Exception as e:
            logger.error(f"登录失败: {e}")
            raise ITestError(f"登录失败: {e}")
    
    def get_exams(self) -> List[Dict]:
        """获取考试列表"""
        logger.info("获取考试列表...")
        self.session.selenium_get("https://itestcloud.unipus.cn/utest/itest/s/exam")
        
        exams_list = []
        
        def get_page(page: int) -> tuple:
            payload = {
                "curPage": page,
                "pageSize": 5
            }
            res = self.session.post(
                "https://itestcloud.unipus.cn/utest/itest-mobile-api/student/exam/list",
                json=payload
            )
            data = res.json()
            if data.get('msg') == "SUCCESS":
                return data['rs']['totalPage'], data['rs']['data']
            return 0, []
        
        try:
            total_page, data = get_page(1)
            exams_list.extend(data)
            
            if total_page > 1:
                for i in range(2, total_page + 1):
                    _, data = get_page(page=i)
                    exams_list.extend(data)
            
            logger.success(f"获取到 {len(exams_list)} 个考试")
            return exams_list
        except Exception as e:
            logger.error(f"获取考试列表失败: {e}")
            return []
    
    def get_mock(self) -> List[Dict]:
        """获取模拟考试列表"""
        logger.info("获取模拟考试列表...")
        self.session.selenium_get("https://itestcloud.unipus.cn/utest/itest/s/train")
        
        try:
            res = self.session.get("https://itestcloud.unipus.cn/utest/itest/s/jcxl/mock")
            
            if not HAS_PARSEL:
                raise ITestError("缺少依赖，请安装: pip install parsel")
            
            html = Selector(text=res.text)
            mock_table = html.css(".paper-table tbody tr")
            
            mock_data = []
            for tr in mock_table:
                tds = tr.css("td")
                if len(tds) >= 5:
                    mock_data.append({
                        "id": tds[0].css("::text").get(default="").strip(),
                        "mock_id": tds[1].css("::text").get(default="").strip(),
                        "name": tds[2].css("::text").get(default="").strip(),
                        "times": tds[3].css("::text").get(default="").strip(),
                        "score": tds[4].css("::text").get(default="").strip(),
                    })
            
            logger.success(f"获取到 {len(mock_data)} 个模拟考试")
            return mock_data
        except Exception as e:
            logger.error(f"获取模拟考试失败: {e}")
            return []

    def get_train(self) -> List[Dict]:
        """获取训练列表"""
        logger.info("获取训练列表...")
        self.session.selenium_get("https://itestcloud.unipus.cn/utest/itest/s/train")

        train_list = []

        def get_page(page: int) -> tuple:
            """获取指定页数据，返回(训练列表, 总页数)"""
            payload = {
                "curPage": page,
                "finish": 2,  # 默认获取未完成训练
                "keyword": "",
                "tagId": ""
            }

            res = self.session.post(
                "https://itestcloud.unipus.cn/utest/itest/s/train",
                data=payload
            )

            if not HAS_PARSEL:
                raise ITestError("缺少依赖，请安装: pip install parsel")

            html = Selector(text=res.text)
            items = html.css(".train_task_item")

            page_data = []
            for item in items:
                head = item.css(".head")
                task_id = head.css("::attr(data-id)").get(default="").strip()
                task_name = head.css("h2.taskName::text").get(default="").strip()
                tag_name = head.css(".tagName::attr(title)").get(default="").strip()

                # 获取按钮文本（开始训练/继续训练）
                btn_text = head.css("a.task-link::text").get(default="").strip()
                time_attr = head.css("a.task-link::attr(data-time)").get(default="")

                # 解析详细信息（dt/dd结构）
                rows = item.css(".task-form-item")
                info = {}
                for row in rows:
                    dt = row.css("dt::text").get(default="").strip().replace("：", "")
                    dd = row.css("dd::text").get(default="").strip()
                    if dt and dd:
                        info[dt] = dd

                page_data.append({
                    "id": task_id,
                    "name": task_name,
                    "tag": tag_name,
                    "total_score": info.get("训练总分", "").replace("分", ""),
                    "time_range": info.get("训练时间", ""),
                    "score_rule": info.get("训练成绩", ""),
                    "status": btn_text,  # "开始训练" 或 "继续训练"
                    "time_attr": time_attr  # 原始时间属性，格式：开始时间@结束时间
                })

            # 从JavaScript变量中提取总页数
            total_page = 1
            script_content = html.css("script:contains('totalPageNo')::text").get(default="")
            if script_content:
                import re
                match = re.search(r'totalPageNo\s*=\s*(\d+)', script_content)
                if match:
                    total_page = int(match.group(1))

            return page_data, total_page

        try:
            # 获取第一页和总页数
            data, total_page = get_page(1)
            train_list.extend(data)

            # 获取后续页面
            if total_page > 1:
                for i in range(2, total_page + 1):
                    logger.info(f"获取训练列表第 {i}/{total_page} 页...")
                    data, _ = get_page(i)
                    train_list.extend(data)

            logger.success(f"获取到 {len(train_list)} 个训练任务")
            return train_list

        except Exception as e:
            logger.error(f"获取训练列表失败: {e}")
            return []


    def to_train_exam(self, train_info: Dict):
        # 设置音频缓存上下文
        self._current_audio_context = {'type': 'train', 'id': str(train_info.get('id', ''))}
        
        payload = {
            "examId": train_info['id'],
            "examCode": ""
        }
        try:
            res = self.session.post(
                "https://itestcloud.unipus.cn/utest/itest/s/taskanswer/judgeEntry",
                data=payload
            )
            result = res.json()

            url = result["data"]["url"]
            token = result["data"]["token"]

            # 进入考试页面
            url = url + "&returnUrl=https://itestcloud.unipus.cn/utest/itest/s/exam"
            self.session.selenium_get(url)

            # 尝试关闭弹窗
            self.session.try_click(".layui-layer-btn0", max_attempt=1, timeout=3)

            # 进入考试
            return_url = 'https://itestcloud.unipus.cn/utest/itest/s/exam&skipEnvTest=true'
            self._enter_exam(token, return_url)
        except Exception as e:
            logger.error(e)

    def to_mock_exam(self, mock_info: Dict):
        """进入模拟考试"""
        mock_id = mock_info.get('mock_id')
        if not mock_id:
            raise ITestError("mock_id 不能为空")
        
        # 设置音频缓存上下文
        self._current_audio_context = {'type': 'mock', 'id': str(mock_id)}
        
        logger.info(f"进入模拟考试: {mock_info.get('name', 'Unknown')}")
        
        url = f"https://itestcloud.unipus.cn/utest/itest/s/jcxl/mock/doMockTest?ppId={mock_id}&returnUrl=https://itestcloud.unipus.cn/utest/itest/s/jcxl/mock"
        self.session.selenium_get(url)
        
        # 等待页面加载并获取token
        time.sleep(2)
        
        current_url = self.session.get_current_url()
        parsed_url = urlparse(current_url)
        params = parse_qs(parsed_url.query)
        token = params.get('token', [None])[0]
        
        if not token:
            logger.warning("URL中未找到token，尝试从页面获取...")
            # 尝试从页面元素获取token
            try:
                page_source = self.session.driver.page_source
                import re
                token_match = re.search(r'token[\"\']?\s*[:=]\s*[\"\']([^\"\']+)[\"\']', page_source)
                if token_match:
                    token = token_match.group(1)
            except Exception as e:
                logger.error(f"从页面获取token失败: {e}")
        
        if not token:
            raise ITestError("无法获取考试 token")
        
        # 尝试关闭弹窗
        self.session.try_click(".layui-layer-btn0", max_attempt=1, timeout=3)
        
        # 进入考试
        return_url = 'https://itestcloud.unipus.cn/utest/itest/s/jcxl/mock&skipEnvTest=true'
        self._enter_exam(token, return_url)

    # def to_train(self):


    def to_exam(self, exam_info: Dict):
        """进入正式考试"""
        ksd_id = exam_info.get('ksdId')
        if not ksd_id:
            raise ITestError("ksdId 不能为空")
        
        # 设置音频缓存上下文
        self._current_audio_context = {'type': 'exam', 'id': str(ksd_id)}
        
        logger.info(f"进入考试: {exam_info.get('ksName', 'Unknown')}")
        
        payload = {
            "examId": ksd_id,
            "examCode": ""
        }
        
        # 检查是否需要考试码
        if exam_info.get('examCodeFlag'):
            code, ok = QInputDialog.getText(None, "考试码", "请输入六位考试码:")
            if ok and code:
                payload['examCode'] = code
        
        try:
            res = self.session.post(
                "https://itestcloud.unipus.cn/utest/itest/s/exam/judgeEntry",
                data=payload
            )
            result = res.json()
            if result['code'] == 0:
                raise Exception(result['msg'])
            url = result["data"]["url"]
            token = result["data"]["token"]
            
            # 进入考试页面
            url = url + "&returnUrl=https://itestcloud.unipus.cn/utest/itest/s/exam"
            self.session.selenium_get(url)
            
            # 尝试关闭弹窗
            self.session.try_click(".layui-layer-btn0", max_attempt=1, timeout=3)
            
            # 进入考试
            return_url = 'https://itestcloud.unipus.cn/utest/itest/s/exam&skipEnvTest=true'
            self._enter_exam(token, return_url)
            
        except Exception as e:
            raise ITestError(f"进入考试失败: {e}")
    
    def _enter_exam(self, token: str, return_url: str):
        """通用进入考试方法"""
        payload = {"token": token}
        
        try:
            res = self.session.post(
                "https://itestcloud.unipus.cn/utest/itest-mobile-api/student/exam/examToken",
                data={},
                headers=payload
            )
            
            result = res.json()
            url = result["rs"]["url"] + f"&returnUrl={return_url}"
            
            self.session.selenium_get(url)
            self.session.try_click(".layui-layer-btn0", max_attempt=1, timeout=3)
            self.session.try_click("#success-ok", max_attempt=1, timeout=3)
            
            logger.success("已进入考试")
        except Exception as e:
            raise ITestError(f"进入考试页面失败: {e}")
    
    def download_mp3(self, output_dir: Path = None) -> List[Path]:
        """下载听力MP3文件"""
        logger.info("下载听力资源...")
        
        output_dir = output_dir or Path("./hear_temp")
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            sections = self.session.get_element_selector("#main-content .itest-section")
            all_hear = sections.css(".itest-hear-reslist::text").getall()
            
            hear_list = []
            for item in all_hear:
                try:
                    hear_list.extend(json.loads(item))
                except json.JSONDecodeError:
                    continue
            
            downloaded_files = []
            for i, hear in enumerate(hear_list):
                if hear.startswith("http"):
                    res = self.session.get(hear, is_refresh=False)
                    file_path = output_dir / f"hear{i}.mp3"
                    with open(file_path, "wb") as f:
                        f.write(res.content)
                    downloaded_files.append(file_path)
            
            logger.success(f"下载完成，共 {len(downloaded_files)} 个文件")
            return downloaded_files
            
        except Exception as e:
            logger.error(f"下载听力失败: {e}")
            return []
    
    def mp3_to_str(self) -> str:
        """将MP3转换为文字（带缓存）"""
        context = self._current_audio_context
        
        # 如果有上下文信息，使用缓存
        if context['type'] and context['id']:
            # 构建缓存键
            import hashlib
            cache_input = f"{context['type']}_{context['id']}"
            cache_key = hashlib.md5(cache_input.encode()).hexdigest()[:16]
            
            # 使用带缓存的 process 方法
            self.audio_processor.mp3_to_wav()
            text = self.audio_processor.wav_to_str(cache_key=cache_key)
        else:
            # 无缓存处理
            self.audio_processor.mp3_to_wav()
            text = self.audio_processor.wav_to_str()
        
        logger.success(f"听力文本: {text[:200]}..." if len(text) > 200 else f"听力文本: {text}")
        return text
    
    def ai_get_ans(self) -> Dict:
        """使用AI生成答案"""
        logger.info("AI生成答案中...")
        
        # 下载听力
        self.download_mp3()
        
        # 转换音频
        logger.info("转换听力资源...")
        mp3_str = self.mp3_to_str()
        
        # 获取试卷内容
        try:
            page_source = self.session.get_element_selector("#main-content .itest-section").getall()
            page_html = "".join(page_source)
        except Exception as e:
            logger.error(f"获取试卷内容失败: {e}")
            page_html = ""
        
        # AI生成答案
        ans_data = self.ai_client.write(page_html, mp3_str)
        logger.success("AI生成完成")
        return ans_data
    
    def write_ans(self, ans: List[Dict]):
        """填写答案"""
        logger.info(f"开始填写答案，共 {len(ans)} 道题")
        
        for i, ans_data in enumerate(ans):
            qid = ans_data.get('qid')
            q_type = ans_data.get('type')
            css = ans_data.get('css')
            answer = ans_data.get('ans')
            
            if not all([qid, q_type, css]):
                logger.warning(f"题目 {i} 数据不完整，跳过")
                continue
            
            try:
                if q_type == "write":
                    self.session.send_key(css, answer)
                    if i != len(ans) - 1:
                        self._next_page()
                        
                elif q_type == "select":
                    self.session.try_click(css, max_attempt=1, timeout=5)
                    if i != len(ans) - 1:
                        next_ans = ans[i + 1]
                        if next_ans.get('type') != "write":
                            if next_ans.get('qsubindex') == "1":
                                self._next_page()
                        else:
                            self._next_page()
                            
                elif q_type == "input":
                    self.session.send_key(css, answer)
                    if i != len(ans) - 1:
                        next_ans = ans[i + 1]
                        if next_ans.get('type') != "write":
                            if next_ans.get('qsubindex') == "1":
                                self._next_page()
                        else:
                            self._next_page()
                
                logger.success(f"题目 {qid}: {str(answer)[:50]}...")
                
            except Exception as e:
                logger.error(f"填写题目 {qid} 失败: {e}")
    
    def _next_page(self):
        """下一页"""
        self.session.try_click("#footer .goto a", max_attempt=1, timeout=3)
    
    def submit(self, sleep_time: int = 3):
        """提交试卷"""
        logger.info(f"{sleep_time}秒后提交试卷...")
        time.sleep(sleep_time)
        
        self.session.try_click("#submit-answer", max_attempt=1, timeout=3)
        self.session.try_click(".layui-layer-btn0", max_attempt=1, timeout=3)
        
        time.sleep(5)
        logger.success("试卷已提交")
    
    def _close_session_only(self):
        """仅关闭会话（用于复用时清理旧实例）"""
        try:
            self.session.quit()
        except:
            pass
    
    def quit(self, clear_cache: bool = True):
        """关闭浏览器并清理缓存
        
        Args:
            clear_cache: 是否从缓存中移除，默认True
        """
        try:
            # 从缓存中移除
            if clear_cache and self.account_id in ITest._browser_cache:
                del ITest._browser_cache[self.account_id]
            
            # 关闭浏览器
            try:
                self.session.quit()
            except:
                pass
            self.is_logged_in = False
            logger.info("浏览器已关闭")
        except Exception as e:
            logger.debug(f"关闭浏览器时出错: {e}")
    
    def is_session_valid(self) -> bool:
        """检查浏览器会话是否有效"""
        try:
            # 尝试获取当前URL来检查会话是否有效
            _ = self.session.driver.current_url
            return True
        except:
            return False
    
    def clear_cache(self):
        """清除该账号的浏览器缓存"""
        if self.account_id in ITest._browser_cache:
            del ITest._browser_cache[self.account_id]
    
    @classmethod
    def clear_all_cache(cls):
        """清除所有浏览器缓存"""
        cls._browser_cache.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 不复用时不自动关闭，由管理器控制
        pass
