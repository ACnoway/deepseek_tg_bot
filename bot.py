import re, os, logging, json
import sqlite3
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, MessageHandler, CallbackContext, filters

# 设置日志配置
log_file = 'bot_logs.log'
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,  # 设置最低日志级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 日志格式
)
# 禁用 httpx 的 INFO 级别日志，设置为 WARNING 级别
logging.getLogger('httpx').setLevel(logging.WARNING)

# 创建一个logger实例
logger = logging.getLogger()

# 用你从 BotFather 获取的 Token 替换 'YOUR_TOKEN'
TOKEN = 'YOUR_TOKEN'

# 初始化 OpenAI 客户端
client = OpenAI(
    api_key="APIKEY",  # 替换成你的 API 密钥
    base_url="https://qianfan.baidubce.com/v2")

# 开始提示语
welcome_message = "你好喵，这里是聪明猫猫，后端为Deepseek\-V3/R1模型，记忆条数15条，发送`/reset`可以清除记忆。在群里找我玩的话记得在消息开头加`聪明猫猫`，否则我是不会理你的！在聪明猫猫后面（私聊的话在消息最开始）加`r1`的话可以让我变得更聪明喵\~"
# 唤醒词
wakeup_word = "聪明猫猫"

# 白名单
try:
    with open('whitelist.json', 'r') as f:
        whitelist = json.load(f)
except:
    open('whitelist.json', 'w')
print(whitelist)


# 转义 Markdown 中的特殊字符
def escape_markdown_v2(text: str) -> str:
    if not text:
        return ""
    # 使用正则表达式转义所有 MarkdownV2 特殊字符
    return re.sub(r'([\\_*[\]()>#+\-.=|!~`])', r'\\\1', text)


# 检查数据库是否存在，如果不存在则创建
def create_db():
    if not os.path.exists('chat_memory.db'):
        logger.info("数据库不存在，正在创建数据库...")
        conn = get_db_connection()
        cursor = conn.cursor()
        # 创建表格
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("数据库和表格已创建")
    else:
        logger.info("数据库已存在")


# 创建 SQLite 数据库连接
def get_db_connection():
    conn = sqlite3.connect('chat_memory.db')
    conn.row_factory = sqlite3.Row  # 以字典形式访问行
    return conn


# 保存用户消息到数据库
def save_to_db(user_id, role, content):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        INSERT INTO user_conversations (user_id, role, content)
        VALUES (?, ?, ?)
    ''', (user_id, role, content))

    conn.commit()
    conn.close()


# 获取用户最近的 15 条对话记录
def get_user_conversations(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT role, content FROM user_conversations
        WHERE user_id = ?
        ORDER BY timestamp DESC LIMIT 15
    ''', (user_id, ))

    rows = cursor.fetchall()
    conn.close()
    return [{
        'role': row['role'],
        'content': row['content']
    } for row in rows[::-1]]  # 返回从最早的消息开始


# 定义处理群聊消息的函数
async def check_message(update: Update, context: CallbackContext):
    # 获取用户消息的文本
    text = update.message.text
    user_id = update.message.from_user.id
    chat_type = update.message.chat.type

    logger.info(f"Received message from {user_id}: {text}")

    # # 白名单判断 如果需要开启的话取消下方代码注释即可
    # if str(user_id) not in whitelist:
    #     await update.message.reply_text("你不在白名单里喵~请联系 @noloudelou 添加白名单", quote=True)
    #     return

    # 指令处理
    if chat_type == "group":
        if text == "/help@BOT昵称" or text == "/start@BOT昵称":
            await update.message.reply_text(welcome_message,
                                            parse_mode='MarkdownV2',
                                            quote=True)
            return

        if text == "/reset@BOT昵称":
            # 清除用户记忆
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_conversations WHERE user_id = ?',
                           (user_id, ))
            conn.commit()
            conn.close()
            await update.message.reply_text("记忆已清除！", quote=True)
            return
    else:
        if text == "/help" or text == "/start":
            await update.message.reply_text(welcome_message,
                                            parse_mode='MarkdownV2',
                                            quote=True)
            return

        if text == "/reset":
            # 清除用户记忆
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_conversations WHERE user_id = ?',
                           (user_id, ))
            conn.commit()
            conn.close()
            await update.message.reply_text("记忆已清除！", quote=True)
            return

    # 判断消息是否以唤醒词开头 (你可以修改这里的词语)
    if re.match(r'^' + wakeup_word, text,
                re.IGNORECASE) or chat_type == "private":
        if chat_type == "group":
            pattern = r"^" + wakeup_word + "\s*"
            text = re.sub(pattern, '', text, 1)

        if not text:
            text = "猫猫"

        model_name = "deepseek-v3"
        if re.match(r'^r1', text, re.IGNORECASE):
            logger.info("r1 mode")
            pattern = r"^r1\s*"
            text = re.sub(pattern, '', text, 1)
            model_name = "deepseek-r1"

        reply_message = await update.message.reply_text("猫猫思考中...", quote=True)

        # 获取或初始化用户的记忆
        user_conversations = get_user_conversations(user_id)

        # 保存用户消息到数据库
        save_to_db(user_id, 'user', text)

        # 将用户记忆传递给 OpenAI
        # 将用户消息作为 content 发送给 OpenAI API
        try:
            logger.info("entered ai")
            completion = client.chat.completions.create(
                model=model_name,
                messages=[{
                    'role': 'system',
                    'content': '你是一只聪明可爱的猫娘，是我的助理，回复请稍短一点'
                }] + user_conversations + [{
                    'role': 'user',
                    'content': text
                }])
            logger.info("got reply")
            # 获取 API 回复的消息
            reply = completion.choices[0].message
            logger.info(reply)
            ai_reply = reply.content

            # 确保 ai_reply 是字符串类型
            if not isinstance(ai_reply, str):
                raise ValueError("AI 回复的内容不是有效的字符串类型")

            # 提取 <think> 和 </think> 之间的内容
            think_content = re.search(r'<think>(.*?)</think>', ai_reply,
                                      re.DOTALL)

            if think_content:
                # 如果找到了思考内容，用 quote 格式包裹
                think_content = think_content.group(1)
                # 去掉 <think> 和 </think> 的标签，保留其余内容
                ai_reply = ai_reply.replace(think_content, '').replace(
                    '<think>', '').replace('</think>', '')
                think_content = escape_markdown_v2(think_content)

                think_reply = f"> 🐾 猫猫动脑:\n"
                for line in think_content.splitlines():
                    think_reply += f"> {line}\n"
            else:
                think_reply = ""

            # 保存 AI 回复到数据库
            save_to_db(user_id, 'assistant', ai_reply)

            ai_reply = escape_markdown_v2(ai_reply)

            # 撤回收到的回复
            await reply_message.delete()

            final_reply = f"{think_reply}🐱猫猫动嘴：\n{ai_reply.strip()}"
            logger.info(final_reply)

            # 将 API 回复发送回 Telegram 群聊
            await update.message.reply_text(final_reply,
                                            parse_mode='MarkdownV2',
                                            quote=True)

        except Exception as e:
            logger.error(f"发生错误: {e}")
            await update.message.reply_text(f"发生错误: {e}", quote=True)


def main():
    # 在程序启动时检查并创建数据库
    create_db()

    # 创建 Application 对象
    application = Application.builder().token(TOKEN).build()

    # 注册监听群聊消息的处理函数
    application.add_handler(MessageHandler(filters.TEXT, check_message))

    # 启动 Bot，开始轮询更新
    application.run_polling()


if __name__ == '__main__':
    main()
