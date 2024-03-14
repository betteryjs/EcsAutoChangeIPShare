import json
import time

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.auth.credentials import AccessKeyCredential
from aliyunsdkvpc.request.v20160428.AddCommonBandwidthPackageIpRequest import AddCommonBandwidthPackageIpRequest
from aliyunsdkvpc.request.v20160428.AllocateEipAddressRequest import AllocateEipAddressRequest
from aliyunsdkvpc.request.v20160428.AssociateEipAddressRequest import AssociateEipAddressRequest
from aliyunsdkvpc.request.v20160428.CreateCommonBandwidthPackageRequest import CreateCommonBandwidthPackageRequest
from aliyunsdkvpc.request.v20160428.DescribeCommonBandwidthPackagesRequest import DescribeCommonBandwidthPackagesRequest
from aliyunsdkvpc.request.v20160428.DescribeEipAddressesRequest import DescribeEipAddressesRequest
from aliyunsdkvpc.request.v20160428.ReleaseEipAddressRequest import ReleaseEipAddressRequest
from aliyunsdkvpc.request.v20160428.RemoveCommonBandwidthPackageIpRequest import RemoveCommonBandwidthPackageIpRequest
from aliyunsdkvpc.request.v20160428.UnassociateEipAddressRequest import UnassociateEipAddressRequest
from cloudflare_ddns import CloudFlare
from loguru import logger

logger.remove(handler_id=None)  # 清除之前的设置
logger.add("ECS_IP.log", rotation="10MB", encoding="utf-8", enqueue=True, retention="5 days")


