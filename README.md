## Python 网络接口逆向、会话保持、多线程请求练手项目

python 3.11，利用selenium自动操作浏览器进行购票操作

### 文件说明

README.md：说明文件

city_code.txt：城市中文名与三字码对应文件

config.ini：配置文件

12306.py：主程序

### 环境说明

python3.11	selenium4.35.0

### 依赖包

pip install selenium

### 使用方法

0.准备合适版本的chrome.exe和chromedriver.exe（下载地址：https://vikyd.github.io/download-chromium-history-version/#/）

1.提前将待购票的乘车人姓名加入登录的账号里

2.按照注释说明根据需要修改config.ini文件

3.直接运行（验证码需在60s内手动获取输入！）

4.若找不到合适车票将一直循环查询直至找到

5.提交订单后自行支付

