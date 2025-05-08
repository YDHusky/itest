import yaml
from loguru import logger

from itest import ITest

config = yaml.load(open("config.yml", "r", encoding="utf-8"), Loader=yaml.FullLoader)

if __name__ == '__main__':
    itest = ITest(config['username'], config['password'], model=config['ai']['model'],
                  driver_type=config['driver_type'], api_key=config['ai']['apikey'], base_url=config['ai']['base_url'])
    exams = itest.get_exams()
    for exam in exams:
        print(exam)
        is_next = input("是否继续[Y/n]:")
        if is_next == "n" or is_next == "N":
            continue
        itest.to_exam(exam)
        itest.write_ans(itest.ai_get_ans())
        itest.submit(sleep_time=config['sleep_time'])
        logger.success("当前试卷已完成!")
