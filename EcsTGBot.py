# stop
import signal
import sys

from telebot import types


def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

from loguru import logger
import json

# loads config
with open("config.json", 'r') as file:
    config_json = json.loads(file.read())

authorized_users = config_json["BaseConfig"]["authorized_users"]
logName = 'AutoChangeIP.log'
logger.remove(handler_id=None)  # 清除之前的设置
logger.add(logName, rotation="15MB", encoding="utf-8", enqueue=True, retention="1 days")

from telebot.util import quick_markup
import telebot
from EcsBase import CreateEIP
from EcsBase import CDTClient

token = config_json["BaseConfig"]["TGBotAPI"]
EIPConfig =config_json["EcsConfig"]
EIPConfigFindID={}
eips=[]
cdts=[]
for i in range(len(EIPConfig)):
    EIPConfigFindID[EIPConfig[i]["name"]]=i
    eips.append(CreateEIP(EIPConfig[i]))
    cdts.append(CDTClient(EIPConfig[i]["AccessKeyId"],EIPConfig[i]["AccessKeySecret"],EIPConfig[i]["region_id"]))

bot = telebot.TeleBot(token)
bot.message_handler(commands=['help'])


def send_welcome(message):
    bot.reply_to(message, "Hello! Send /menu to see the menu.")

    if is_authorized(message.from_user):
        bot.reply_to(message, "Hello! Send /menu to see the menu.")
    else:
        bot.reply_to(message, "You are not authorized to use this bot.")


# @bot.message_handler(commands=['menu'])
# def menu_command(message):
#     if is_authorized(message.from_user):
#         send_menu(message)
#     else:
#         bot.reply_to(message, f"You are not authorized to use this bot. id is {message.from_user.id}"
#                               f"username is {message.from_user.username}")


# 生成主菜单按钮布局
def generate_main_menu_markup():
    markup = types.InlineKeyboardMarkup()
    for config in EIPConfig:
        button = types.InlineKeyboardButton(config["name"], callback_data=f"server_{config['name']}")
        markup.add(button)
    exit_button = types.InlineKeyboardButton('退出菜单', callback_data='exit_menu')
    markup.add(exit_button)
    return markup


# 生成二级菜单按钮布局
def generate_secondary_menu_markup(server_name):
    markup = types.InlineKeyboardMarkup()
    # for i in range(1, 14):
    #     button = types.InlineKeyboardButton(f'button{server_name}-{i}',
    #                                         callback_data=f'button{server_name}_{i}_{server_name}')
    #     markup.add(button)

    button_dicts = [
        {"text":"更换IP",  "callback_data":f'button{server_name}_1_{server_name}'},
        {"text":"检测当前IP是否被墙", "callback_data":f'button{server_name}_2_{server_name}'},
        {"text":"开启每日换IP", "callback_data":f'button{server_name}_3_{server_name}'},
        {"text":"关闭每日换IP","callback_data":f'button{server_name}_4_{server_name}'},
        {"text":"每日换IP状态", "callback_data":f'button{server_name}_5_{server_name}'},
        {"text":"开启FGW自动换IP", "callback_data":f'button{server_name}_6_{server_name}'},
        {"text":"关闭FGW自动换IP", "callback_data":f'button{server_name}_7_{server_name}'},
        {"text":"FGW自动换IP状态",  "callback_data":f'button{server_name}_8_{server_name}'},
        {"text":"获取当前ip", "callback_data":f'button{server_name}_9_{server_name}'},
        {"text":"切换到BGP",  "callback_data":f'button{server_name}_10_{server_name}'},
        {"text":"切换到BGP_PRO", "callback_data":f'button{server_name}_11_{server_name}'},
        {"text":"查看线路类型",  "callback_data":f'button{server_name}_12_{server_name}'},
        {"text":"关闭屏蔽所有流量入",  "callback_data":f'button{server_name}_13_{server_name}'},
        {"text": "开启CDT检测", "callback_data": f'button{server_name}_14_{server_name}'},
        {"text": "关闭CDT检测", "callback_data": f'button{server_name}_15_{server_name}'},
        {"text": "CDT检测状态", "callback_data": f'button{server_name}_16_{server_name}'},
        {"text": "屏蔽所有流量入", "callback_data": f'button{server_name}_17_{server_name}'},

    ]
    # button = types.InlineKeyboardButton(button_dicts)
    # markup.add(button)

    for button_info in button_dicts:
        button = types.InlineKeyboardButton(
            text=button_info["text"],
            callback_data=button_info["callback_data"]
        )
        markup.add(button)

    back_button = types.InlineKeyboardButton('返回上级菜单', callback_data='back_to_menu')
    exit_button = types.InlineKeyboardButton('退出菜单', callback_data='exit_menu')
    markup.add(back_button, exit_button)
    return markup


