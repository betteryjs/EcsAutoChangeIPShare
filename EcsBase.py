from datetime import datetime
import json
import time

import requests
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.auth.credentials import AccessKeyCredential
from aliyunsdkcore.request import CommonRequest
from aliyunsdkecs.request.v20140526.AuthorizeSecurityGroupRequest import AuthorizeSecurityGroupRequest
from aliyunsdkecs.request.v20140526.CreateSecurityGroupRequest import CreateSecurityGroupRequest
from aliyunsdkecs.request.v20140526.DescribeSecurityGroupAttributeRequest import DescribeSecurityGroupAttributeRequest
from aliyunsdkecs.request.v20140526.DescribeSecurityGroupsRequest import DescribeSecurityGroupsRequest
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
from croniter import croniter
from threading import Thread, Event

from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_cdt20210813 import models as cdt_models
from alibabacloud_tea_util.models import RuntimeOptions
from alibabacloud_cdt20210813.client import Client


class CDTClient:
    def __init__(self, AccessKeyId,AccessKeySecret,region_id):
        config = open_api_models.Config(
            access_key_id=AccessKeyId,
            access_key_secret=AccessKeySecret
        )
        config.endpoint = "cdt.aliyuncs.com"
        self.client = Client(config)
        self.region_id = region_id

    def get_cdt_traffic(self):
        request = cdt_models.ListCdtInternetTrafficRequest(
            business_region_id=self.region_id
        )
        runtime = RuntimeOptions()
        try:
            response = self.client.list_cdt_internet_traffic_with_options(request, runtime)
            traffic_details = response.body.traffic_details
            for i in range(len(traffic_details)):
                totals = traffic_details[i].to_map()
                if totals['ISPType'] == 'bgp':
                    return sum([c['Traffic'] for c in totals['ProductTrafficDetails']]) / 1024 / 1024 / 1024

        except Exception as e:
                print(f"Error occurred: {str(e)}")


class BaseEIP:
    def __init__(self):
        with open("config.json", 'r') as file:
            self.configJson = json.loads(file.read())
        self.email = self.configJson["BaseConfig"]["email"]
        self.api_key = self.configJson["BaseConfig"]["api_key"]
        self.domain = self.configJson["BaseConfig"]["domain"]
        self.API = self.configJson["BaseConfig"]["TGBotAPI"]
        self.sendTelegramUrl = "https://api.telegram.org/bot" + self.API + "/sendMessage"
        self.chartId = self.configJson["BaseConfig"]["chartId"]
        self.checkgfwport = self.configJson["BaseConfig"]["checkgfwport"]
        self.checkGFWUrl = self.configJson["BaseConfig"]["checkGFWUrl"]


