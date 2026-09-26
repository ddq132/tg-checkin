"""
自动签到脚本。
 
从环境变量读取配置:
    TG_API_ID       - 你的 API ID
    TG_API_HASH     - 你的 API HASH
    TG_SESSION      - login.py 生成的 session 字符串
    TG_BOT_USERNAME - 积分机器人的用户名,例如 "some_points_bot"(不带 @)
 
    以下是可选的通知配置,不填就只打印日志,不发通知:
    TG_NOTIFY_TARGET - 签到结果要转发到哪里,填一个能收到消息的
                        用户名/群名/频道名,比如 "me" 表示发给"收藏夹"自己
 
    以下是可选的代理配置,如果 GitHub Actions 直连 Telegram 超时(数据中心 IP 常被拦截),
    需要配置一个代理服务:
    TG_PROXY_TYPE     - 代理类型,填 "socks5" 或 "http"
    TG_PROXY_HOST     - 代理服务器地址
    TG_PROXY_PORT     - 代理服务器端口
    TG_PROXY_USERNAME - 可选,代理需要账号密码认证时填
    TG_PROXY_PASSWORD - 可选,代理需要账号密码认证时填
"""
 
import asyncio
import os
import sys
 
from telethon import TelegramClient
from telethon.sessions import StringSession
 
 
def build_proxy():
    proxy_type = os.environ.get("TG_PROXY_TYPE")
    proxy_host = os.environ.get("TG_PROXY_HOST")
    proxy_port = os.environ.get("TG_PROXY_PORT")
    proxy_username = os.environ.get("TG_PROXY_USERNAME")
    proxy_password = os.environ.get("TG_PROXY_PASSWORD")
 
    if not (proxy_type and proxy_host and proxy_port):
        return None
 
    import socks
 
    type_map = {
        "socks5": socks.SOCKS5,
        "socks4": socks.SOCKS4,
        "http": socks.HTTP,
    }
    ptype = type_map.get(proxy_type.lower())
    if ptype is None:
        print(f"[错误] 不支持的代理类型: {proxy_type}(只支持 socks5 / socks4 / http)", flush=True)
        sys.exit(1)
 
    if proxy_username and proxy_password:
        return (ptype, proxy_host, int(proxy_port), True, proxy_username, proxy_password)
    return (ptype, proxy_host, int(proxy_port))
 
 
async def main():
    api_id = int(os.environ["TG_API_ID"])
    api_hash = os.environ["TG_API_HASH"]
    session = os.environ["TG_SESSION"]
    bot_username = os.environ["TG_BOT_USERNAME"]
    notify_target = os.environ.get("TG_NOTIFY_TARGET")  # 可选
    proxy = build_proxy()  # 可选
 
    print(f"正在连接 Telegram...{'(使用代理)' if proxy else ''}", flush=True)
 
    # connection_retries: 连接失败时最多重试几次
    # timeout: 单次连接尝试最多等待多少秒,避免无限期卡住
    client = TelegramClient(
        StringSession(session),
        api_id,
        api_hash,
        connection_retries=3,
        timeout=20,
        proxy=proxy,
    )
 
    try:
        await asyncio.wait_for(client.connect(), timeout=30)
    except asyncio.TimeoutError:
        print("[错误] 连接 Telegram 超时(30秒)。如果你平时用 Telegram 需要开代理,请检查 TG_PROXY_* 是否配置正确、代理软件是否正在运行。", flush=True)
        sys.exit(1)
 
    if not await client.is_user_authorized():
        print("[错误] session 无效或已过期,需要重新运行 login.py 生成新的 session。", flush=True)
        sys.exit(1)
 
    print("连接成功,发送签到指令...", flush=True)
 
    async with client:
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
            print(f"[签到结果] {reply_text}", flush=True)
        else:
            reply_text = "(未收到机器人回复,可能签到超时或机器人无响应)"
            print(f"[警告] {reply_text}", flush=True)
 
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
 
