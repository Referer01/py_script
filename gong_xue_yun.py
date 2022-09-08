# coding:utf-8
import json
import logging
import hashlib
import requests
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# import datetime

logger = logging.getLogger()

loginURL = "https://api.moguding.net:9000/session/user/v3/login"
doCardURL = "https://api.moguding.net:9000/attendence/clock/v2/save"
planIdURL = "https://api.moguding.net:9000/practice/plan/v3/getPlanByStu"

pre = {
    # "http": "http://218.2.214.107:80",
    # "https": "https://http://101.34.59.236:8876"
}

logData = []

headers = {
    "Host": "api.moguding.net:9000",
    "Accept-Language": "zh-CN,zh;q=0.8",
    "User-Agent": "Mozilla/5.0 (Linux; Android 7.0; HTC M9e Build/EZG0TF) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/55.0.1566.54 Mobile Safari/537.36",
    # "User-Agent": "gxy/3.5.6 (iPhone; iOS 15.6.1; Scale/3.00)",
    "sign": "",
    'Connection': 'keep-alive',
    "Authorization": "",
    "roleKey": "student",
    "Content-Type": "application/json; charset=UTF-8",
    "Accept-Encoding": "",
}


def readFile():
    # account_data = ""
    dataList = []
    # try:
    with open("account.txt", "r+", encoding="UTF-8") as obj:
        readline = obj.readlines()
        for i in readline:
            if i:
                json_loads = json.loads(i)
                dataList.append(json_loads)
            else:
                pass
        return dataList


class User_PO:
    def __init__(self):
        self.userData = readFile()

    def do(self):
        for data in self.userData:
            if data.get("account") is not None and data.get("password") is not None:
                if data.get("state") is not None and data.get("state") == 1:
                    # 下班
                    data["cardType"] = "END"
                else:
                    # 上班
                    data["cardType"] = "START"
                if data.get("token") is not None:
                    # 获得签到的签名
                    sign = getSign(data.get("cardType"), data.get("planId"), data.get("userId"), data.get("address"))
                    data["sign"] = sign
                    doCard(data)
                else:
                    doLogin(data)
                    if data.get("userId") is None:
                        continue
                    planSign = getPlanIdSign(data["userId"])
                    # //获得planId
                    plan_id = getPlanId(headers, str(data.get("token")), str(planSign))
                    data["planId"] = plan_id
                    # 获得签到的签名
                    sign = getSign(data.get("cardType"), plan_id, data.get("userId"), data.get("address"))
                    data["sign"] = sign
                    doCard(data)
            else:
                logger.error("请填写账号密码")
                pushMessge(data.get("plusToken"), "请填写账号密码")
        t = open("account.txt", 'w+', encoding="UTF-8")
        writeData = ""
        for data in self.userData:
            writeData = writeData + json.dumps(data, ensure_ascii=False) + "\n"

        t.write(writeData)
        t.close()

        fileName = time.strftime("%Y-%m-%d--%H", time.localtime()) + "工学云打卡日志.txt"
        text_io = open("logs/" + fileName, "w", encoding="UTF-8")
        for line in logData:
            text_io.write(line + "\n")

        text_io.close()
    # 登陆


def doLogin(data):
    account_ = encrypt(data.get("account"))
    password_ = encrypt(data.get("password"))
    loginData = {
        "phone": account_,
        "password": password_,
        "loginType": "android",
        "uuid": "",
        "t": getT()
    }
    loginResult = requests.post(loginURL, headers=headers, data=json.dumps(loginData)).json()
    if loginResult["code"] != 200:
        logger.error(loginResult["msg"])
        pushMessge(data.get("plusToken"), loginResult["msg"])
        errorLog = data.get("account") + loginResult["msg"] + time.strftime("%Y-%m-%d -- %H:%M:%S", time.localtime())
        logData.append(errorLog)
    else:
        # 将获取到的用户信息存入
        data["token"] = str(loginResult["data"]["token"])
        data["userId"] = str(loginResult["data"]["userId"])
        data["moguNo"] = str(loginResult["data"]["moguNo"])


