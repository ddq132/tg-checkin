"""
自动签到脚本。

从环境变量读取配置(GitHub Actions 会自动注入 Secrets 作为环境变量):
    TG_API_ID       - 你的 API ID
    TG_API_HASH     - 你的 API HASH
    TG_SESSION      - login.py 生成的 session 字符串
    TG_BOT_USERNAME - 积分机器人的用户名,例如 "some_points_bot"(不带 @)

    以下是可选的通知配置,不填就只打印日志,不发通知:
    TG_NOTIFY_TARGET - 签到结果要转发到哪里,填一个能收到消息的
                        用户名/群名/频道名,比如 "me" 表示发给"收藏夹"自己
"""

import asyncio
import os
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession


async def main():
    api_id = int(os.environ["TG_API_ID"])
    api_hash = os.environ["TG_API_HASH"]
    session = os.environ["TG_SESSION"]
    bot_username = os.environ["TG_BOT_USERNAME"]
    notify_target = os.environ.get("TG_NOTIFY_TARGET")  # 可选

    async with TelegramClient(StringSession(session), api_id, api_hash) as client:
        # 发送签到指令
        await client.send_message(bot_username, "/checkin")

        # 等待机器人回复(最多等 15 秒,轮询检查最新消息)
        reply_text = None
        for _ in range(15):
            await asyncio.sleep(1)
            messages = await client.get_messages(bot_username, limit=1)
            if messages and messages[0].out is False:
                reply_text = messages[0].message
                break

        if reply_text:
            print(f"[签到结果] {reply_text}")
        else:
            reply_text = "(未收到机器人回复,可能签到超时或机器人无响应)"
            print(f"[警告] {reply_text}")

        # 可选:把结果转发通知给自己
        if notify_target:
            await client.send_message(
                notify_target,
                f"📋 签到结果 ({bot_username}):\n{reply_text}",
            )

        # 如果没收到回复,以非零状态码退出,方便 GitHub Actions 标红提醒你
        if reply_text.startswith("(未收到"):
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