class CreateEIP(BaseEIP):
    def __init__(self, EIPConfig):
        super().__init__()
        logger.info(EIPConfig)
        self.ddnsUrl = EIPConfig["ddnsUrl"]
        self.name = EIPConfig["name"]
        self.changeIPCrons = EIPConfig["changeIPCrons"]
        self.checkGfwCron = EIPConfig["checkGfwCron"]
        self.AccessKeyId = EIPConfig["AccessKeyId"]
        self.AccessKeySecret = EIPConfig["AccessKeySecret"]
        self.region_id = EIPConfig["region_id"]
        self.Linetype = EIPConfig["Linetype"]
        self.InstanceId = EIPConfig["InstanceId"]
        self.cdtMax = EIPConfig["cdtMax"]

        self.AllocationId = ""
        self.EipAddress = ""
        self.BandwidthPackageId = ""

        # timmer
        # 定时器存储
        self.timers = {}

        # 初始化定时器，但不启动
        self.initialize_timer('checkGfw', self.checkGfwCron, self.check_gfw_block)
        self.initialize_timer('changeip', self.changeIPCrons, self.changeEcsIP)
        self.initialize_timer('checkCdt', self.checkGfwCron, self.checkCdt)

        self.initialize_timer('enableCdt', "0 0 1 * *", self.enableTraffic)
        # 每月1号启动enableTraffic
        self.start_timer("enableCdt")


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
        # 创建SecurityGroup
        self.SecurityGroupId=self.findSecurityGroupId()
        if self.SecurityGroupId == "":
            self.SecurityGroupId=self.creatSecurityGroupId()
        self.instanceAddInSecurityGroup()

        # 默认是开启所有流量入
        self.enableTraffic()


    def findSecurityGroupId(self):
        request = DescribeSecurityGroupsRequest()
        request.set_accept_format('json')

        request.set_MaxResults(100)

        response = json.loads(self.client.do_action_with_exception(request).decode('utf-8'))["SecurityGroups"][
            "SecurityGroup"]
        for i in response:
            if i["SecurityGroupName"] == "EcsAutoSecurityGroup":
                logger.success(f"find SecurityGroupId success and SecurityGroupId is {i['SecurityGroupId']}")
                return i["SecurityGroupId"]
        return ""


    def creatSecurityGroupId(self):
        request = CreateSecurityGroupRequest()
        request.set_accept_format('json')

        request.set_SecurityGroupName("EcsAutoSecurityGroup")

        SecurityGroupId = json.loads(self.client.do_action_with_exception(request).decode('utf-8'))['SecurityGroupId']
        logger.success(f"create SecurityGroupId success and SecurityGroupId is {SecurityGroupId}")
        return SecurityGroupId


    def instanceAddInSecurityGroup(self):
        request = CommonRequest()
        request.set_accept_format('json')
        request.set_domain(f'ecs.{self.region_id}.aliyuncs.com')
        request.set_method('POST')
        request.set_protocol_type('https')  # https | http
        request.set_version('2014-05-26')
        request.set_action_name('ModifyInstanceAttribute')

        request.add_query_param('SecurityGroupIds.1', self.SecurityGroupId)
        request.add_query_param('InstanceId', self.InstanceId)

        response = self.client.do_action_with_exception(request)
        logger.success(f"SecurityGroupId : {self.SecurityGroupId} add to InstanceId : {self.InstanceId} success!")




    def allocipinfo(self):
        request = DescribeEipAddressesRequest()
        request.set_accept_format('json')
        request.set_ISP("BGP")
        response = json.loads(self.client.do_action_with_exception(request).decode())
        if not response["EipAddresses"]["EipAddress"]:
            return "BGP_PRO"
        else:
            return "BGP"

    def check_gfw_block(self):
        gfwUrl = self.checkGFWUrl + self.get_ip() + ":" + self.checkgfwport
        resp = requests.get(url=gfwUrl).json()
        logger.info(gfwUrl)
        logger.info(resp)
        if resp["isblock"] == True:
            self.changeEcsIP()
            msg = f"IP Ban啦  IP已更换为   {self.get_ip()}"
            logger.info(msg)

        else:
            msg = "[{}]-[GFW检测]-[IP正常]".format(self.name)
            logger.info(msg)
        return msg

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
        try:
            res = self.cf.get_record('A', self.ddnsUrl)
            logger.info("改变前 " + res["content"])
        except Exception as e:
            logger.error(e)
        self.cf.create_or_update_record(dns_type='A', name=self.ddnsUrl, content=ip, ttl=60)
        res = self.cf.get_record('A', self.ddnsUrl)
        logger.info("改变后 " + res["content"])

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

    def RemoveCommonBandwidthPackageIp(self, AllocationId, BandwidthPackageId):
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
            ip = res["content"]
            logger.info("ip is {}".format(ip))
            return ip

        except Exception as err:
            logger.error(err)

    def changeEcsIP(self):
        start = time.time()
        # stop check ip ban
        flag=False
        if self.is_timer_running("checkGfw"):
            flag=True
        if flag:
            self.stop_timer("checkGfw")
            logger.info("关闭checkGfw")

        flag2 = False
        if self.is_timer_running("checkCdt"):
            flag2 = True
        if flag2:
            self.stop_timer("checkCdt")
            logger.info("关闭checkCdt")



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
            if self.allocipinfo() == "BGP":
                self.RemoveCommonBandwidthPackageIp(self.AllocationId, self.EcsAutoBandBGPID)
            elif self.allocipinfo() == "BGP_PRO":
                self.RemoveCommonBandwidthPackageIp(self.AllocationId, self.EcsAutoBandBGP_PROID)

            self.deleteIP()

            self.createIP()
            if self.allocipinfo() == "BGP":
                self.ecsAddToCommonBandwidthPackage(self.AllocationId, self.EcsAutoBandBGPID)
            elif self.allocipinfo() == "BGP_PRO":
                self.ecsAddToCommonBandwidthPackage(self.AllocationId, self.EcsAutoBandBGP_PROID)
            time.sleep(self.sleepTime)
            self.IPBandEcs()

        # start check ip ban
        if flag:
            self.start_timer("checkGfw")
            logger.info("开启checkGfw")

        if flag2:
            self.start_timer("checkCdt")
            logger.info("开启checkCdt")


        msg = "[{}]-[IP更换成功]-[当前IP {}]-[用时 {}s ]".format(self.name, self.EipAddress, int(time.time() - start))
        return msg

    def checkCdt(self):
        # stop check ip ban
        flag = False
        if self.is_timer_running("checkGfw"):
            flag = True
        if flag:
            self.stop_timer("checkGfw")
            logger.info("关闭checkGfw")


        cdt=CDTClient(self.AccessKeyId,self.AccessKeySecret,self.region_id).get_cdt_traffic()
        logger.info(f"instance 流量使用了 {cdt} GB")
        if cdt > (self.cdtMax)*0.95:
            # ban the instance  Traffic in
            self.disableTraffic()
            self.stop_timer("checkCdt")
            logger.info(f"CDT流量超过 {self.cdtMax} 的 95%啦!")
            return


        # start check ip ban
        if flag:
            self.start_timer("checkGfw")
            logger.info("关闭checkGfw")


    def disableTraffic(self):
        requests =[AuthorizeSecurityGroupRequest() for i in range(2)]
        Rules = [["0.0.0.0/0", "AutoIPv4"], ["::/0", "AutoIPv6"]]
        for i in range(len(requests)):
            requests[i].set_accept_format('json')
            requests[i].set_SecurityGroupId(self.SecurityGroupId)
            requests[i].set_Permissions([
                {
                    "Priority": "1",
                    "IpProtocol": "ALL",
                    "SourceCidrIp" if i == 0 else "Ipv6SourceCidrIp": Rules[i][0],
                    "PortRange": "-1/-1",
                    "Policy": "drop",
                    "Description": Rules[i][1]

                }
            ])

            self.client.do_action_with_exception(requests[i])
            logger.success(f"drop {Rules[i][0]} {Rules[i][1]}  add success! ")

    def getSecurityGroupRuleId(self):

        request = DescribeSecurityGroupAttributeRequest()
        request.set_accept_format('json')

        request.set_SecurityGroupId(self.SecurityGroupId)
        request.set_Direction("ingress")
        SecurityGroupRuleIdv4 = ""
        SecurityGroupRuleIdv6 = ""
        SecurityGroupRules = json.loads(self.client.do_action_with_exception(request).decode('utf-8'))['Permissions'][
            "Permission"]
        for SecurityGroupRule in SecurityGroupRules:
            if SecurityGroupRule['Policy'] == 'Drop' and SecurityGroupRule['Description'] == 'AutoIPv4':
                SecurityGroupRuleIdv4 = SecurityGroupRule['SecurityGroupRuleId']
            if SecurityGroupRule['Policy'] == 'Drop' and SecurityGroupRule['Description'] == 'AutoIPv6':
                SecurityGroupRuleIdv6 = SecurityGroupRule['SecurityGroupRuleId']
        return [SecurityGroupRuleIdv4, SecurityGroupRuleIdv6]

    def isdisableTraffic(self):
        return self.getSecurityGroupRuleId() is   ['','']


    def enableTraffic(self):
        SecurityGroupRuleIds=self.getSecurityGroupRuleId()
        for i in range(len(SecurityGroupRuleIds)):
            if SecurityGroupRuleIds[i]!="":
                request = CommonRequest()
                request.set_accept_format('json')
                request.set_domain(f'ecs.{self.region_id}.aliyuncs.com')
                request.set_method('POST')
                request.set_protocol_type('https')  # https | http
                request.set_version('2014-05-26')
                request.set_action_name('RevokeSecurityGroup')

                request.add_query_param('RegionId', self.region_id)
                request.add_query_param('SecurityGroupId', self.SecurityGroupId)
                request.add_query_param('SecurityGroupRuleId.1', SecurityGroupRuleIds[i])

                response = self.client.do_action_with_exception(request)
                # python2:  print(response)
                logger.success(f"drop {SecurityGroupRuleIds[i]} remove success !")



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
        return self.Linetype

    def schedule_cron(self, cron_expression, stop_event, job):
        base_time = datetime.now()
        cron = croniter(cron_expression, base_time)

        while not stop_event.is_set():
            next_run = cron.get_next(datetime)
            sleep_duration = (next_run - datetime.now()).total_seconds()

            if sleep_duration > 0:
                stop_event.wait(sleep_duration)
                if not stop_event.is_set():
                    job()

    def initialize_timer(self, timer_id, cron_expression, job):
        stop_event = Event()
        self.timers[timer_id] = {
            'cron_expression': cron_expression,
            'job': job,
            'stop_event': stop_event,
            'thread': None
        }

    def start_timer(self, timer_id):
        if timer_id in self.timers and self.timers[timer_id]['thread'] is None:
            cron_expression = self.timers[timer_id]['cron_expression']
            job = self.timers[timer_id]['job']
            stop_event = self.timers[timer_id]['stop_event']
            t = Thread(target=self.schedule_cron, args=(cron_expression, stop_event, job))
            self.timers[timer_id]['thread'] = t
            t.start()

    def stop_timer(self, timer_id):
        if timer_id in self.timers and self.timers[timer_id]['thread'] is not None:
            self.timers[timer_id]['stop_event'].set()
            self.timers[timer_id]['thread'].join()
            self.timers[timer_id]['thread'] = None

    def is_timer_running(self, timer_id):
        return timer_id in self.timers and self.timers[timer_id]['thread'] is not None




# if __name__ == '__main__':
#
#     with open("config.json", 'r') as file:
#         EIPConfig  = json.loads(file.read())["EcsConfig"]
#     # c=CreateEIP()
#     # for c in EIPConfig:
#     #     print(c)
#     c = CreateEIP(EIPConfig[0])
#     c.changeEcsIP()
#     b = CreateEIP(EIPConfig[1])
#     b.changeEcsIP()