# 推送消息
def pushMessge(token, message):
    hea = {
        "Content-Type": "application/json; charset=UTF-8",
    }
    url = "http://www.pushplus.plus/send"
    requestData = {
        "token": token,
        "title": "学工云打卡通知",
        "content": message
    }
    result = requests.post(url, headers=hea, data=json.dumps(requestData)).json()
    print(result)


def bytesToHexString(bs):
    return ''.join(['%02X' % b for b in bs])


# 加密参数
def encrypt(word, key="23DbtQHR2UMbH6mJ"):
    key = key.encode('utf-8')
    mode = AES.MODE_ECB
    aes = AES.new(key, mode)
    pad_pkcs7 = pad(word.encode('utf-8'), AES.block_size, style='pkcs7')  # 选择pkcs7补全
    encrypt_aes = aes.encrypt(pad_pkcs7)
    encrypted_text = bytesToHexString(encrypt_aes)
    return encrypted_text.replace(" ", "").lower()


# 对字符进行加密
def getMd5(byStr):
    encode = byStr.encode('utf-8')
    return hashlib.md5(encode).hexdigest()


def getT():
    t = str(int(time.time()) * 1000)
    return encrypt(t)


# 获取planId的sign
def getPlanIdSign(userId):
    byStr = str(userId) + "student" + "3478cbbc33f84bd00d75d7dfa69e0daa"
    return getMd5(byStr)


# 获取签到sign
def getSign(cardType, planId, userId, address):
    byStr = "Android" + str(cardType) + str(planId) + str(userId) + str(address) + "3478cbbc33f84bd00d75d7dfa69e0daa"
    return getMd5(byStr)


# 获得planId
def getPlanId(hea, token, palnIdSign):
    hea["sign"] = palnIdSign
    hea["Authorization"] = token
    hea["roleKey"] = "student"
    data = {
        "state": ""
    }
    planIdResult = requests.post(planIdURL, headers=hea, data=json.dumps(data)).json()
    print(planIdResult)
    return str(planIdResult["data"][0]["planId"])


def doCard(data):
    cardData = {
        "country": data.get("country"),
        "address": data.get("address"),
        "province": data.get("province"),
        "city": data.get("city"),
        "latitude": data.get("latitude"),
        "description": "",
        "planId": data.get("planId"),
        "type": data.get("cardType"),
        "device": "Android",
        "longitude": data.get("longitude"),
    }
    headers["sign"] = data.get("sign")
    headers["Authorization"] = data.get("token")
    doCardResult = requests.post(doCardURL, headers=headers, proxies=pre, data=json.dumps(cardData)).json()
    logger.info(str(doCardResult))
    print("打卡结果是；" + str(doCardResult))
    if doCardResult.get("code") == 200:
        # 切换状态
        if data.get("state") == 1:
            data["state"] = 0
            logger.info(data.get("account") + "下班打卡成功")
            pushMessge(data.get("plusToken"), "下班打卡成功！")
        else:
            data["state"] = 1
            logger.info(data.get("account") + "上班打卡成功")
            pushMessge(data.get("plusToken"), "上班打卡成功！")
        log = data.get("account") + "打卡成功" + time.strftime("%Y-%m-%d -- %H:%M:%S", time.localtime())
        logData.append(log)
    elif doCardResult.get("code") == 401:
        del data["token"]
        del data["userId"]
        del data["planId"]
        del data["sign"]
        doLogin(data)
        if data.get("userId") is None:
            return
        planSign = getPlanIdSign(data["userId"])
        plan_id = getPlanId(headers, str(data.get("token")), str(planSign))
        data["planId"] = plan_id
        sign = getSign(data.get("cardType"), plan_id, data.get("userId"), data.get("address"))
        data["sign"] = sign
        doCard(data)
    else:
        logger.error(data.get("account") + "打卡失败，未知异常！！")
        pushMessge(data.get("plusToken"), "打卡失败，未知异常！！")
        errorLog = data.get("account") + doCardResult["msg"] + time.strftime("%Y-%m-%d -- %H:%M:%S", time.localtime())
        logData.append(errorLog)


if __name__ == "__main__":
    po = User_PO()
    po.do()

# def main_handler(event, context):
#     logger.info('got event{}'.format(event))
#     return User_PO().do()
