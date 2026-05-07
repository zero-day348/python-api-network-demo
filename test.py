# -*- coding: utf-8 -*-
"""
@time: 2025-09-04
@author: zero
"""

"""
Usage:
    python test.py -c <configpath>
Example:
    python test.py -c /Users/Administrator/PycharmProjects/12306Python/config.ini
    python test.py
"""

# Selenium 4.x 核心依赖：Service类指定驱动路径
# 显示等待核心依赖
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from configparser import ConfigParser
from time import sleep
import traceback
import time
import sys
import codecs
import argparse
import os


class hackTickets(object):
    """12306购票类"""

    """读取配置文件（从config.ini获取账号、车次、席别等信息）"""

    def readConfig(self, config_file='config.ini'):
        print("加载配置文件...")
        path = os.path.join(os.getcwd(), config_file)

        cp = ConfigParser()
        try:
            with codecs.open(config_file, "r", "utf-8-sig") as f:
                cp.read_file(f)
        except IOError as e:
            print(u'打开配置文件"%s"失败, 请先创建或拷贝config.ini' % (config_file))
            input('Press any key to continue')
            sys.exit()

        # 登录信息
        self.username = cp.get("login", "username")
        self.passwd = cp.get("login", "password")

        # 城市信息（转换为12306识别的编码格式）
        starts_city = cp.get("cookieInfo", "starts")
        self.starts = self.convertCityToCode(starts_city).encode('unicode_escape').decode("utf-8").replace("\\u",
                                                                                                           "%u").replace(
            ",", "%2c")
        ends_city = cp.get("cookieInfo", "ends")
        self.ends = self.convertCityToCode(ends_city).encode('unicode_escape').decode("utf-8").replace("\\u",
                                                                                                       "%u").replace(
            ",", "%2c")
        self.dtime = cp.get("cookieInfo", "dtime")  # 乘车日期（格式：YYYY-MM-DD）

        # 订单配置
        self.order = int(cp.get("orderItem", "order"))  # 选择第N个可预订车次（0表示优先第一个）
        self.users = cp.get("userInfo", "users").split(",")  # 乘车人列表（逗号分隔）
        self.train_types = cp.get("trainInfo", "train_types").split(",")  # 车次类型（如G,D,Z）
        self.start_time = cp.get("trainInfo", "start_time")  # 发车时间段（如06:00-12:00）

        # 网址配置
        self.ticket_url = cp.get("urlInfo", "ticket_url")  # 购票页面URL
        self.login_url = cp.get("urlInfo", "login_url")  # 登录页面URL
        self.initmy_url = cp.get("urlInfo", "initmy_url")  # 个人中心URL

        # 席别配置（映射12306席别编码）
        seat_type = cp.get("confirmInfo", "seat_type")
        self.seatMap = {
            "硬座": "1", "硬卧": "3", "软卧": "4", "一等软座": "7",
            "二等软座": "8", "商务座": "9", "一等座": "M", "二等座": "O",
            "混编硬座": "B", "特等座": "P"
        }
        self.seatType = self.seatMap[seat_type] if seat_type in self.seatMap else ""
        self.noseat_allow = 1 if int(cp.get("confirmInfo", "noseat_allow")) != 0 else 0  # 是否允许无座

        # ChromeDriver路径（从配置文件读取）
        self.executable_path = cp.get("pathInfo", "executable_path")

    """解析命令行参数（支持指定自定义config.ini路径）"""

    def loadConfig(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--config', help='Specify config file (absolute path)')
        args = parser.parse_args()
        self.readConfig(args.config) if args.config else self.readConfig()

    """加载城市编码映射（从city_code.txt读取中文城市与12306编码的对应关系）"""

    def loadCityCode(self):
        print("映射出发地、目的地...")
        city_codes = {}
        path = os.path.join(os.getcwd(), 'city_code.txt')

        if not os.path.exists(path):
            print(f"错误：未找到city_code.txt文件，路径：{path}")
            sys.exit(1)

        with codecs.open(path, "r", "utf-8-sig") as f:
            for line_num, l in enumerate(f.readlines(), 1):
                l = l.strip()
                if not l:
                    continue
                parts = l.split(':')
                if len(parts) != 2:
                    print(f"警告：第 {line_num} 行格式错误，跳过该行 - {l}")
                    continue
                city_codes[parts[0]] = parts[0] + "," + parts[1].strip()
        return city_codes

    """将中文城市名转换为12306识别的编码"""

    def convertCityToCode(self, c):
        try:
            return self.city_codes[c]
        except KeyError:
            print("转换城市错误，请修改config.ini中starts/ends为中文全称（如：北京、上海）")
            sys.exit(1)

    """类初始化（加载城市编码+配置文件）"""

    def __init__(self):
        self.city_codes = self.loadCityCode()
        self.loadConfig()

    """登录逻辑（模拟人工操作，绕过12306反爬）"""

    def login(self):
        print("开始登录...")
        # 1. 先访问12306首页建立正常会话（避免直接登录被拦截）
        self.driver.get("https://www.12306.cn/index/")
        sleep(2)

        # 2. 点击首页"登录"按钮（模拟人工操作路径）
        try:
            self.driver.find_element(By.LINK_TEXT, "登录").click()
        except Exception as e:
            print(u"点击登录按钮异常，尝试直接访问登录页...")
            self.driver.get(self.login_url)
        sleep(2)

        # 3. 字符级输入账号密码（模拟人工输入，减少机器特征）
        try:
            username_input = self.driver.find_element(By.ID, "J-userName")
            for char in self.username:
                username_input.send_keys(char)
                sleep(0.1)
            sleep(0.5)

            passwd_input = self.driver.find_element(By.ID, "J-password")
            for char in self.passwd:
                passwd_input.send_keys(char)
                sleep(0.1)
            sleep(1)
        except Exception as e:
            print(u"填充账号密码异常：%s，尝试备用定位..." % str(e))
            # 备用定位：兼容12306页面更新后的元素变化
            username_input = self.driver.find_element(By.NAME, "loginUserDTO.user_name")
            for char in self.username:
                username_input.send_keys(char)
                sleep(0.1)
            sleep(0.5)

            passwd_input = self.driver.find_element(By.NAME, "userDTO.password")
            for char in self.passwd:
                passwd_input.send_keys(char)
                sleep(0.1)
            sleep(1)

        # 4. 等待用户手动完成验证码
        print(u"请在60秒内完成验证码验证并点击【登录】按钮...")
        timeout = 60
        start_time = time.time()
        while True:
            # 关键：登录成功后离开登录页，URL 不含 "login"
            if "login" not in self.driver.current_url.lower():
                print(u"登录成功！")
                # 自动跳转到首页，避免停留在登录提示页
                self.driver.get("https://www.12306.cn/index/")
                sleep(2)
                break
            # 超时处理
            if time.time() - start_time > timeout:
                print(u"登录超时，请重新运行程序！")
                self.driver.quit()
                sys.exit(1)
            sleep(1)
    """选择车次类型、发车时间等查询条件"""

    def searchMore(self):
        # 1. 选择车次类型（如G高铁、D动车）
        train_type_map = {
            'T': u'T-特快', 'G': u'GC-高铁/城际',
            'D': u'D-动车', 'Z': u'Z-直达', 'K': u'K-快速'
        }
        for train_type in self.train_types:
            if train_type in train_type_map:
                print(u'--------->选择车次类型：', train_type_map[train_type])
                try:
                    # 定位车次类型复选框（精确到input标签）
                    check_box = self.driver.find_element(By.XPATH,
                                                         f"//label[contains(text(), '{train_type_map[train_type]}')]/input")
                    if not check_box.is_selected():
                        check_box.click()
                except Exception as e:
                    print(u"选择车次类型异常：%s，尝试点击文本..." % str(e))
                    self.driver.find_element(By.XPATH,
                                             f"//label[contains(text(), '{train_type_map[train_type]}')]").click()
                sleep(0.3)
            else:
                print(u"车次类型异常，跳过：%s" % train_type)

        # 2. 选择发车时间段（如06:00-12:00）
        if self.start_time:
            print(u'--------->选择发车时间：', self.start_time)
            try:
                Select(self.driver.find_element(By.ID, "cc_start_time")).select_by_visible_text(self.start_time)
            except Exception as e:
                print(u"选择发车时间异常：%s，尝试备用定位..." % str(e))
                Select(self.driver.find_element(By.XPATH, "//select[@id='cc_start_time']")).select_by_visible_text(
                    self.start_time)
            sleep(0.3)
        else:
            print(u"未指定发车时间，默认00:00-24:00")

    """添加查询Cookie（预设出发地、目的地、乘车日期）"""

    def preStart(self):
        self.driver.add_cookie({"name": "_jc_save_fromStation", "value": self.starts, "path": "/"})
        self.driver.add_cookie({"name": "_jc_save_toStation", "value": self.ends, "path": "/"})
        self.driver.add_cookie({"name": "_jc_save_fromDate", "value": self.dtime, "path": "/"})

    """按配置选择第N个可预订车次"""

    def specifyTrainNo(self):
        count = 0
        while "otn/leftTicket/init" in self.driver.current_url:
            self.searchMore()
            # 点击查询按钮
            try:
                self.driver.find_element(By.ID, "query_ticket").click()
            except Exception as e:
                print(u"点击查询按钮异常：%s，尝试文本定位..." % str(e))
                self.driver.find_element(By.LINK_TEXT, u"查询").click()

            count += 1
            print(u"循环查询... 第 %s 次" % count)
            sleep(1)  # 等待车次列表加载

            try:
                # 筛选可点击的"预订"按钮（排除禁用状态）
                book_buttons = self.driver.find_elements(By.XPATH,
                                                         "//a[contains(@class, 'btn72') and text()='预订' and not(@disabled)]")
                if len(book_buttons) >= self.order:
                    book_buttons[self.order - 1].click()
                    sleep(1)
                    break
                else:
                    print(u"可预订车次不足（当前%d个），继续查询..." % len(book_buttons))
            except Exception as e:
                print(u"预订异常：", str(e))
                sleep(1)

    """默认选择第一个可预订车次"""

    def buyOrderZero(self):
        count = 0
        while "otn/leftTicket/init" in self.driver.current_url:
            self.searchMore()
            # 点击查询按钮
            try:
                self.driver.find_element(By.ID, "query_ticket").click()
            except Exception as e:
                self.driver.find_element(By.LINK_TEXT, u"查询").click()

            count += 1
            print(u"循环查询... 第 %s 次" % count)
            sleep(1)

            try:
                book_buttons = self.driver.find_elements(By.XPATH,
                                                         "//a[contains(@class, 'btn72') and text()='预订' and not(@disabled)]")
                if book_buttons:
                    book_buttons[0].click()  # 优先第一个可预订车次
                    sleep(1)
                    break
                else:
                    print(u"无可用车次，继续查询...")
            except Exception as e:
                print(u"预订异常：", str(e))
                sleep(1)

    """选择乘车人（适配12306当前页面，显式等待更稳定）"""
    def selUser(self):
        print(u'选择乘客...')
        for user in self.users:
            try:
                # 显式等待10秒：等待乘车人复选框出现（避免页面加载延迟）
                user_box = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        # 新XPath：适配12306当前乘车人列表结构
                        (By.XPATH,
                         f"""//ul[@id='normal_passenger_id']//li[contains(., '{user}')]//input[@type='checkbox']"""
                    )
                )
                # 若未选中则点击
                if not user_box.is_selected():
                    user_box.click()
                    sleep(0.3)
                print(f"✅ 成功选择乘客：{user}")
            except Exception as e:
                print(u"❌ 未找到乘客：%s（异常：%s）" % (user, str(e)))
                print(u"   请检查：1. 乘客名是否与12306完全一致（无空格/错别字）；2. 该乘客是否已添加到12306常用联系人")

    """选择席别（如二等座、硬卧）"""
    def confirmOrder(self):
        print(u"选择席别...")
        if self.seatType:
            try:
                seat_radio = self.driver.find_element(By.XPATH,
                                                      f"//input[@name='seatType' and @value='{self.seatType}']")
                if not seat_radio.is_selected():
                    seat_radio.click()
                    sleep(0.3)
            except Exception as e:
                print(u"席别选择异常：%s，使用默认席别" % str(e))
        else:
            print(u"未指定席别，使用默认")

    """提交订单"""

    def submitOrder(self):
        print(u"提交订单...")
        try:
            self.driver.find_element(By.ID, 'submitOrder_id').click()
            sleep(2)  # 等待确认弹窗加载
        except Exception as e:
            print(u"提交订单异常：%s" % str(e))
            raise

    """确认选座（处理无座情况）"""

    def confirmSeat(self):
        print(u"确认选座...")
        try:
            # 检查是否无票（模糊匹配提示文本）
            no_seat = self.driver.find_elements(By.XPATH,
                                                "//div[contains(text(), '无票') or contains(text(), '余票0')]")
            if not no_seat or self.noseat_allow == 1:
                self.driver.find_element(By.ID, 'qr_submit_id').click()
                print(u"订单提交成功！请在30分钟内完成支付。")
            else:
                self.driver.find_element(By.ID, 'back_edit_id').click()
                print(u"无可用座位，已返回编辑页")
        except Exception as e:
            print(u"确认选座异常：%s" % str(e))
            raise

    """完整购票流程（串联所有步骤）"""

    def buyTickets(self):
        t_start = time.time()
        try:
            print(u"购票流程启动...")
            self.preStart()
            self.driver.refresh()
            sleep(2)

            # 选择车次（按配置决定选第N个还是第一个）
            if self.order != 0:
                self.specifyTrainNo()
            else:
                self.buyOrderZero()

            # 等待乘车人页面加载（避免元素未渲染）
            sleep(3)  # 增加3秒等待，确保页面完全加载
            print(u"等待乘车人页面加载完成...")

            # 选择乘车人→选择席别→提交订单→确认选座
            self.selUser()
            self.confirmOrder()
            self.submitOrder()
            self.confirmSeat()

            print(u"购票流程完成，总耗时：%.2f秒" % (time.time() - t_start))
        except Exception as e:
            print(u"购票异常：%s" % str(e))
            traceback.print_exc()

    """入口函数：初始化防反爬浏览器"""
    def start(self):
        print(u"初始化浏览器（防反爬配置）...")
        # Chrome防反爬配置
        chrome_options = Options()
        # 1. 指定本地Chrome浏览器路径
        chrome_options.binary_location = "C:\\Users\\Administrator\\PycharmProjects\\chrome-win\\chrome.exe"
        # 2. 禁用自动化检测开关
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        # 3. 隐藏webdriver标识（核心防检测）
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        # 4. 模拟正常浏览器窗口大小
        chrome_options.add_argument("window-size=1400,1000")
        # 5. 设置正常User-Agent
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")
        # 6. 配置日志级别
        chrome_options.set_capability("goog:loggingPrefs", {"browser": "SEVERE"})

        try:
            # 初始化Chrome驱动
            chrome_service = Service(executable_path=self.executable_path)
            self.driver = webdriver.Chrome(
                service=chrome_service,
                options=chrome_options  # 仅保留service和options参数
            )
            # 额外隐藏webdriver属性（双重保险）
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
            })
            print(u"浏览器初始化成功")

            # 启动核心流程
            self.login()
            self.driver.get(self.ticket_url)
            sleep(2)
            self.buyTickets()

        except Exception as e:
            print(u"初始化异常：%s" % str(e))
            traceback.print_exc()
        finally:
            input(u"操作完成，按回车键关闭浏览器...")
            self.driver.quit()

if __name__ == '__main__':
    print("===========hack12306 begin===========")
    # 解决Windows中文显示乱码
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    # 启动程序
    ticket_hacker = hackTickets()
    ticket_hacker.start()
