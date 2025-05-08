# ITest 脚本

## 配置

修改itest.py中 相关账户密码部分启动即可

```python
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
```

## 启动

启动发现需要完成的考试输入y即可, 部分考试需要考试码!