@bot.message_handler(commands=['menu'])
def menu_command(message):
    if is_authorized(message.from_user):
        markup = generate_main_menu_markup()
        bot.send_message(message.chat.id, '选择要操作的服务器', reply_markup=markup)
    else:
        bot.reply_to(message, f"You are not authorized to use this bot. id is {message.from_user.id}"
                              f"username is {message.from_user.username}")





# 处理按钮点击事件
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        if call.data.startswith('server_'):
            server_name = call.data.split('_')[1]
            for config in EIPConfig:
                if config["name"] == server_name:
                    # details = "\n".join([f"{k}: {v}" for k, v in config.items()])
                    cdt = cdts[EIPConfigFindID[server_name]]
                    eip=eips[EIPConfigFindID[server_name]]

                    used=float(cdt.get_cdt_traffic())
                    total=float(config['cdtMax'])
                    # 计算进度百分比
                    progress_percentage = (used / total) * 100
                    # 手动绘制进度条
                    bar_length = 20
                    filled_length = int(bar_length * (used / total))
                    progress_bar = "■" * filled_length + "□" * (bar_length - filled_length)
                    details=""
                    details+=f"{config['name']}   ({eip.get_ip()}) "
                    details+=f"\n{progress_bar} {progress_percentage:.2f}%"
                    details+=f"\n已使用流量: {used:.2f}GB / {total:.2f}GB"
                    details+=f"\n实例IP类型 : {  'BGP(多线)' if config['Linetype']=='BGP' else 'BGP(多线)_精品'}"
                    details+=f"\n实例地区 {config['region_id']}"
                    details+=f"\n是否屏蔽所有流量入:  {  '已屏蔽' if eip.isdisableTraffic() else '未屏蔽'}"


                    markup = generate_secondary_menu_markup(server_name)
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text=details, reply_markup=markup)
                    break
        elif call.data.startswith('button'):
            parts = call.data.split('_')
            button_number = parts[1]
            server_name = parts[2]
            handle_button_operation(button_number, server_name, call)
        elif call.data == 'back_to_menu':
            logger.info("chick back_to_menu")
            markup = generate_main_menu_markup()
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='选择要操作的服务器', reply_markup=markup)
        elif call.data == 'exit_menu':
            logger.info("chick exit_menu")
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_message(call.message.chat.id, 'exit success')

    except Exception as e:
        print(f"处理回调时出错: {e}")


