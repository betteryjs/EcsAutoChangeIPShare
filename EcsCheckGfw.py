# ./nf -proxy socks5://hinet.660114.xyz:10241
import json
import subprocess
import requests
from cloudflare_ddns import CloudFlare
from loguru import logger

logger.remove(handler_id=None)  # 清除之前的设置
logger.add("ECS_IP.log", rotation="10MB", encoding="utf-8", enqueue=True, retention="5 days")


from EcsChangeIP import CreateEIP

eip = CreateEIP()


class CheckGFW(object):


    def __init__(self):
        with open("config.json", 'r') as file:
            configJson = json.loads(file.read())

        self.API = configJson["TGBotAPI"]
        self.sendTelegramUrl = "https://api.telegram.org/bot" + self.API + "/sendMessage"
        self.chartId = configJson["chartId"]
        self.name = configJson["name"]
        self.checkGFWUrl = configJson["checkGFWUrl"]
        self.email = configJson["email"]
        self.api_key = configJson["api_key"]
        self.domain = configJson["domain"]
        self.ddnsUrl = configJson["ddnsUrl"]
        self.cf = CloudFlare(self.email, self.api_key, self.domain)





    def sendTelegram(self,msg):
        params={
            "chat_id":self.chartId,
            "text": msg
        }
        resp=requests.get(url=self.sendTelegramUrl,params=params)
        logger.debug(resp.text)



    def get_ip(self):
        try:
            res = self.cf.get_record('A', self.ddnsUrl)
            return res["content"]

        except Exception as err:
            logger.error(err)





    def check_gfw_block(self):
        gfwUrl = self.checkGFWUrl + self.get_ip()
        resp = requests.get(url=gfwUrl).json()
        if resp["isblock"]==True:
            msg="[{}]-[GFW检测]-[IP ban 啦]".format(self.name)
            self.sendTelegram(msg)
            logger.debug(msg)
            eip.changeEcsIP()
        else:
            logger.debug("[{}]-[GFW检测]-[IP正常]".format(self.name))

    def check_gfw_block_tg(self):
        gfwUrl = self.checkGFWUrl + self.get_ip()
        resp = requests.get(url=gfwUrl).json()
        if resp["isblock"]==True:
            msg="[{}]-[GFW检测]-[IP ban 啦]".format(self.name)
            logger.debug(msg)
            return msg
        else:
            msg="[{}]-[GFW检测]-[IP正常]".format(self.name)
            logger.debug(msg)
            return msg












if __name__ == '__main__':

    gfwtest=CheckGFW()
    gfwtest.check_gfw_block()


