## 在国内端部署 GFW检测程序

```shell
sudo docker run -d -p 5000:5000  --restart unless-stopped --name checkip betteryjs/checkip

```

## 在 https://t.me/BotFather 创建通知机器人 
## 通过 https://t.me/getmyid_bot 获取私聊chat_id 或者 通过 https://t.me/get_id_bot 获取群组chat_id

## 提前将 Hinet的ip 解析到要设置ddns的域名上
## 克隆项目

```shell
git clone git@github.com:betteryjs/EcsAutoChangeIP.git

cd EcsAutoChangeIP
```

## 复制` config.json.exp` 到 `config.json` 修改其中字段


```shell
{
  "AccessKeyId": "xxxxx", 填入阿里云AccessKeyId
  "AccessKeySecret": "xxxxx",  填入阿里云AccessKeySecret
  "region_id":"cn-hongkong", # 填入机器的地域
  "name": "aliyun-HK-ECS",  # 填入通知名字
  "email": "xxxxxx@gmail.com", # 填入CF的个人邮箱
  "api_key": "xxxxxxxxxxxx", # 填入CF的Global API Key	
  "domain": "example.xyz", # 填入ddns的主域名
  "TGBotAPI": "xxxxxxxxxxx", # 填入Botfather上面获取的TG bot token
  "chartId": "xxxxxxxxxx", # 填入上面获取的私聊chat_id或者群组chat_id
  "ddnsUrl": "test.660114.xyz", # 填入要ddns的域名 先要吧Hinet的ip解析到要ddns的域名上
  "checkGFWUrl": "http://填入在国内端部署的GFW检测程序的IP:5000/checkip/", # 例如 http://1.1.1.1:5000/checkip/
  "changeIPCrons": "0 3 * * *", #每日换IP的crontab 时间 默认每天凌晨3点
  "checkGfwCron": "*/10 * * * *", # 被墙检测默认10分钟1次
  "Linetype": "BGP",        # IP的类型 BGP 或者 BGP_PRO  BGP（默认值）：BGP（多线）线路。目前全部地域都支持 BGP（多线）线路 EIP。BGP_PRO：BGP（多线）_精品线路。目前仅中国香港、新加坡、日本（东京）、马来西亚（吉隆坡）、菲律宾（马尼拉）、印度尼西亚（雅加达）和泰国（曼谷）地域支持 BGP（多线）_精品线路 EIP。
  "InstanceId": "xxxxxx"    # 要开启自动换IP的实例ID
}

```


## 在机子上安装python

```
apt install python3-pip python3-venv
```

## 创建虚拟环境 venv
```
python3 -m venv .venv
source .venv/bin/activate
```

## install requirements.txt

```
pip install -r requirements.txt
```


## 复制 service
```
cp  EcsTGBot.service  /lib/systemd/system/
chmod 644 /lib/systemd/system/EcsTGBot.service
systemctl start EcsTGBot.service
systemctl enable EcsTGBot.service
systemctl status EcsTGBot.service

```





![1](images/1.png)
![1](images/2.png)
![1](images/3.png)


