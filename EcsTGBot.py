
import json

from telegram import  Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

from loguru import logger
import json
from crontab import CronTab

from EcsChangeIP import CreateEIP
from EcsCheckGfw import  CheckGFW

eip = CreateEIP()
checkGfw = CheckGFW()


token = checkGfw.API
# 创建当前用户的crontab，当然也可以创建其他用户的，但得有足够权限
my_cron = CronTab(user=True)

# 创建任务
cmd1="/root/EcsAutoChangeIPShare/EcsChangeIP.sh >/dev/null 2>&1"
cmd2="/root/EcsAutoChangeIPShare/EcsCheckGfw.sh >/dev/null 2>&1"

changeip_job = my_cron.new(command=cmd1)
checkgfw_job = my_cron.new(command=cmd2)

changeip_job.setall(eip.changeIPCrons)
checkgfw_job.setall(eip.checkGfwCron)
changeip_job.enable(False)  # 默认关闭
checkgfw_job.enable()
my_cron.write()


# def main() -> None:
#     """Run the bot."""
#     # Create the Application and pass it your bot's token.
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with three inline buttons attached."""
    keyboard = [
        [
            InlineKeyboardButton("更换IP", callback_data="1"),
            InlineKeyboardButton("检测当前IP是否被墙", callback_data="2"),

        ],
        [
            InlineKeyboardButton("开启每日换IP", callback_data="3"),
            InlineKeyboardButton("关闭每日换IP", callback_data="4"),

        ],
        [
            InlineKeyboardButton("每日换IP状态", callback_data="5"),
            InlineKeyboardButton("开启FGW自动换IP", callback_data="6"),

        ],

        [
            InlineKeyboardButton("关闭FGW自动换IP", callback_data="7"),
            InlineKeyboardButton("FGW自动换IP状态", callback_data="8"),

        ],
        [
            InlineKeyboardButton("获取当前ip", callback_data="9"),
            InlineKeyboardButton("切换到BGP", callback_data="10")
        ],
        [
            InlineKeyboardButton("切换到BGP_PRO", callback_data="11"),
            InlineKeyboardButton("查看线路类型", callback_data="12"),
        ],
        [
            InlineKeyboardButton("xxxxxxx", callback_data="13"),
            InlineKeyboardButton("退出菜单", callback_data="14")
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    menumsg = "选择你要进行的操作!"
    await update.message.reply_text(menumsg, reply_markup=reply_markup)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    # print("query.data       ", query.data)

    if query.data == "1":
        eip.changeEcsIP()
        msg = f"change ip success! and ip is {eip.get_ip()}"
    elif query.data == "2":
        checkGfw.check_gfw_block_tg()
    elif query.data == "3":
        changeip_job.enable()
        my_cron.write()
        msg = "开启每日换IP成功 crontab is {}".format(eip.changeIPCrons)
    elif query.data == "4":
        changeip_job.enable(False)
        my_cron.write()
        msg = "关闭每日换IP成功"

    elif query.data == "5":
        if not changeip_job.is_enabled():
            msg = "每日换IP已关闭"
        else:
            msg = "每日换IP已开启 crontab is {}".format(eip.changeIPCrons)


    elif query.data == "6":
        checkgfw_job.enable()
        my_cron.write()
        msg = "开启FGW自动换IP成功"


    elif query.data == "7":

        checkgfw_job.enable(False)
        my_cron.write()
        msg = "关闭FGW自动换IP成功"

    elif query.data == "8":
        if not checkgfw_job.is_enabled():
            msg = "FGW自动换IP关闭"
        else:
            msg = "FGW自动换IP已开启 crontab is {}".format(eip.checkGfwCron)

    elif query.data == "9":
        msg = "当前IP是 {}".format(eip.get_ip())
    elif query.data == "10":
        eip.changetoBGP()
        msg = "change BGP success!"
    elif query.data == "11":
        eip.changetoBGPPro()
        msg = "change BGP_PRO success!"
    elif query.data == "12":
        msg=eip.showBgpOrPro()
    elif query.data == "13":
        msg="xxxxxxxx"




    elif query.data == "14":
        msg = "exit success!"

    # checkGfw.sendTelegram(msg)

    await query.edit_message_text(text=msg)
    await query.answer()


if __name__ == "__main__":
    application = Application.builder().token(token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CallbackQueryHandler(button))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    my_cron.remove(changeip_job)
    my_cron.remove(checkgfw_job)
    my_cron.write()




