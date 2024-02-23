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
            configJson = json.loads(file.read())

        self.email = configJson["email"]
        self.api_key = configJson["api_key"]
        self.domain = configJson["domain"]
        self.API = configJson["TGBotAPI"]
        self.sendTelegramUrl = "https://api.telegram.org/bot" + self.API + "/sendMessage"
        self.chartId = configJson["chartId"]
        self.ddnsUrl = configJson["ddnsUrl"]
        self.name = configJson["name"]
        self.changeIPCrons = configJson["changeIPCrons"]
        self.checkGfwCron = configJson["checkGfwCron"]
        self.AccessKeyId = configJson["AccessKeyId"]
        self.AccessKeySecret = configJson["AccessKeySecret"]
        self.region_id = configJson["region_id"]
        self.Linetype = configJson["Linetype"]
        self.InstanceId = configJson["InstanceId"]

        self.AllocationId = ""
        self.EipAddress = ""
        self.BandwidthPackageId = ""

        self.cf = CloudFlare(self.email, self.api_key, self.domain)
        self.credentials = AccessKeyCredential(self.AccessKeyId, self.AccessKeySecret)
        self.client = AcsClient(region_id=self.region_id, credential=self.credentials)

        if self.findCommonBandwidthPackage() == "":
            self.createCommonBandwidthPackage()
        if self.findAllocationId() == "":
            self.createIP()
            self.IPBandEcs()
        self.ecsAddToCommonBandwidthPackage()

    def createIP(self):

        request = AllocateEipAddressRequest()
        request.set_accept_format('json')

        request.set_Bandwidth("200")
        request.set_ISP("BGP")
        request.set_InternetChargeType("PayByTraffic")
        request.set_InstanceChargeType("PostPaid")
        request.set_AutoPay(True)
        request.set_Description("EcsAutoIP")

        response = json.loads(self.client.do_action_with_exception(request).decode())
        self.AllocationId = response["AllocationId"]
        self.EipAddress = response["EipAddress"]
        logger.info("create EIP success! EipAddress is {}".format(self.EipAddress))
        self.cf_ddns(self.EipAddress)
        return self.AllocationId

    def createCommonBandwidthPackage(self):
        request = CreateCommonBandwidthPackageRequest()
        request.set_accept_format('json')

        request.set_ISP(self.Linetype)
        request.set_Bandwidth(2000)
        request.set_InternetChargeType("PayByDominantTraffic")
        request.set_Name("EcsAutoBand")

        response = json.loads(self.client.do_action_with_exception(request).decode())

        self.BandwidthPackageId = response["BandwidthPackageId"]
        logger.info("EcsAutoBand create success and BandwidthPackageId is {}".format(response["BandwidthPackageId"]))

    def deleteIP(self):
        request = ReleaseEipAddressRequest()
        request.set_accept_format('json')
        logger.info(self.findAllocationId())
        request.set_AllocationId(self.findAllocationId())

        response = self.client.do_action_with_exception(request).decode()
        print(response)
        logger.info(f"{self.EipAddress} delete success!")

    def cf_ddns(self, ip):
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

    def findCommonBandwidthPackage(self):

        request = DescribeCommonBandwidthPackagesRequest()
        request.set_accept_format('json')

        request.set_Name("EcsAutoBand")

        response = json.loads(self.client.do_action_with_exception(request).decode())
        if not response["CommonBandwidthPackages"]["CommonBandwidthPackage"]:
            logger.info("EcsAutoBand not exist ")

            return ""
        else:
            msg = response["CommonBandwidthPackages"]["CommonBandwidthPackage"][0]["BandwidthPackageId"]
            logger.info("EcsAutoBand exist and BandwidthPackageId is {}".format(msg))

            self.BandwidthPackageId = msg
            return msg

    def ecsAddToCommonBandwidthPackage(self):
        if not self.eipInTheCommonBand():
            request = AddCommonBandwidthPackageIpRequest()
            request.set_accept_format('json')
            request.set_BandwidthPackageId(self.BandwidthPackageId)
            request.set_IpInstanceId(self.AllocationId)
            request.set_IpType("EIP")
            self.client.do_action_with_exception(request)

            logger.info("{} add to {} success!".format(self.AllocationId, self.BandwidthPackageId))

    def RemoveCommonBandwidthPackageIp(self):
        request = RemoveCommonBandwidthPackageIpRequest()
        request.set_accept_format('json')

        request.set_BandwidthPackageId(self.BandwidthPackageId)
        request.set_IpInstanceId(self.AllocationId)

        response = self.client.do_action_with_exception(request)
        logger.info("{} remove to {} success!".format(self.AllocationId, self.BandwidthPackageId))

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
        # python2:  print(response)
        logger.info(f"{self.EipAddress} remove to  {self.InstanceId} success!")

    def get_ip(self):
        try:
            res = self.cf.get_record('A', self.ddnsUrl)
            return res["content"]

        except Exception as err:
            logger.error(err)

    def changeEcsIP(self):
        sleepTime = 1
        time.sleep(sleepTime)
        self.IPremoveEcs()
        time.sleep(sleepTime)
        self.RemoveCommonBandwidthPackageIp()
        self.deleteIP()
        self.createIP()
        self.ecsAddToCommonBandwidthPackage()
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


if __name__ == '__main__':
    createip = CreateEIP()
    createip.changeEcsIP()