class CreateEIP:
    def __init__(self):

        with open("config.json", 'r') as file:
            self.configJson = json.loads(file.read())

        self.email = self.configJson["email"]
        self.api_key = self.configJson["api_key"]
        self.domain = self.configJson["domain"]
        self.API = self.configJson["TGBotAPI"]
        self.sendTelegramUrl = "https://api.telegram.org/bot" + self.API + "/sendMessage"
        self.chartId = self.configJson["chartId"]
        self.ddnsUrl = self.configJson["ddnsUrl"]
        self.name = self.configJson["name"]
        self.changeIPCrons = self.configJson["changeIPCrons"]
        self.checkGfwCron = self.configJson["checkGfwCron"]
        self.AccessKeyId = self.configJson["AccessKeyId"]
        self.AccessKeySecret = self.configJson["AccessKeySecret"]
        self.region_id = self.configJson["region_id"]
        self.Linetype = self.configJson["Linetype"]
        self.InstanceId = self.configJson["InstanceId"]

        self.AllocationId = ""
        self.EipAddress = ""
        self.BandwidthPackageId = ""

        if self.Linetype == "BGP":
            self.EcsAutoBandName = "EcsAutoBandBGP"
        elif self.Linetype == "BGP_PRO":
            self.EcsAutoBandName = "EcsAutoBandBGP_PRO"

        self.cf = CloudFlare(self.email, self.api_key, self.domain)
        self.credentials = AccessKeyCredential(self.AccessKeyId, self.AccessKeySecret)
        self.client = AcsClient(region_id=self.region_id, credential=self.credentials)

        self.sleepTime = 5

        # 创建共享带宽
        self.EcsAutoBandBGPID = self.findCommonBandwidthPackage("EcsAutoBandBGP")
        self.EcsAutoBandBGP_PROID = self.findCommonBandwidthPackage("EcsAutoBandBGP_PRO")
        if self.EcsAutoBandBGPID == "":
            self.EcsAutoBandBGPID = self.createCommonBandwidthPackage("BGP", "EcsAutoBandBGP")
        if self.EcsAutoBandBGP_PROID == "":
            self.EcsAutoBandBGP_PROID = self.createCommonBandwidthPackage("BGP_PRO", "EcsAutoBandBGP_PRO")





    def allocipinfo(self):
        request = DescribeEipAddressesRequest()
        request.set_accept_format('json')
        request.set_ISP("BGP")
        response = json.loads(self.client.do_action_with_exception(request).decode())
        if not response["EipAddresses"]["EipAddress"]:
            return "BGP_PRO"
        else:
            return "BGP"

    def createIP(self):

        request = AllocateEipAddressRequest()
        request.set_accept_format('json')

        request.set_Bandwidth("200")
        request.set_ISP(self.Linetype)
        request.set_InternetChargeType("PayByTraffic")
        request.set_InstanceChargeType("PostPaid")
        request.set_AutoPay(True)
        request.set_Description("EcsAutoIP")

        response = json.loads(self.client.do_action_with_exception(request).decode())
        self.AllocationId = response["AllocationId"]
        self.EipAddress = response["EipAddress"]
        logger.info("create EIP success! EipAddress is {} and Linetype is {}".format(self.EipAddress, self.Linetype))
        self.cf_ddns(self.EipAddress)
        return self.AllocationId

    def createCommonBandwidthPackage(self, Linetype, EcsAutoBandName):
        request = CreateCommonBandwidthPackageRequest()
        request.set_accept_format('json')

        request.set_ISP(Linetype)
        request.set_Bandwidth(2000)
        request.set_InternetChargeType("PayByDominantTraffic")

        request.set_Name(EcsAutoBandName)

        response = json.loads(self.client.do_action_with_exception(request).decode())

        logger.info("{} create success and BandwidthPackageId is {}".format(EcsAutoBandName,
                                                                            response["BandwidthPackageId"]))
        return response["BandwidthPackageId"]

    def deleteIP(self):
        request = ReleaseEipAddressRequest()
        request.set_accept_format('json')
        logger.info(self.findAllocationId())
        request.set_AllocationId(self.findAllocationId())

        response = self.client.do_action_with_exception(request).decode()
        logger.info(f"{self.EipAddress} delete success!")

    def cf_ddns(self, ip):
        self.cf.refresh()
        res = self.cf.get_record('A', self.ddnsUrl)
        logger.debug("改变前 " + res["content"])
        self.cf.update_record(dns_type='A', name=self.ddnsUrl, content=ip, ttl=60)
        res = self.cf.get_record('A', self.ddnsUrl)
        logger.debug("改变后 " + res["content"])

    def findAllocationId(self):
        request = DescribeEipAddressesRequest()
        request.set_accept_format('json')
        response = json.loads(self.client.do_action_with_exception(request).decode())["EipAddresses"]["EipAddress"]
        if not response:
            logger.info("EcsAutoIP not exist")

            return ""
        else:
            for i in response:
                if i["Description"] == "EcsAutoIP":
                    logger.info("EcsAutoIP exist and AllocationId is {}".format(i["AllocationId"]))
                    self.AllocationId = i["AllocationId"]
                    self.EipAddress = i["IpAddress"]
                    return i["AllocationId"]
        logger.info("EcsAutoIP not exist")
        return ""

    def findCommonBandwidthPackage(self, EcsAutoBandName):

        request = DescribeCommonBandwidthPackagesRequest()
        request.set_accept_format('json')

        request.set_Name(EcsAutoBandName)

        response = json.loads(self.client.do_action_with_exception(request).decode())
        if not response["CommonBandwidthPackages"]["CommonBandwidthPackage"]:
            logger.info(f"{EcsAutoBandName} not exist ")

            return ""
        else:

            self.BandwidthPackageId = response["CommonBandwidthPackages"]["CommonBandwidthPackage"][0][
                "BandwidthPackageId"]

            logger.info("{} exist and BandwidthPackageId is {}".format(
                response["CommonBandwidthPackages"]["CommonBandwidthPackage"][0]["Name"],
                self.BandwidthPackageId
            ))
            return self.BandwidthPackageId

    def ecsAddToCommonBandwidthPackage(self, AllocationId, BandwidthPackageId):
        request = AddCommonBandwidthPackageIpRequest()
        request.set_accept_format('json')
        request.set_BandwidthPackageId(BandwidthPackageId)
        request.set_IpInstanceId(AllocationId)
        request.set_IpType("EIP")
        self.client.do_action_with_exception(request)
        logger.info("{} add to {} success!".format(AllocationId, BandwidthPackageId))

    def RemoveCommonBandwidthPackageIp(self,AllocationId,BandwidthPackageId):
        request = RemoveCommonBandwidthPackageIpRequest()
        request.set_accept_format('json')

        request.set_BandwidthPackageId(BandwidthPackageId)
        request.set_IpInstanceId(AllocationId)
        logger.info("RemoveCommonBandwidthPackageIp")
        self.client.do_action_with_exception(request)
        logger.info("{} remove to {} success!".format(AllocationId, BandwidthPackageId))

    def IPBandEcs(self):
        request = AssociateEipAddressRequest()
        request.set_accept_format('json')
        request.set_AllocationId(self.AllocationId)
        request.set_InstanceId(self.InstanceId)
        response = self.client.do_action_with_exception(request)
        logger.info(f"{self.EipAddress} band in {self.InstanceId} success!")

    def IPremoveEcs(self):

        request = UnassociateEipAddressRequest()
        request.set_accept_format('json')

        request.set_AllocationId(self.AllocationId)

        self.client.do_action_with_exception(request)
        logger.info(f"{self.EipAddress} remove to  {self.InstanceId} success!")

    def get_ip(self):
        try:
            self.cf.refresh()
            res = self.cf.get_record('A', self.ddnsUrl)
            return res["content"]

        except Exception as err:
            logger.error(err)

    def changeEcsIP(self):
        if self.findAllocationId() == "":
            self.createIP()
            time.sleep(self.sleepTime)
            self.IPBandEcs()
            if self.Linetype == "BGP":
                self.ecsAddToCommonBandwidthPackage(self.AllocationId, self.EcsAutoBandBGPID)
            elif self.Linetype == "BGP_PRO":
                self.ecsAddToCommonBandwidthPackage(self.AllocationId, self.EcsAutoBandBGP_PROID)
        else:
            self.IPremoveEcs()
            time.sleep(self.sleepTime)
            if self.allocipinfo()=="BGP":
                self.RemoveCommonBandwidthPackageIp(self.AllocationId,self.EcsAutoBandBGPID)
            elif self.allocipinfo()=="BGP_PRO":
                self.RemoveCommonBandwidthPackageIp(self.AllocationId,self.EcsAutoBandBGP_PROID)

            self.deleteIP()


            self.createIP()
            if self.allocipinfo() == "BGP":
                self.ecsAddToCommonBandwidthPackage(self.AllocationId, self.EcsAutoBandBGPID)
            elif self.allocipinfo() == "BGP_PRO":
                self.ecsAddToCommonBandwidthPackage(self.AllocationId, self.EcsAutoBandBGP_PROID)
            time.sleep(self.sleepTime)
            self.IPBandEcs()

    def eipInTheCommonBand(self):
        request = DescribeCommonBandwidthPackagesRequest()
        request.set_accept_format('json')

        request.set_BandwidthPackageId(self.BandwidthPackageId)
        logger.info(self.BandwidthPackageId)
        response = json.loads(self.client.do_action_with_exception(request).decode())

        if not response["CommonBandwidthPackages"]["CommonBandwidthPackage"]:
            logger.info("{} not in the {}".format(self.AllocationId, self.BandwidthPackageId))
            return False
        else:
            for i in response["CommonBandwidthPackages"]["CommonBandwidthPackage"]:
                for j in i["PublicIpAddresses"]["PublicIpAddresse"]:
                    if self.AllocationId == j["AllocationId"]:
                        logger.info("{} in the {}".format(self.AllocationId, self.BandwidthPackageId))
                        return True
            logger.info("{} not in the {}".format(self.AllocationId, self.BandwidthPackageId))
        return False

    def changetoBGPPro(self):

        self.configJson["Linetype"] = "BGP_PRO"
        self.Linetype = "BGP_PRO"
        with open("config.json", "w") as file:
            file.write(json.dumps(self.configJson))

    def changetoBGP(self):
        self.configJson["Linetype"] = "BGP"
        self.Linetype = "BGP"
        with open("config.json", "w") as file:
            file.write(json.dumps(self.configJson))

    def showBgpOrPro(self):
        return self.configJson["Linetype"]


if __name__ == '__main__':
    createip = CreateEIP()
    createip.changeEcsIP()
