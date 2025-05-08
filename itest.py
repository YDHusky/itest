import json
import os
import shutil
import time

from husky_spider_utils import SeleniumSession

from kimi_model import ItestKimi
from mp32str import mp3_to_wav, wav_to_str
from loguru import logger


class ITest:
    base_url = "https://sso.unipus.cn/sso/login?service=https%3A%2F%2Fitestcloud.unipus.cn%2Futest%2Fitest%2Flogin%3F_rp%3D%252Fitest%253Fx%253D1742213323268"

    def __init__(self, username, password, api_key, model="deepseek-chat", base_url="https://api.deepseek.com/v1",
                 driver_type="edge"):
        self.session = SeleniumSession(self.base_url, driver_type=driver_type)
        self.ai_client = ItestKimi(api_key=api_key, model=model, base_url=base_url)
        self.login(username, password)

    def login(self, username, password):
        self.session.send_key("input[name='username']", username)
        self.session.send_key("input[name='password']", password)
        self.session.click(".help-block input[type='checkbox']")
        self.session.click("#login")

    def get_exams(self):
        self.session.selenium_get("https://itestcloud.unipus.cn/utest/itest/s/exam")
        exams_list = []

        def get_res(page: int):
            payload = {
                "curPage": page,
                "pageSize": 5
            }
            res = self.session.post("https://itestcloud.unipus.cn/utest/itest-mobile-api/student/exam/list",
                                    json=payload)
            if res.json()['msg'] == "SUCCESS":
                return res.json()['rs']['totalPage'], res.json()['rs']['data']
            else:
                return None

        total_page, data = get_res(1)
        exams_list.extend(data)
        if total_page > 1:
            for i in range(2, total_page + 1):
                _, data = get_res(page=i)
                exams_list.extend(data)
        return exams_list

    def to_exam(self, exam_info):
        ksd_id = exam_info['ksdId']
        payload = {
            "examId": ksd_id,
            "examCode": ""
        }
        if exam_info['examCodeFlag']:
            payload['examCode'] = input("请输入六位考试码:")
        res = self.session.post("https://itestcloud.unipus.cn/utest/itest/s/clsanswer/judgeEntry", data=payload)
        print(res.json())
        url = res.json()["data"]["url"]
        token = res.json()["data"]["token"]

        url = url + "&returnUrl=https://itestcloud.unipus.cn/utest/itest/s/exam"
        self.session.selenium_get(url)
        self.session.try_click(".layui-layer-btn0", max_attempt=1, timeout=5)
        payload = {
            "token": token
        }
        data = {}
        self.session.headers.update(payload)
        res = self.session.post("https://itestcloud.unipus.cn/utest/itest-mobile-api/student/exam/examToken", data=data)
        url = res.json()["rs"]["url"] + "&returnUrl=https://itestcloud.unipus.cn/utest/itest/s/exam&skipEnvTest=true"
        self.session.selenium_get(url)
        self.session.try_click(".layui-layer-btn0", max_attempt=1, timeout=3)
        self.session.try_click("#success-ok", max_attempt=1, timeout=3)

    def download_mp3(self):
        sections = self.session.get_element_selector("#main-content .itest-section")
        all_hear = sections.css(".itest-hear-reslist::text").getall()
        hear_list = []
        if os.path.exists("hear_temp"):
            shutil.rmtree("hear_temp")
        os.mkdir("hear_temp")
        for item in all_hear:
            hear_list.extend(json.loads(item))
        for i, hear in enumerate(hear_list):  # type: int, str

            if hear.startswith("http"):
                res = self.session.get(hear, is_refresh=False)
                with open(f"./hear_temp/hear{i}.mp3", "wb") as f:
                    f.write(res.content)

    def mp3_to_str(self):
        mp3_to_wav()
        mp3_str = wav_to_str()
        return mp3_str

    def ai_get_ans(self):
        logger.info("下载听力资源中...")
        self.download_mp3()
        logger.info("转换听力资源中...")
        mp3_str = self.mp3_to_str()
        logger.success(f"听力文本: {mp3_str}")
        page_source = self.session.get_element_selector("#main-content .itest-section").getall()
        page_source_data = "".join(page_source)
        logger.info("ai生成答案中...")
        ans_data = self.ai_client.write(page_source_data, mp3_str)['ans']
        logger.info("ai生成完成！")
        return ans_data

    def write_ans(self, ans: list):
        logger.info("即将为您填写答案!")
        for i, ans_data in enumerate(ans):
            qid = ans_data['qid']
            q_type = ans_data['type']
            css = ans_data['css']
            a = ans_data['ans']
            logger.success(f"正在完成题目{qid}: {a}")
            if q_type == "write":
                self.session.send_key(css, a)
                if i != len(ans) - 1:
                    self.next_page()
            elif q_type == "select":
                self.session.try_click(css, max_attempt=1, timeout=5)
                if i != len(ans) - 1:
                    next_ans = ans[i + 1]
                    if next_ans['type'] != "write":
                        if next_ans['qsubindex'] == "1":
                            self.next_page()
                    else:
                        self.next_page()
            elif q_type == "input":
                self.session.send_key(css, a)
                if i != len(ans) - 1:
                    next_ans = ans[i + 1]
                    if next_ans['type'] != "write":
                        if next_ans['qsubindex'] == "1":
                            self.next_page()
                    else:
                        self.next_page()

    def submit(self, sleep_time=3):
        time.sleep(sleep_time)
        self.session.try_click("#submit-answer", max_attempt=1, timeout=3)
        self.session.try_click(".layui-layer-btn0", max_attempt=1, timeout=3)
        time.sleep(5)

    def next_page(self):
        self.session.try_click("#footer .goto a", max_attempt=1, timeout=3)


if __name__ == '__main__':
    itest = ITest("账户", "密码", "deepseek-api")
    exams = itest.get_exams()
    for exam in exams:
        print(exam)
        is_next = input("是否继续[Y/n]:")
        if is_next != "y" and is_next != "Y":
            continue
        itest.to_exam(exam)
        itest.write_ans(itest.ai_get_ans())
        itest.submit(sleep_time=3) # 完成后提交前等待时间
        logger.success("当前试卷已完成!")