# 定义处理 button 操作的函数
def handle_button_operation(button_number, server_name, call):
    try:
        # operation = f"对 {server_name} 进行 {button_number.split('button')[server_name][-1].split('-')[0]} 操作"
        # bot.send_message(call.message.chat.id, operation)
        # bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        # bot.send_message(call.message.chat.id, 'exit success')

        # for config in EIPConfig:
        #     if config["name"] == server_name:
        #         eip=CreateEIP(config)
        eip=eips[EIPConfigFindID[server_name]]

        if button_number == "1":
            logger.info("chick 更换IP")

            msg = eip.changeEcsIP()
            bot.send_message(call.message.chat.id, msg)


        elif button_number == "2":
            logger.info("chick 检测当前IP是否被墙")
            msg = eip.check_gfw_block()
            bot.send_message(call.message.chat.id, msg)


        elif button_number== "3":
            logger.info("chick 开启每日换IP")
            eip.start_timer("changeip")
            msg = "开启每日换IP成功 crontab is {}".format(eip.changeIPCrons)
            bot.send_message(call.message.chat.id, msg)


        elif button_number == "4":
            logger.info("chick 关闭每日换IP")
            eip.stop_timer("changeip")
            msg = "关闭每日换IP成功"
            bot.send_message(call.message.chat.id, msg)



        elif button_number == "5":
            logger.info("chick 每日换IP状态")
            if eip.is_timer_running("changeip"):
                msg = "每日换IP已开启 crontab is {}".format(eip.changeIPCrons)
            else:
                msg = "每日换IP已关闭"
            bot.send_message(call.message.chat.id, msg)




        elif button_number == "6":
            logger.info("chick 开启GFW自动换IP")

            eip.start_timer("checkGfw")
            msg = "开启被墙自动换IP成功"
            bot.send_message(call.message.chat.id, msg)




        elif button_number == "7":
            logger.info("chick 关闭FGW自动换IP")

            eip.stop_timer("checkGfw")
            msg = "关闭被墙自动换IP成功"
            bot.send_message(call.message.chat.id, msg)



        elif button_number == "8":
            logger.info("chick GFW自动换IP状态")
            if eip.is_timer_running("checkGfw"):
                msg = "被墙自动换IP已开启 crontab is {}".format(eip.checkGfwCron)
            else:
                msg = "被墙自动换IP已关闭"
            bot.send_message(call.message.chat.id, msg)


        elif button_number == "9":
            logger.info("chick 获取当前ip")
            msg = "当前IP是 {}".format(eip.get_ip())
            bot.send_message(call.message.chat.id, msg)


        elif button_number == "10":
            logger.info("check 切换到BGP")
            eip.changetoBGP()
            msg = "change BGP success!"
            bot.send_message(call.message.chat.id, msg)

        elif button_number == "11":
            logger.info("check 切换到BGP_PRO")
            eip.changetoBGPPro()
            msg = "change BGP_PRO success!"
            bot.send_message(call.message.chat.id, msg)

        elif button_number == "12":
            logger.info("check 查看线路类型")
            msg = eip.showBgpOrPro()
            bot.send_message(call.message.chat.id, msg)

        elif button_number == "13":
            logger.info("chick 关闭屏蔽所有流量入")

            eip.enableTraffic()
            msg = "enableTraffic success!"
            bot.send_message(call.message.chat.id, msg)

        elif button_number == "14":
            logger.info("chick 开启CDT检测")

            eip.start_timer("checkCdt")
            msg = "开启CDT检测成功"
            bot.send_message(call.message.chat.id, msg)
        elif button_number == "15":
            logger.info("chick 关闭CDT检测")

            eip.stop_timer("checkCdt")
            msg= "关闭CDT检测成功"
            bot.send_message(call.message.chat.id, msg)
        elif button_number == "16":

            logger.info("chick CDT检测状态")
            if eip.is_timer_running("checkCdt"):
                msg = "CDT检测已开启 crontab is {}".format(eip.checkGfwCron)
            else:
                msg = "CDT检测已关闭"
            bot.send_message(call.message.chat.id, msg)
        elif button_number == "17":
            logger.info("chick 屏蔽所有流量入")
            eip.disableTraffic()
            msg= "屏蔽所有流量入"
            bot.send_message(call.message.chat.id, msg)


        bot.delete_message(call.message.chat.id, call.message.message_id)

    except Exception as e:
        print(f"处理操作时出错: {e}")














def is_authorized(user_identifier):
    # 检查用户 ID 或用户名是否在授权用户列表中

    if str(user_identifier.id) in authorized_users:
        return True
    elif user_identifier.username in authorized_users:
        return True
    return False


if __name__ == '__main__':
    bot.infinity_polling()
