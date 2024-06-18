# stop
import signal
import sys


def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

from loguru import logger
import json

# loads config
with open("config.json", 'r') as file:
    config_json = json.loads(file.read())

authorized_users = config_json["authorized_users"]
logName = config_json["name"] + '.log'
logger.remove(handler_id=None)  # 清除之前的设置
logger.add(logName, rotation="15MB", encoding="utf-8", enqueue=True, retention="1 days")

from telebot.util import quick_markup
import telebot
from EcsBase import CreateEIP

eip = CreateEIP()
token = eip.API
bot = telebot.TeleBot(token)

bot.message_handler(commands=['help'])


def send_welcome(message):
    bot.reply_to(message, "Hello! Send /menu to see the menu.")

    if is_authorized(message.from_user):
        bot.reply_to(message, "Hello! Send /menu to see the menu.")
    else:
        bot.reply_to(message, "You are not authorized to use this bot.")


@bot.message_handler(commands=['menu'])
def menu_command(message):
    if is_authorized(message.from_user):
        send_menu(message)
    else:
        bot.reply_to(message, f"You are not authorized to use this bot. id is {message.from_user.id}"
                              f"username is {message.from_user.username}")


def send_menu(message):
    button = {
        "更换IP": {"callback_data": "1"},
        "检测当前IP是否被墙": {"callback_data": "2"},
        "开启每日换IP": {"callback_data": "3"},
        "关闭每日换IP": {"callback_data": "4"},
        "每日换IP状态": {"callback_data": "5"},
        "开启FGW自动换IP": {"callback_data": "6"},
        "关闭FGW自动换IP": {"callback_data": "7"},
        "FGW自动换IP状态": {"callback_data": "8"},
        "获取当前ip": {"callback_data": "9"},
        "切换到BGP": {"callback_data": "10"},
        "切换到BGP_PRO": {"callback_data": "11"},
        "查看线路类型": {"callback_data": "12"},
        "退出菜单": {"callback_data": "13"},
        # "查看流量": {"callback_data": "15"},
    }
    menu_message = bot.send_message(message.chat.id, "选择你要进行的操作! ",
                                    reply_markup=quick_markup(button, row_width=2))


@bot.callback_query_handler(func=lambda call: True)
def refresh(call):
    if call.data == "1":
        logger.info("chick 更换IP")

        msg = eip.changeEcsIP()
        bot.send_message(call.message.chat.id, msg)

    elif call.data == "2":
        logger.info("chick 检测当前IP是否被墙")
        msg = eip.check_gfw_block()
        bot.send_message(call.message.chat.id, msg)

    elif call.data == "3":
        logger.info("chick 开启每日换IP")
        eip.start_timer("changeip")
        msg = "开启每日换IP成功 crontab is {}".format(eip.changeIPCrons)
        bot.send_message(call.message.chat.id, msg)

    elif call.data == "4":
        logger.info("chick 关闭每日换IP")
        eip.stop_timer("changeip")
        msg = "关闭每日换IP成功"
        bot.send_message(call.message.chat.id, msg)


    elif call.data == "5":
        logger.info("chick 每日换IP状态")
        if eip.is_timer_running("changeip"):
            msg = "每日换IP已开启 crontab is {}".format(eip.changeIPCrons)
        else:
            msg = "每日换IP已关闭"
        bot.send_message(call.message.chat.id, msg)



    elif call.data == "6":
        logger.info("chick 开启GFW自动换IP")

        eip.start_timer("checkGfw")
        msg = "开启被墙自动换IP成功"
        bot.send_message(call.message.chat.id, msg)



    elif call.data == "7":
        logger.info("chick 关闭FGW自动换IP")

        eip.stop_timer("checkGfw")
        msg = "关闭被墙自动换IP成功"
        bot.send_message(call.message.chat.id, msg)


    elif call.data == "8":
        logger.info("chick GFW自动换IP状态")
        if eip.is_timer_running("checkGfw"):
            msg = "被墙自动换IP已开启 crontab is {}".format(eip.checkGfwCron)
        else:
            msg = "被墙自动换IP已关闭"
        bot.send_message(call.message.chat.id, msg)

    elif call.data == "9":
        logger.info("chick 获取当前ip")
        msg = "当前IP是 {}".format(eip.get_ip())
        bot.send_message(call.message.chat.id, msg)

    elif call.data == "10":
        eip.changetoBGP()
        msg = "change BGP success!"
        bot.send_message(call.message.chat.id, msg)

    elif call.data == "11":
        eip.changetoBGPPro()
        msg = "change BGP_PRO success!"
        bot.send_message(call.message.chat.id, msg)

    elif call.data == "12":
        msg = eip.showBgpOrPro()
        bot.send_message(call.message.chat.id, msg)


    elif call.data == "13":
        msg = "exit success!"
        bot.send_message(call.message.chat.id, msg)

    bot.delete_message(call.message.chat.id, call.message.message_id)


def is_authorized(user_identifier):
    # 检查用户 ID 或用户名是否在授权用户列表中

    if str(user_identifier.id) in authorized_users:
        return True
    elif user_identifier.username in authorized_users:
        return True
    return False


if __name__ == '__main__':
    bot.infinity_polling()
