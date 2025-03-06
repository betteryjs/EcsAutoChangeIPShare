
# 赞助信息

<div style="text-align: center;">
    <a href="https://www.vmiss.com/">
        <img src="https://www.vmiss.com/wp-content/uploads/2023/11/logo.svg" width="170.7" height="62.9">
    </a>
    <a href="https://www.zovps.com/aff/VWSIBCGP">
        <img src="https://raw.githubusercontent.com/betteryjs/EcsAutoChangeIPShare/refs/heads/master/images/img.png" width="170.7" height="62.9">
    </a>
 <a href="https://yxvm.com">
        <img src="https://raw.githubusercontent.com/betteryjs/EcsAutoChangeIPShare/refs/heads/master/images/logo.webp" width="170.7" height="62.9">
    </a>
</div>


我们非常感谢[Vmiss](https://www.vmiss.com/)  [慈云数据](https://www.zovps.com/aff/VWSIBCGP) [Yxvm](https://yxvm.com/)提供了支持本项目所需的网络基础设施。


# 在国内端部署 GFW检测程序

## `docker`部署

```shell
sudo docker run -d -p 5000:5000  --restart unless-stopped --name checkip betteryjs/checkip
```



## 在 https://t.me/BotFather 创建通知机器人 

## 通过 https://t.me/getmyid_bot 获取私聊chat_id 或者 通过 https://t.me/get_id_bot 获取群组chat_id

## 克隆项目

```shell
git clone git@github.com:betteryjs/EcsAutoChangeIPShare.git

cd EcsAutoChangeIPShare
```

## 复制` config.json.exp` 到 `config.json` 修改其中字段


```shell
{
  "BaseConfig": {
    "email": "xxxxx@gmail.com", # 填入CF的个人邮箱
    "api_key": "xxxx",          # 填入CF的Global API Key	
    "domain": "example.com",    # 填入ddns的主域名
    "TGBotAPI": "xxxx",  # 填入Botfather上面获取的TG bot token
    "chartId": "xxxx",   # 填入上面获取的私聊chat_id或者群组chat_id
    "checkGFWUrl": "http://填入在国内端部署的GFW检测程序的IP:5000/checkip/", # 例如 http://1.1.1.1:5000/checkip/
    "authorized_users": [
      "AS99294837"       # 机器人授权给那些用户
    ],
    "checkgfwport": "10241"             # TCP检测的端口号 可以在这个端口建立一个节点 这样TCP端口就是打开的
  },
  "EcsConfig": [
    {
      "AccessKeyId": "xxxxx", # 填入阿里云AccessKeyId
      "AccessKeySecret": "xxxxx", #填入阿里云AccessKeySecret
      "region_id": "cn-hongkong", # 填入机器的地域
      "name": "AliCloud-HK-ECS",  # 填入通知名字
      "ddnsUrl": "xxxxx", # 填入要ddns的域名 hkg.example.com
      "changeIPCrons": "0 3 * * *", #每日换IP的crontab 时间 默认每天凌晨3点
      "checkGfwCron": "*/1 * * * *", # 被墙检测默认1分钟1次
      "Linetype": "BGP",  # # IP的类型 BGP 或者 BGP_PRO  
      "InstanceId": "xxxxxx",    # 要开启自动换IP的实例ID
      "cdtMax": 180    # cdt 检测
    },
    {
      "AccessKeyId": "xxxxx",
      "AccessKeySecret": "xxxxx",
      "region_id": "ap-northeast-1",
      "name": "AliCloud-JP-ECS",
      "ddnsUrl": "xxxxx",
      "changeIPCrons": "0 3 * * *",
      "checkGfwCron": "*/1 * * * *",
      "Linetype": "BGP",
      "InstanceId": "i-6weiufe1kyocvgpekyq5",
      "cdtMax": 180
    }
  ]
}


```


## 在机子上安装Python环境

```
./initvenv.sh
```






## 配置开启Install
```
./install.sh

```

### 在切换线路后要手动点击更换IP
![1](images/1.png)


