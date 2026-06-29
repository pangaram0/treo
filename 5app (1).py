import discord
from discord.ext import commands, tasks
from discord import Interaction
from discord import app_commands

async def safe_send(interaction: discord.Interaction, message: str, ephemeral=False):
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(message, ephemeral=ephemeral)
        else:
            await interaction.followup.send(message, ephemeral=ephemeral)
    except discord.NotFound:
        print("[WARN] Interaction expired")

from discord import app_commands
import threading
import requests
import re
import time
import json
import os
import gc
import random
import base64
import multiprocessing
from instagrapi import Client
import itertools, sys, time, aiohttp, asyncio
from datetime import datetime
from colorama import Fore
from enum import Enum
from Crypto.Cipher import AES
from textwrap import shorten
from datetime import datetime, timedelta
import smtplib, ssl, time, threading, os
from email.mime.text import MIMEText

TOKEN = input("   Token bot: ").strip()
ADMIN_IDS = input("   ID Admin: ").split(",")
ADMIN_IDS = [aid.strip() for aid in ADMIN_IDS]

INTENTS = discord.Intents.default()
INTENTS.members = True

bot = commands.Bot(command_prefix="/", intents=INTENTS)
tree = bot.tree

DATA_FILE = "users.json"

user_tabs = {}
TAB_LOCK = threading.Lock()
user_image_tabs = {}
IMAGE_TAB_LOCK = threading.Lock()
user_nhaymess_tabs = {}
NHAY_LOCK = threading.Lock()
user_discord_tabs = {}
DIS_LOCK = asyncio.Lock()
user_nhaydis_tabs = {}  
NHAYDIS_LOCK = asyncio.Lock()
user_treotele_tabs = {}   
TREOTELE_LOCK = threading.Lock()
SPAM_TASKS = {}  
IG_LOCK = threading.Lock()
user_treogmail_tabs = {}
TREOGMAIL_LOCK = threading.Lock()

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_admin(interaction: discord.Interaction):
    return str(interaction.user.id) in ADMIN_IDS

def is_authorized(interaction: discord.Interaction):
    users = load_users()
    uid = str(interaction.user.id)
    if uid in users:
        exp = users[uid]
        if exp is None:
            return True
        elif datetime.fromisoformat(exp) > datetime.now():
            return True
        else:            
            _remove_user_and_kill_tabs(uid)
    return False

def _add_user(uid: str, days: int = None):
    users = load_users()
    if days:
        expire_time = (datetime.now() + timedelta(days=days)).isoformat()
        users[uid] = expire_time
    else:
        users[uid] = None
    save_users(users)

def _remove_user_and_kill_tabs(uid: str):
    users = load_users()
    if uid in users:
        del users[uid]
        save_users(users)
    with TAB_LOCK:
        if uid in user_tabs:
            for tab in user_tabs[uid]:
                tab["stop_event"].set()
            del user_tabs[uid]

def _get_user_list():
    users = load_users()
    result = []
    for uid, exp in users.items():
        if exp:
            remaining = datetime.fromisoformat(exp) - datetime.now()
            if remaining.total_seconds() <= 0:
                continue  
            days = remaining.days
            hours, rem = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(rem, 60)
            time_str = f"{days} ngày, {hours} giờ, {minutes} phút"
            result.append((uid, time_str))
        else:
            result.append((uid, "vĩnh viễn"))
    return result
            
async def _discord_spam_worker(session, token, channels, message, delay, start_time, discord_user_id):
    while True:
        elapsed = int((datetime.now() - start_time).total_seconds())
        ts = format_time(elapsed)
        for channel_id in channels:
            ok, err = await send_message(session, token, channel_id, message)
            if ok:
                print(Fore.LIGHTGREEN_EX + f"[DIS][{discord_user_id}]  {channel_id} | Token:{token[:20]}... | Delay:{delay}s | Up:{ts}")
            else:
                print(Fore.RED + f"[DIS][{discord_user_id}]  {channel_id}: {err}")
        await asyncio.sleep(delay)
 
def telegram_send_loop(token, chat_ids, caption, photo, delay, stop_event, discord_user_id):
    while not stop_event.is_set():
        for chat_id in chat_ids:
            if stop_event.is_set():
                break
            try:
                if photo:
                    if photo.startswith("http"):
                        url = f"https://api.telegram.org/bot{token}/sendPhoto"
                        data = {"chat_id": chat_id, "caption": caption, "photo": photo}
                        resp = requests.post(url, data=data, timeout=10)
                    else:
                        url = f"https://api.telegram.org/bot{token}/sendPhoto"
                        with open(photo, "rb") as f:
                            files = {"photo": f}
                            data = {"chat_id": chat_id, "caption": caption}
                            resp = requests.post(url, data=data, files=files, timeout=10)
                else:
                    url = f"https://api.telegram.org/bot{token}/sendMessage"
                    data = {"chat_id": chat_id, "text": caption}
                    resp = requests.post(url, data=data, timeout=10)

                if resp.status_code == 200:
                    print(f"[TELE][{discord_user_id}] {token[:10]}... → {chat_id}")
                elif resp.status_code == 429:
                    retry = resp.json().get("parameters", {}).get("retry_after", 10)
                    print(f"[TELE][{discord_user_id}] Rate limit {retry}s")
                    time.sleep(retry)
                else:
                    print(f"[TELE][{discord_user_id}] Err {resp.status_code}: {resp.text[:100]}")
            except Exception as e:
                print(f"[TELE][{discord_user_id}] Conn Err: {e}")
            time.sleep(0.2)
        time.sleep(delay)           

def _ig_spam_loop(task_id, discord_user_id):
    with IG_LOCK:
        task = next((t for t in SPAM_TASKS[discord_user_id] if t["id"] == task_id), None)
    if not task:
        return

    cl       = task["client"]
    targets  = task["targets"]
    message  = task["message"]
    delay    = task["delay"]
    stop_set = task["stop_targets"]

    while True:
        for target in targets:
            if target in stop_set:
                continue
            try:
                if target.isdigit():
                    cl.direct_send(message, thread_ids=[target])
                else:
                    uid = cl.user_id_from_username(target)
                    cl.direct_send(message, thread_ids=[uid])
                print(f"[IG][{discord_user_id}] Gửi tới {target}")
            except Exception as e:
                print(f"[IG][{discord_user_id}] Lỗi {target}: {e}")
        time.sleep(delay)           

def parse_gmail_accounts(input_str: str):
    accounts = []
    for entry in re.split(r"[,/]", input_str):
        if "|" in entry:
            email, pwd = entry.split("|",1)
            accounts.append({
                "server": "smtp.gmail.com",
                "port": 465,
                "email": email.strip(),
                "password": pwd.strip(),
                "active": True
            })
    return accounts

def send_mail(smtp_info, to_email, content):
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_info["server"], smtp_info["port"], context=context) as server:
        server.login(smtp_info["email"], smtp_info["password"])
        msg = MIMEText(content)
        msg["From"] = smtp_info["email"]
        msg["To"] = to_email
        msg["Subject"] = " "
        server.sendmail(smtp_info["email"], to_email, msg.as_string())

def gmail_spam_loop(tab, discord_user_id):
    smtp_list = tab["smtp_list"]
    to_email  = tab["to_email"]
    content   = tab["content"]
    delay     = tab["delay"]
    stop_evt  = tab["stop_event"]
    idx = 0
    while not stop_evt.is_set():
        active = [acc for acc in smtp_list if acc["active"]]
        if not active:
            for acc in smtp_list: acc["active"] = True
            active = smtp_list
        smtp = active[idx % len(active)]
        try:
            send_mail(smtp, to_email, content)
            print(f"[GMAIL][{discord_user_id}] ✓ {smtp['email']} → {to_email}")
        except smtplib.SMTPAuthenticationError:
            smtp["active"] = False
            print(f"[GMAIL][{discord_user_id}] ✗ Auth failed {smtp['email']}")
        except smtplib.SMTPDataError as e:
            txt = str(e)
            if "Quota" in txt or "limit" in txt:
                smtp["active"] = False
                print(f"[GMAIL][{discord_user_id}] Quota limit {smtp['email']}")
            else:
                print(f"[GMAIL][{discord_user_id}] DataErr {smtp['email']}: {e}")
        except Exception as e:
            print(f"[GMAIL][{discord_user_id}] Err {smtp['email']}: {e}")
        idx += 1
        for _ in range(int(delay)):
            if stop_evt.is_set(): break
            time.sleep(1)
        if stop_evt.is_set(): break
        time.sleep(delay - int(delay))      
                   
def get_uptime(start_time: datetime) -> str:
    elapsed = (datetime.now() - start_time).total_seconds()
    hours, rem = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

@tasks.loop(minutes=60)
async def cleanup_expired_users():
    users = load_users()
    to_remove = []
    for uid, exp in users.items():
        if exp and datetime.fromisoformat(exp) <= datetime.now():
            to_remove.append(uid)
    if to_remove:
        for uid in to_remove:
            _remove_user_and_kill_tabs(uid)


class Kem:
    def __init__(self, cookie):
        self.cookie = cookie
        self.user_id = self.id_user()
        self.fb_dtsg = None
        self.init_params()

    def id_user(self):
        try:
            c_user = re.search(r"c_user=(\d+)", self.cookie).group(1)
            return c_user
        except:
            raise Exception("Cookie không hợp lệ")

    def init_params(self):
        headers = {
            'Cookie': self.cookie,
            'User-Agent': 'Mozilla/5.0',
            'Accept': '*/*',
        }
        try:
            response = requests.get('https://www.facebook.com', headers=headers)
            fb_dtsg_match = re.search(r'"token":"(.*?)"', response.text)
            if not fb_dtsg_match:
                response = requests.get('https://mbasic.facebook.com', headers=headers)
                fb_dtsg_match = re.search(r'name="fb_dtsg" value="(.*?)"', response.text)
                if not fb_dtsg_match:
                    response = requests.get('https://m.facebook.com', headers=headers)
                    fb_dtsg_match = re.search(r'name="fb_dtsg" value="(.*?)"', response.text)
            if fb_dtsg_match:
                self.fb_dtsg = fb_dtsg_match.group(1)
            else:
                raise Exception("Không thể lấy được fb_dtsg")
        except Exception as e:
            raise Exception(f"Lỗi khi khởi tạo tham số: {str(e)}")

    def gui_tn(self, recipient_id, message):
        if not message or not recipient_id:
            raise ValueError("ID Box và Nội Dung không được để trống")
        timestamp = int(time.time() * 1000)
        data = {
            'thread_fbid': recipient_id,
            'action_type': 'ma-type:user-generated-message',
            'body': message,
            'client': 'mercury',
            'author': f'fbid:{self.user_id}',
            'timestamp': timestamp,
            'source': 'source:chat:web',
            'offline_threading_id': str(timestamp),
            'message_id': str(timestamp),
            'ephemeral_ttl_mode': '',
            '__user': self.user_id,
            '__a': '1',
            '__req': '1b',
            '__rev': '1015919737',
            'fb_dtsg': self.fb_dtsg
        }
        headers = {
            'Cookie': self.cookie,
            'User-Agent': 'python-http/0.27.0',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        try:
            response = requests.post('https://www.facebook.com/messaging/send/', data=data, headers=headers)
            if response.status_code != 200:
                return {'success': False, 'error_description': f'Status: {response.status_code}'}
            if 'for (;;);' in response.text:
                clean = response.text.replace('for (;;);', '')
                result = json.loads(clean)
                if 'error' in result:
                    return {'success': False, 'error_description': result.get('errorDescription', 'Unknown error')}
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error_description': str(e)}

def spam_tab_worker(messenger: Kem, box_id: str, message: str, delay: float, stop_event: threading.Event, start_time: datetime, discord_user_id: str):
    success = 0
    fail = 0
    while not stop_event.is_set():
        result = messenger.gui_tn(box_id, message)
        ok = result.get("success", False)
        if ok:
            success += 1
            status = "OK"
        else:
            fail += 1
            status = "FAIL"
            stop_event.set()
        uptime = (datetime.now() - start_time).total_seconds()
        h, rem = divmod(int(uptime), 3600)
        m, s = divmod(rem, 60)
        print(f"[{messenger.user_id}] → {box_id} | {status} | Up: {h:02}:{m:02}:{s:02} | OK: {success} | FAIL: {fail}".ljust(120), end='\r')
        time.sleep(delay)
        gc.collect()
    print(f"\nTab của user {discord_user_id} với cookie {messenger.user_id} đã dừng.")

@tree.command(name="treomess", description="Treo tin nhắn Messenger")
@app_commands.describe(
    idbox="ID Box",
    cookie="Cookie Facebook",
    noidung="Nội dung cần gửi",
    delay="Delay mỗi lần gửi (giây)"
)
async def treomess(interaction: discord.Interaction, idbox: str, cookie: str, noidung: str, delay: float):
    discord_user_id = str(interaction.user.id)
    try:
        messenger = Kem(cookie)
    except Exception as e:
        return await interaction.response.send_message(f"Cookie không hợp lệ hoặc lỗi: {e}", ephemeral=True)

    stop_event = threading.Event()
    start_time = datetime.now()
    th = threading.Thread(
        target=spam_tab_worker,
        args=(messenger, idbox, noidung, delay, stop_event, start_time, discord_user_id),
        daemon=True
    )
    th.start()

    
    with TAB_LOCK:
        if discord_user_id not in user_tabs:
            user_tabs[discord_user_id] = []
        user_tabs[discord_user_id].append({
            "box_id": idbox,
            "delay": delay,
            "start": start_time,
            "stop_event": stop_event
        })

    short_content = shorten(noidung, width=1900, placeholder="...")

    await interaction.response.send_message(
        f"Đã khởi tab spam messenger cho <@{discord_user_id}>:\n"
        f"• ID Box: `{idbox}`\n"
        f"• Delay: `{delay}` giây\n"
        f"• Nội dung: `{short_content}`\n"
        f"• Thời điểm bắt đầu: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`"
    )

@tree.command(name="add", description="Thêm user")
@app_commands.describe(user="Tag hoặc ID user", thoihan="Thời hạn (ví dụ: 7d)")
async def add(interaction: discord.Interaction, user: str, thoihan: str = None):
    if not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này", ephemeral=True)

    user_id = user.replace("<@", "").replace(">", "").replace("!", "")
    days = None
    if thoihan and thoihan.endswith("d"):
        try:
            days = int(thoihan[:-1])
        except:
            return await interaction.response.send_message("Thời hạn không hợp lệ. Phải là số + 'd'.", ephemeral=True)

    _add_user(user_id, days)
    msg = f"Đã thêm <@{user_id}> với quyền sử dụng bot {'vĩnh viễn' if not days else f'{days} ngày'}."
    await interaction.response.send_message(msg)

@tree.command(name="xoa", description="Xoá user")
@app_commands.describe(user="Tag hoặc ID user")
async def xoa(interaction: discord.Interaction, user: str):
    if not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này", ephemeral=True)

    user_id = user.replace("<@", "").replace(">", "").replace("!", "")
    _remove_user_and_kill_tabs(user_id)
    await interaction.response.send_message(f"Đã xóa quyền sử dụng bot và dừng mọi tab của <@{user_id}>.")

@tree.command(name="list", description="Hiển thị danh sách user")
async def list_cmd(interaction: discord.Interaction):
    if not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này", ephemeral=True)

    user_list = _get_user_list()
    if not user_list:
        return await interaction.response.send_message("Danh sách rỗng.")

    msg = "**Danh sách user có quyền sử dụng bot:**\n"
    for uid, time_str in user_list:
        msg += f"- <@{uid}>: `{time_str}`\n"
    await interaction.response.send_message(msg)

@tree.command(name="tabtreomess", description="Quản lý/dừng tab treo messenger")
async def tabtreomess(interaction: discord.Interaction):
    if not is_authorized(interaction) and not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này", ephemeral=True)

    discord_user_id = str(interaction.user.id)
    with TAB_LOCK:
        tabs = user_tabs.get(discord_user_id, [])

    if not tabs:
        return await interaction.response.send_message("Bạn không có tab nào đang hoạt động")

    msg = "**Danh sách tab treo messenger của bạn:**\n"
    for idx, tab in enumerate(tabs, start=1):
        uptime = get_uptime(tab["start"])
        msg += (
            f"{idx}. Box: `{tab['box_id']}` | Delay: `{tab['delay']}` giây | "
            f"Uptime: `{uptime}`\n"
        )
    msg += "\nNhập số tab để dừng tab đó".format(len(tabs))

    await interaction.response.send_message(msg)

    def check(m: discord.Message):
        return (
            m.author.id == interaction.user.id and 
            m.channel.id == interaction.channel.id
        )

    try:
        reply: discord.Message = await bot.wait_for("message", check=check, timeout=30.0)
        content = reply.content.strip()
        if content.isdigit():
            idx = int(content)
            if 1 <= idx <= len(tabs):               
                with TAB_LOCK:
                    chosen = tabs[idx-1]
                    chosen["stop_event"].set()
                    tabs.pop(idx-1)
                    if not tabs:
                        del user_tabs[discord_user_id]
                return await interaction.followup.send(f"Đã dừng tab số {idx}")
        await interaction.followup.send("Không dừng tab nào")
    except asyncio.TimeoutError:
        return await interaction.followup.send("Hết thời gian (30s). Không dừng tab nào")
    
@tree.command(name="nhaymess", description="Spam nhây Facebook bằng cookie")
@app_commands.describe(
    cookies="Cookie (cách nhau dấu phẩy)",
    box_ids="ID Box (cách nhau dấu phẩy)",
    ten_reo="Tên cần réo (tuỳ chọn)",
    delay="Delay mỗi tin (giây)"
)
async def nhaymess(interaction: discord.Interaction, cookies: str, box_ids: str, ten_reo: str = "", delay: float = 2.0):
    await interaction.response.defer(ephemeral=True)
    discord_user_id = str(interaction.user.id)

    cookie_list = [x.strip() for x in cookies.split(",") if x.strip()]
    id_list = [x.strip() for x in box_ids.split(",") if x.strip()]
    messengers = []

    for c in cookie_list:
        try:
            messengers.append(Kem(c))
        except Exception as e:
            print(f"[!] Cookie lỗi: {e}")

    if not messengers:
        return await interaction.followup.send("❌ Tất cả cookie đều lỗi!", ephemeral=True)

    chon_name = ten_reo or ""
    CAU_CHUI = [
f"ccho sua lofi de {chon_name}",
f"sua di {chon_name} em😏🤞",
f"lofi di {chon_name} cu😝",
f"tk ngu lon {chon_name} eyy🤣🤣",
f"nhanh ti em {chon_name}🤪👌",
f"cam a {chon_name} mo coi😏🤞",
f"hang hai len ti {chon_name} de👉🤣",
f"cn tat nguyen {chon_name}😏??",
f"cn 2 lai mat mam {chon_name}🤪👎",
f"anh cho may sua a {chon_name}😏🤞",
f"ah ba meta 2025 ma {chon_name}😋👎",
f"bi anh da na tho cmnr dk {chon_name}🤣",
f"thieu oxi a {chon_name}🤣🤣",
f"anh cko may oxi hoa ne {chon_name}😏👉🤣",
f"may cay cha qua a cn ngu {chon_name}🤪",
f"may phe nhu con me may bi tao hiep ma {chon_name}🤣",
f"dung ngam dang nuot cay tao nha coan {chon_name}👉🤣",
f"con cho {chon_name} cay tao ro👉🌶",
f"oc cho ngoi do nhay voi tao a {chon_name}🤣",
f"me may bi tao cho len dinh r {chon_name}=))",
f"ui cn ngu {chon_name} oc cac=))",
f"cn gai me may khog bt day nay a {chon_name} cn oc cac😝",
f"cn cho {chon_name} may cam a:))?",
f"cam lang that r a cn ngu {chon_name}🤣",
f"ui tk cac dam cha chem chu ak {chon_name}😝🤞",
f"cn cho dot so tao run cam cap me roi ha em {chon_name} =))",
f"ui cai con hoi {chon_name}👉🤣",
f"cn me may chet duoi ao roi kia {chon_name}😆",
f"djt con {chon_name} cu cn lon tham:))",
f"ui con bem {chon_name} nha la nhin phen v:))",
f"con cho cay gan nha sua di {chon_name}😏",
f"con bem {chon_name} co me khog😏🤞",
f"a quen may mo coi tu nho ma {chon_name}🤣",
f"sua chill de {chon_name} oc🤣",
f"hay cam nhan noi dau di em {chon_name}:))))",
f"hinh anh con bem {chon_name} gie rach bi anh cha dap:))))))",
f"ti anh chup dang tbg la may hot nha {chon_name}🤣",
f"a may muon hot cx dau co de cn ngu {chon_name}👉🤣🤣",
f"oi may bi cha suc pham kia {chon_name}-))",
f"tao co noti con boai {chon_name} so tao:)) ti tao cap dang profile 1m theo doi:))",
f" {chon_name} con o moi khong bame bi tao khinh thuong=)))",
f"may con gi khac hon khong con bem du ngu {chon_name}🤣",
f"cam canh cdy ngu bi cha chui khong giam phan khang a {chon_name}:))",
f"bi tao chui ma toi so a {chon_name}🤞",
f"nhin ga {chon_name} muon ia chay🤣",
f"con culi lua thay phan ban bi phan boi a {chon_name}:))",
f"may bi tao chui cho om han dk {chon_name}👉🤣🤣🤞",
f"bi tao chui cho so queo cac dung khong {chon_name}:))))",
f"dung cam han tao nua {chon_name}:))",
f"con dog {chon_name} bi tao chui ghi thu a:))",
f"su dung ngon sat thuong xiu de bem anh di mo {chon_name}=)))",
f"co sat thuong chi mang ko ay {chon_name}😝",
f"con ngheo nha la {chon_name} bi bo si va👉🤣🤣",
f"nao may co biet thu nhu anh vay {chon_name}🤪👌",
f"thang nghich tu {chon_name} sao may giet cha may the:))",
f"khong ngo thang phan nghich {chon_name} lua cha doi me=))",
f"tk ngu {chon_name} bi anh co lap ma-))",
f"phan khang di con cali {chon_name} mat map:))",
f"may con gi khac ngoai sua khong ay {chon_name}👉😏🤞",
f" {chon_name} mo coi=))",
f"bi cha chui phat nao ghi han phat do {chon_name} dk em:))",
f"may toi day de chi bi tao chui thoi ha {chon_name}:))",
f"bo la ac quy fefe ne {chon_name}🤣🤣",
f"nen bo lay cay ak ban nat so may luon😏🤞",
f"keo lu ban an hai may ra lmj dc anh khong vay {chon_name}🤣🤞",
f"ui ui dung thang an hai mang ten {chon_name}:))",
f"dung la con can ba mxh chi biet nhin anh chui cha mang me no ma {chon_name}=))",
f"may co phan khang duoc khong vay:)) {chon_name}",
f"may khong phan khang duoc a {chon_name}=))",
f"may yeu kem den vay a con cali {chon_name}😋👎",
f"con cali {chon_name} mat mam cay ah roi🌶",
f"cu anh lam dk em {chon_name}:))",
f"may co biet gi ngoai sua kiki dau ma {chon_name}👉🤣🤣",
f"may la chi qua qua ban may la chi gau gau ha {chon_name}=))",
f"mua skill di em {chon_name}🤪🤞",
f"anh mua skill duoc ma em {chon_name}😏🤞",
f"anh mua skill vo cai lon me may ay em {chon_name}:))",
f"con culi {chon_name} said : sap win duoc anh roi mung vai a🤣",
f"con cali {chon_name} nghi vay nen mung lam dk:)) {chon_name}",
f"win duoc anh dau de dau em {chon_name}🤪🤞",
f"con cho dien {chon_name} sua dien cuong nao🤣",
f"ui ui con kiki {chon_name} cay anh da man a🌶",
f"tk mo coi {chon_name} sua belike a🤣",
f"chill ti di em {chon_name}🤣🤣",
f"sao sua ko chill gi het vay {chon_name}🤣🤣",
f"bi anh chui cho tat ngon a {chon_name}=))",
f"may sua mau khong anh dap may tat sua bh {chon_name}:))",
f"sua toi khi kiet que nha cn thu {chon_name}🤣🤣",
f"cam may ngung nha cn kiki {chon_name}😝",
f"bo mat nghen ngon a ma nhai hoai v {chon_name}:🤪👌",
f"tao cam 1887 ban ca gia pha nha may chet {chon_name} ay:))",
f"may thay anh ba qua nen sui cmnr a {chon_name}😜",
f"sao may cam vay {chon_name}🤪🤞",
f"may cam = tao win do {chon_name}🤣🤣",
f"may nham win duoc tao khong {chon_name}🤣",
f"ga ma hay sua vay {chon_name}👉🤣",
f"tao dem 123 may chua len tao giet con gia may do {chon_name}🤣",
f"ra tinh hieu de tao treo co con ba may die di {chon_name}:))",
f"may ra tinh hieu sos chay thoat than trc a {chon_name}🤣",
f"dung thang con bat hieu {chon_name}👉🤣🤣",
f"con me may moi de ra thang con bat hieu nhu vay🤣🤞",
f"thang con troi danh di bao gia pha a {chon_name}🤪🤞",
f"bao nhu may gap anh cung tat dien {chon_name}🤣🤞🤞",
f" {chon_name} bi anh chui off mxh la vua roi=))",
f"may lam lai anh khong vayy {chon_name}:))",
f"tao biet la khongg ma {chon_name}👉🤣",
f"do may bai tao all san ro cmnr ma {chon_name}🤣",
f"tao dep trai ma {chon_name}👉🤣",
f"nen may le luoi liem chan tao di {chon_name}🤪🤞",
f"o o ccho {chon_name} loe toe bo may dap vo mom🤣",
f"tk cac {chon_name} oc cho vai cuc👉🤣",
f"tk ngu {chon_name} thay hw la lam than a🤪🤞",
f"du ngu cung onl mxh a {chon_name}😏😏",
f"svat {chon_name} cay cu anh den tim tai het roi a🤣",
f"moi ti xiu ma go duoi roi a {chon_name}🤣",
f"anh speed ne tk ngu {chon_name}👉😏",
f"cn cho ngu {chon_name} moi 5p ma da met a🤣🤣",
f"tk bach tang {chon_name}",
f"ccho dot la {chon_name}",
f"ngu cn ra de a {chon_name}",
f"tk ngon lu {chon_name}",
f"sped di tk ga {chon_name}",
f"ga v em {chon_name}",
f"anh uoc ga giong may a {chon_name}",
f"o o cn nghich tu {chon_name}",
f"chay dau vay tk {chon_name} ngu",
f"anh cho may chay a {chon_name}",
f"chay nhanh vay em {chon_name}",
f"ma sao em thoat khoi anh duoc ha {chon_name} em",
f"co gang win anh di {chon_name}",
f"sap win dc roi do {chon_name}",
f"e e care t di ma {chon_name}",
f"sao ko giam {chon_name}",
f"roi roi cam lang a {chon_name}",
f"on khong vay {chon_name}",
f"bat on a {chon_name}",
f"bi tao chui ma sao on dc {chon_name}",
f"cn cali {chon_name} sua bay",
f"ai cho m sua v {chon_name}",
f"xin phep ah chua o {chon_name}",
f"da may chetme may ma cn culi {chon_name} du xe",
f"sao may bel vay em {chon_name}",
f"120kg a {chon_name}",
f"sao may khon v {chon_name}",
f"khon nhu con kiki nha tao🤣 {chon_name}",
f"sat thuog ti di em {chon_name}",
f"em kem coi v {chon_name}",
f"co gi khac khong {chon_name}",
f"khong co j a {chon_name}",
f"em phe vay la cung dk {chon_name}",
f"dung a🤣 {chon_name}",
f"roi roi {chon_name}",
f"cn phe {chon_name}",
f"leg keg di troi {chon_name}",
f"lien tuc {chon_name} di boa",
f"sao ko lien tuc {chon_name}",
f"yeu sinh ly a🤣 {chon_name}",
f"nang khong em {chon_name}",
f"so anh nen dai ra mau luon a {chon_name}",
f"cn culi {chon_name} mat mam",
f"gap gap len tk ngu {chon_name}",
f"anh speed vcl ma {chon_name}",
f"may slow vaicalonn {chon_name}",
f"an c j phe lam vay tk phe vat {chon_name}",
f"cay cu anh lam ma {chon_name}",
f"cay ma choi a {chon_name}",
f"nhin mat ns nhu trai ot kia {chon_name}",
f"choi la doi a {chon_name}",
f"sao hay v cn dog ten {chon_name}",
f"t cam ba chia dam dit bme may ma {chon_name}",
f"o o thg cn bat hieu nay chs gay vs cau {chon_name} a",
f"{chon_name} teu v em",
f"tau hai a {chon_name}",
f"cn an hai danh trong lang a {chon_name}",
f"duoi a {chon_name}",
f"nhin biet duoi r🤣 {chon_name}",
f"anh cho may rot a {chon_name}",
f"sao cam lang r {chon_name}",
f"roi roi cn ngu cam {chon_name}",
f"ccho {chon_name} nay phen ia v",
f"anh go ba vcl ay {chon_name}",
f"cay a {chon_name}",
f"Ngầu Êyy {chon_name}",
f"Cố lên con thú {chon_name}",
f"Tao cho mày ngậm chx ? {chon_name}",
f"Mày cút rồi hả {chon_name} ",
f"cố tí nữa {chon_name}",
f"speed nào {chon_name}",
f"nhây tới năm sau dc ko {chon_name}",
f"mạnh mẽ nào {chon_name}",
f"Con culi mocoi ey {chon_name}",
f"k đc à {chon_name}",
f"con chó ngu cố đê {chon_name}",
f"sao m câm kìa {chon_name}",
f"gà j {chon_name}",
f"mày sợ tao à =)) {chon_name}",
f"m gà mà {chon_name}",
f"mày ngu rõ mà {chon_name}",
f"đúng mà {chon_name}",
f"cãi à {chon_name}",
f"mày còn gì khác k {chon_name}",
f"học lỏm kìa {chon_name}",
f"cố tí em {chon_name}",
f"mếu à {chon_name}",
f"sao mếu kìa {chon_name}",
f"tao đã cho m mếu đâu {chon_name}",
f"va lẹ đi con dốt {chon_name}",
f"sao kìa {chon_name}",
f"từ bỏ r à {chon_name}",
f"mạnh mẽ tí đi con đĩ {chon_name}",
f"cố lên con chó ngu {chon_name}",
f"=)) cay tao à con đĩ {chon_name}",
f"sợ tao à {chon_name}",
f"sao sợ tao kìa {chon_name}"
f"cay lắm phải kh {chon_name}",
f"ớt rồi kìa em {chon_name}",
f"mày còn chối à {chon_name}",
f"làm tí đê {chon_name}",
f"mới đó đã mệt r kìa {chon_name}",
f"sao gà mà sồn v {chon_name}",
f"sồn như lúc đầu cho tao {chon_name}",
f"sao à {chon_name}",
f"ai cho m nhai {chon_name}",
f"cay lắm r {chon_name}", 
f"từ bỏ đi em {chon_name}",
f"mày nghĩ mày làm t cay đc à {chon_name}",
f"có đâu {chon_name}",
f"tao đang hành m mà {chon_name}",
f"bịa à {chon_name}",
f"cay :))))) {chon_name}",
f"cố lên chó dốt {chon_name}",
f"hăng tiếp đi {chon_name}",
f"tới sáng k em {chon_name}",
f"k tới sáng à {chon_name}",
f"chán v {chon_name}",
f"m gà mà {chon_name}",
f"log acc thay phiên à {chon_name}",
f"coi tụi nó dồn ngu kìa {chon_name}",
f"sợ tao à con chó đần {chon_name}",
f"lại win à {chon_name}",
f"lại win r {chon_name}",
f"lũ cặc cay tao lắm🤣🤣 {chon_name}",
f"cố lên đê {chon_name}",
f"sao mới 5p đã câm r {chon_name}",
f"yếu đến thế à {chon_name}",
f"sao kìa {chon_name}",
f"khóc kìa {chon_name}",
f"cầu cứu lẹ ei {chon_name}",
f"ai cứu đc m à :)) {chon_name}",
f"tao bá mà {chon_name}",
f"sao m gà thế {chon_name}",
f"hăng lẹ cho tao {chon_name}",
f"con chó eiii🤣 {chon_name}",
f"ổn k em {chon_name}",
f"kh ổn r à {chon_name}",
f"mày óc à con chó bẻm=)) {chon_name}",
f"mẹ mày ngu à {chon_name}",
f"bú cặc cha m k em {chon_name}",
f"thg giả gái :)) {chon_name}",
f"coi nó ngu kìa ae {chon_name}",
f"con chó này giả ngu à {chon_name}",
f"m ổn k {chon_name}",
f"mồ côi kìa {chon_name}",
f"sao v sợ r à {chon_name}",
f"cố gắng tí em {chon_name}",
f"cay cú lắm r {chon_name}",
f"đấy đấy bắt đầu {chon_name}",
f"chảy nước đái bò r à em {chon_name}",
f"sao kìa đừng run {chon_name}",
f"mày run à:)) {chon_name}",
f"thg dái lở {chon_name}",
f"cay mẹ m lắm {chon_name}",
f"lgbt xuất trận à con đĩ {chon_name}",
f"thg cặc giết cha mắng mẹ {chon_name}",
f"sủa mạnh eii {chon_name}",
f"mày chết r à:)) {chon_name}",
f"sao chết kìa {chon_name}",
f"bị t hành nên muốn chết à {chon_name}",
f"con lồn ngu=)) {chon_name}",
f"sao kìa {chon_name}",
f"mạnh lên kìa {chon_name}",
f"yếu sinh lý à {chon_name}",
f"sủa đê {chon_name}",
f"cay à {chon_name}",
f"hăng đê {chon_name}",
f"gà kìa ae {chon_name}",
f"akakaa {chon_name}",
f"óc chó kìa {chon_name}",
f"🤣🤣🤣 {chon_name}",
f"ổn không🤣🤣 {chon_name}",
f"bất ổn à {chon_name}",
f"ơ kìaaa {chon_name}",
f"hăng hái đê {chon_name}",
f"chạy à 🤣🤣 {chon_name}",
f"tởn à {chon_name}",
f"kkkk {chon_name}",
f"mày dốt à {chon_name}",
f"cặc ngu {chon_name}",
f"cháy đê {chon_name}",
f"chat hăng lên {chon_name}",
f"cố lên {chon_name}",
f"mồ côi cay {chon_name}",
f"cay à {chon_name}",
f"cn chó ngu {chon_name}",
f"óc cac kìa {chon_name}",
f"đĩ đú:)) {chon_name}",
f"đú kìa {chon_name}",
f"cùn v {chon_name}",
f"r x {chon_name}",
f"hhhhh {chon_name}",
f"kkakak {chon_name}",
f"sao đú đó em {chon_name}",
f"cac teo a con {chon_name}",
f"ngu kìa {chon_name}",
f"chat mạnh đê {chon_name}",
f"hăng ee {chon_name}",
f"ơ ơ ơ {chon_name}",
f"sủa cháy đê {chon_name}",
f"sủa mạnh eei {chon_name}",
f"mày óc à con {chon_name}",
f"tao cho m chạy à {chon_name}",
f"con đĩ ngu sủa? {chon_name}",
f"mày chạy à con đĩ lồn {chon_name}",
f"co len con {chon_name}",
f"son hang len em {chon_name}",
f"sao m yeu v {chon_name} ",
f"co ti nua {chon_name}",
f"sao kia cham a {chon_name}",
f"hang hai len ti chu {chon_name}",
f"toi sang di {chon_name}",
f"co gang ti con cho {chon_name}",
f"yeu v con {chon_name}",
f"con cho {chon_name} co de",
f"sao m cam kia {chon_name}",
f"ga v {chon_name}",
f"may so a k dam chat hang ak {chon_name}",
f"m ga ma {chon_name}",
f"may ngu ro ma {chon_name}",
f"con {chon_name} an hai ma",
f"cai cun ak {chon_name}",
f"may con gi khac ko vay {chon_name}",
f"hoc dot nen nhay dot ak {chon_name}",
f"co ti di em {chon_name}",
f"meu a {chon_name}",
f"sao meu kia {chon_name}",
f"tao da cho m meu dau {chon_name}",
f"va le di con {chon_name} dot",
f"sao kia {chon_name}",
f"tu bo r a {chon_name}",
f"manh me ti di con {chon_name}",
f"co len con cho {chon_name} ngu",
f"😆 cay tao a con di {chon_name}",
f"so tao a {chon_name}",
f"sao cham roi kia {chon_name}",
f"cay lam phai kh {chon_name}",
f"{chon_name} ot anh cmnr",
f"may con choi a {chon_name}",
f"lam ti keo de {chon_name}",
f"moi do da met r ha {chon_name}",
f"sao ga ma son v {chon_name}",
f"son nhu luc dau cho tao di con {chon_name} dot",
f"sao duoi roi kia {chon_name}",
f"ai cho m nhai vay {chon_name}",
f"cay lam r a {chon_name}",
f"tu bo di em {chon_name}",
f"may nghi may lam t cay dc ha {chon_name}",
f"m dang cay ma {chon_name}",
f"tao dang hanh m ma {chon_name}",
f"keo nhay kg ay {chon_name}",
f"con mo coi {chon_name}",
f"co len {chon_name} oc cho",
f"hang tiep di {chon_name}",
f"toi sang k em {chon_name}",
f"met roi ha {chon_name}",
f"speed ti dc ko {chon_name}",
f"m ga ma {chon_name}",
f"thay phien a {chon_name}",
f"tui anh thay phien ban vo loz me con {chon_name} ma kaka",
f"so tao a con cho {chon_name}",
f"anh win me roi {chon_name} dot",
f"ga ma hay the hien ha {chon_name}",
f"con mo coi {chon_name} keo cai ko em",
f"co len de {chon_name}",
f"sao moi 1 ti ma da cam roi {chon_name}",
f"yeu vay ak {chon_name}",
f"sao kia {chon_name}",
f"bat luc r ak {chon_name}",
f"tim cach roi ha {chon_name}",
f"ai cuu dc m a :)) {chon_name}",
f"anh ba cmnr ma {chon_name}",
f"sao m ga vay {chon_name}",
f"hang le cho tao di {chon_name}",
f"con mo coi {chon_name}",
f"on k em {chon_name}",
f"bat on roi a {chon_name}",
f"may oc a con cho {chon_name}",
f"me may ngu a {chon_name}",
f"bu cac cha m k em {chon_name}",
f"mo coi {chon_name} cay anh ha",
f"me m dot tu roi a {chon_name}",
f"phe vay {chon_name}",
f"m on k {chon_name}",
f"mo coi kia {chon_name}",
f"sao v so r a {chon_name}",
f"co gang ti em {chon_name}",
f"cay cu lam r ha {chon_name}",
f"dien dai di em {chon_name}",
f"chay nuoc dai bo r a em {chon_name}",
f"sao kia dung so anh ma {chon_name}",
f"may run a:)) {chon_name}",
f"thg {chon_name} mo coi",
f"cay tao lam ha {chon_name}",
f"lgbt len phim ngu ak em {chon_name}",
f"thg cac giet cha mang me {chon_name}",
f"sua manh eii {chon_name}",
f"may chet r a:)) {chon_name}",
f"sao chet kia {chon_name}",
f"bi t hanh nen muon chet a {chon_name}",
f"con {chon_name} loz ngu kaka",
f"sao kia {chon_name}",
f"manh len kia {chon_name}",
f"yeu sinh ly a {chon_name}",
f"sua de {chon_name}",
f"cay a {chon_name}",
f"hang de {chon_name}",
f"con ga {chon_name}",
f"phe vat {chon_name}",
f"oc cho {chon_name}",
f"me m bi t du hap hoi kia con {chon_name}",
f"on ko em {chon_name}",
f"bat on ak {chon_name}",
f"o kiaaa sao vayy {chon_name}",
f"hang hai de {chon_name}",
f"chay ak {chon_name}",
f"so ak {chon_name}",
f"quiu luon roi ak {chon_name}",
f"may dot ak {chon_name}",
f"cac ngu {chon_name}",
f"chay de {chon_name}",
f"chat hang len {chon_name}",
f"co len {chon_name}",
f"{chon_name} mo coi",
f"cn cho ngu {chon_name}",
f"oc cac {chon_name}",
f"di du {chon_name}",
f"du kia {chon_name}",
f"cun v {chon_name}",
f"r luon con {chon_name} bi ngu roi",
f"met r am {chon_name}",
f"kkakak",
f"sao du {chon_name}",
f"cac con {chon_name}",
f"ngu kia {chon_name}",
f"chat manh de {chon_name}",
f"hang ee {chon_name}",
f"clm thk oc cho {chon_name}",
f"sua chay de {chon_name}",
f"sua manh eei {chon_name}",
f"may oc a con {chon_name}",
f"tao cho m chay a {chon_name}",
f"con mo coi {chon_name}",
f"may chay a con di lon {chon_name}",
f"sua de {chon_name}",
f"con phen {chon_name}",
f"bat on ho {chon_name}",
f"s do  {chon_name}",
f"sua lien tuc de {chon_name}",
f"moi tay ak {chon_name}",
f"choi t giet cha ma m ne {chon_name}",
f"hang xiu de {chon_name}",
f"th ngu {chon_name}",
f"len daica bieu ne {chon_name}",
f"sua chill de {chon_name}",
f"m thich du ko da {chon_name}",
f"son hang dc kg {chon_name}",
f"cam chay nhen {chon_name}",
f"m mau de {chon_name}",
f"duoi ak {chon_name}",
f"th ngu {chon_name}",
f"con {chon_name} len day anh sut chet me may",
f"m khoc ak {chon_name}",
f"sua lien tuc de {chon_name}",
f"thg {chon_name} cho dien",
f"bi ngu ak {chon_name}",
f"speed de {chon_name}",
f"cham v cn culi {chon_name}",
f"hoang loan ak {chon_name}",
f"bat on ak {chon_name}",
f"run ak {chon_name}",
f"chay ak {chon_name}",
f"duoi ak {chon_name}",
f"met r ak {chon_name}",
f"sua mau {chon_name}",
f"manh dan len {chon_name}",
f"nhanh t cho co hoi cuu ma m ne {chon_name}",
f"cam mach me nha {chon_name}",
f"ao war ak {chon_name}",
f"tk {chon_name} dot v ak",
f"cham chap ak {chon_name}",
f"th cho bua m sao v {chon_name}",
f"th dau buoi mat cho {chon_name}",
f"cam hoang loan ma {chon_name}",
f"lo lo sao may cam v {chon_name}",
f"ai cho may cam vayy {chon_name}",
f"anh cho chx ay=)) {chon_name}",
f"cmm hai a {chon_name}",
f"hai vay em {chon_name}",
f"co gi khac khong {chon_name}",
f"khong a {chon_name}",
f"ga den vay a {chon_name}",
f"thang an hai lien tuc di {chon_name}",
f"bi anh dap dau ma {chon_name}",
f"cay cu anh lam dk {chon_name}",
f"âkkak sua di em {chon_name}",
f"ccho ngu sua {chon_name}",
f"xem ns occho kia {chon_name}",
f"ngu hay sua a👉😏 {chon_name}",
f"alo alo cdy ngu {chon_name}👉🤪",
f"leg keg loc troc lay sa beg dap dau may {chon_name}👉🤣",
f"sua hang hai ti di em ey {chon_name}👉🤪",
f"may vua sua bi tao lay sa beg dap vo 2 hon trug dai ma {chon_name}👉😋",
f"o o cn culi {chon_name} bia ngu a👉🤣🤣",
f"cay anh ma lmj dc anh dau {chon_name} dk🤞🤞",
f"culi {chon_name} cn oc bem a con😋",
f"sao do coan zai {chon_name} cn sua dc khong ay👉😏",
f"khong a {chon_name}🤣🤣",
f"anh biet anh ba ma {chon_name}",
f"ccho ngu hay sua a {chon_name}🤪🤪",
f"mat may nhu trai ot roi kia {chon_name}🤣🤣",
f"ngu ngu bi anh dap dau vo cot dien chetme may nha {chon_name}🤣🤣",
f"anh thog minh vcll ma {chon_name}🤪🤪",
f"may ngu nguc vcll ma em {chon_name}🤣🤣",
f"dk {chon_name} em😏🤞",
f"dung a {chon_name}🤣🤣",
f"may lam tao cuoi dc roi ds {chon_name}🤪🤞",
f"dien siet duoc roi do {chon_name} ngu ey🤣🤣",
f"anh chuc may dien ko ai coi nha {chon_name}👉🤣",
f"bi anh hanh ha den die dk {chon_name}😏🤞",
f"anh dap chetme may ma {chon_name} em🤣🤣",
f"sua lam vay {chon_name} kiki🤣🤣",
f"cn me nay hap hoi a {chon_name}👉😏🤞",
f"may bua nhan a {chon_name}🤣🤣",
f"run ray khi gap a ma {chon_name}🤪🤞",
f"anh len san la may khiep so dk {chon_name}🤣🤣",
f"do ah ba qua nen may so dk {chon_name}👉😏",
f"may van xin anh tha thu ma {chon_name}😝🙏",
f"tao cam ak47 na vo dau mat chetme may {chon_name}😝🙏",
f"may sua dien cuong di {chon_name}🤣🤣",
f"cmm ngu the em {chon_name}🤣🤞",
f"ai ngu = may nua dau {chon_name} em 👉🤣🤞",
f"may nhu culi giang tran vay {chon_name}🤣🤣",
f"may ma culi j may lgbt ma {chon_name} em🤣",
f"anh ba dao san war ma {chon_name} cu😝👎",
f"may an cut san treo ma {chon_name} 👉🤣🤞",
f"bu cut tao song qua ngay ma {chon_name}🤣🤣",
f"xao lon cn gay a {chon_name}😝",
f"culi biet sua la day a {chon_name}😏🤞",
f"ga ma gay quai vay {chon_name}🤪👌",
f"may can ngon roi a {chon_name}😏🤞",
f"con gi khac hon khong {chon_name}🤪🤪",
f"khog a {chon_name}🤣",
f"ngu den vay la cung ha {chon_name}😏🤞",
f"sao may phe nhan vay😏🤞",
f"con nghich tu phan loan {chon_name}🤣🤣",
f"con cho chiu so phan di {chon_name}😏🤞",
f"chiu so phan bi anh dam cha giet ma {chon_name} ha🤣🤣",
f"anh cs hoi dau may tu tra loi a {chon_name}🤣",
f"tk bua nhan {chon_name}😏🤞",
f"sao culi khong sua nx di {chon_name}🤣🤣",
f"nin ngon roi a {chon_name}🤣🤪",
f"gap phai cha la may phai ngam ot roi {chon_name}🤣🤣",
f"ngon xam cac lay len doi bem ah a tk culi {chon_name}🤪🤞",
f"cn cali mat mam sua j ay {chon_name}😏🤞",
f"len nhay vs ah toi trang tron di {chon_name}😝",
f"sao ay tai mat roi a {chon_name}🤣🤣",
f"so lam roi a {chon_name}😏🤞",
f"co may anh da dau may toi chet me {chon_name}🤣",
f"dcm cay cu anh a {chon_name}🤣🤣",
]

    class NhayReoWorker:
        def __init__(self, messengers, box_ids, messages, delay, stop_event):
            self.messengers = messengers
            self.box_ids = box_ids
            self.messages = messages
            self.delay = delay
            self.stop_event = stop_event

        def run(self):
            idx = 0
            while not self.stop_event.is_set():
                for messenger in self.messengers:
                    for box_id in self.box_ids:
                        msg = self.messages[idx % len(self.messages)]
                        result = messenger.gui_tn(box_id, msg)
                        if result.get("success"):
                            print(f"[NHAY][{messenger.user_id}] → {box_id}: OK")
                        else:
                            print(f"[NHAY][{messenger.user_id}] → {box_id}: FAIL")
                        time.sleep(0.2)
                idx += 1
                time.sleep(self.delay)

    stop_event = threading.Event()
    start_time = datetime.now()

    worker = NhayReoWorker(messengers, id_list, CAU_CHUI, delay, stop_event)
    thread = threading.Thread(target=worker.run, daemon=True)
    thread.start()

    if discord_user_id not in user_nhaymess_tabs:
        user_nhaymess_tabs[discord_user_id] = []
    user_nhaymess_tabs[discord_user_id].append({
        "messengers": messengers,
        "box_ids": id_list,
        "delay": delay,
        "start_time": start_time,
        "stop_event": stop_event,
        "thread": thread
    })

    embed = discord.Embed(title="✅ Đã tạo tab nhây mess", color=0x00ff00)
    embed.add_field(name="👤 Người dùng", value=f"<@{discord_user_id}>", inline=False)
    embed.add_field(name="📨 To", value=", ".join(id_list), inline=False)
    embed.add_field(name="📡 Tài khoản", value=str(len(messengers)), inline=True)
    embed.add_field(name="⏱ Delay", value=f"{delay} giây", inline=True)
    embed.add_field(name="🕰 Bắt đầu", value=start_time.strftime("%Y-%m-%d %H:%M:%S"), inline=False)

    await interaction.followup.send(embed=embed)

@tree.command(name="tabnhaymess", description="Xem tab đang chạy và dừng từng tab")
async def tabnhaymess(interaction: discord.Interaction):
    discord_user_id = str(interaction.user.id)
    tabs = user_nhaymess_tabs.get(discord_user_id, [])
    if not tabs:
        return await interaction.response.send_message("⚠️ Không có tab nào đang chạy.", ephemeral=True)

    desc = ""
    for idx, tab in enumerate(tabs):
        elapsed = (datetime.now() - tab["start_time"]).total_seconds()
        h, rem = divmod(int(elapsed), 3600)
        m, s = divmod(rem, 60)
        uptime = f"{h:02}:{m:02}:{s:02}"
        desc += (
            f"**{idx + 1}.** Box: `{', '.join(tab['box_ids'])}` | "
            f"Delay: `{tab['delay']}s` | Uptime: `{uptime}`\n"
        )

    embed = discord.Embed(title="📋 Danh sách tab nhây đang chạy", description=desc, color=0x3498db)
    embed.set_footer(text="Trả lời tin nhắn này bằng STT để dừng tab.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

    def check(msg):
        return (
            msg.author.id == interaction.user.id and 
            msg.channel.id == interaction.channel.id and 
            msg.content.isdigit()
        )

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        stt = int(msg.content.strip()) - 1
        if 0 <= stt < len(tabs):
            tabs[stt]["stop_event"].set()
            del tabs[stt]
            if not tabs:
                del user_nhaymess_tabs[discord_user_id]
            await msg.reply("🛑 Đã dừng tab thành công.")
        else:
            await msg.reply("❌ STT không hợp lệ.")
    except:
        await interaction.followup.send("⏰ Hết thời gian chọn STT.", ephemeral=True)

@bot.event
async def on_ready():
    await tree.sync()
    print("✅ Bot đã online và đã sync slash command")

@tree.command(name="treodis", description="Treo ng\u00f4n discord")
@app_commands.describe(
    tokens="Token",
    channels="ID Channel",
    message="N\u1ed9i dung",
    delays="Delay"
)
async def treodis(
    interaction: discord.Interaction,
    tokens: str,
    channels: str,
    message: str,
    delays: str
):
    if not is_authorized(interaction) and not is_admin(interaction):
        return await interaction.response.send_message("B\u1ea1n kh\u00f4ng c\u00f3 quy\u1ec1n s\u1eed d\u1ee5ng bot", ephemeral=True)

    tokens_list = [t.strip() for t in tokens.split(",") if t.strip()]
    channels_list = [c.strip() for c in channels.split(",") if c.strip()]
    try:
        delays_list = [float(d.strip()) for d in delays.split(",") if d.strip()]
    except:
        return await interaction.response.send_message("Delay ph\u1ea3i l\u00e0 s\u1ed1", ephemeral=True)

    if not tokens_list or not channels_list or not delays_list:
        return await interaction.response.send_message("Thi\u1ebfu tokens/channels/delays h\u1ee3p l\u1ec7", ephemeral=True)
    if len(delays_list) not in (1, len(tokens_list)):
        return await interaction.response.send_message("Delay count ph\u1ea3i =1 ho\u1eb7c = s\u1ed1 token", ephemeral=True)
    if any(d < 0.5 for d in delays_list):
        return await interaction.response.send_message("Delay ph\u1ea3i tr\u00ean 0.5s.", ephemeral=True)

    if len(delays_list) == 1:
        delays_list *= len(tokens_list)

    session = aiohttp.ClientSession()
    start_time = datetime.now()
    discord_user_id = str(interaction.user.id)
    tasks = []

    for token, delay in zip(tokens_list, delays_list):
        task = asyncio.create_task(
            _discord_spam_worker(session, token, channels_list, message, delay, start_time, discord_user_id)
        )
        tasks.append(task)

    async with DIS_LOCK:
        if discord_user_id not in user_discord_tabs:
            user_discord_tabs[discord_user_id] = []
        user_discord_tabs[discord_user_id].append({
            "session": session,
            "tasks": tasks,
            "channels": channels_list,
            "tokens": tokens_list,
            "delays": delays_list,
            "message": message,
            "start": start_time
        })

    return await interaction.response.send_message(
        f"\u0110\u00e3 t\u1ea1o tab treo discord cho <@{discord_user_id}>:\n"
        f"\u2022 Channels: `{', '.join(channels_list)}`\n"
        f"\u2022 Tokens: `{len(tokens_list)}`\n"
        f"\u2022 Delay(s): `{', '.join(str(d) for d in delays_list)}` gi\u00e2y\n"
        f"\u2022 B\u1eaft \u0111\u1ea7u: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`",
        ephemeral=True
    )
    
def format_time(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02}"    
  
@tree.command(
    name="tabtreodis",
    description="Quản lý/dừng tab treo iscord"
)
async def tabtreodis(interaction: discord.Interaction):
    if not is_authorized(interaction) and not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot", ephemeral=True)

    discord_user_id = str(interaction.user.id)
    async with DIS_LOCK:
        tabs = user_discord_tabs.get(discord_user_id, [])

    if not tabs:
        return await interaction.response.send_message("Bạn không có tab treo discord nào đang hoạt động", ephemeral=True)

    msg = "**Danh sách tab treo discord của bạn:**\n"
    for idx, tab in enumerate(tabs, 1):
        elapsed = int((datetime.now() - tab["start"]).total_seconds())
        uptime = format_time(elapsed)
        msg += (
            f"{idx}. Channels:`{','.join(tab['channels'])}` | "
            f"Tokens:`{len(tab['tokens'])}` | Delays:`{','.join(str(d) for d in tab['delays'])}`s | "
            f"Uptime:`{uptime}`\n"
        )
    msg += f"\nNhập số tab để dừng tab"

    await interaction.response.send_message(msg, ephemeral=True)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("Hết thời gian. Không dừng tab nào", ephemeral=True)

    c = reply.content.strip()
    if not c.isdigit():
        return await interaction.followup.send("Không dừng tab nào", ephemeral=True)
    i = int(c)
    if not (1 <= i <= len(tabs)):
        return await interaction.followup.send("Số không hợp lệ", ephemeral=True)

    async with DIS_LOCK:
        tab = tabs.pop(i-1)
        for t in tab["tasks"]:
            t.cancel()
        await tab["session"].close()
        if not tabs:
            del user_discord_tabs[discord_user_id]

    return await interaction.followup.send(f"Đã dừng tab số {i}", ephemeral=True)  
    

messages = [
        "sao m rụng ngay khi anh đến r",
"mồ côi thắp hương cha mẹ trc khi chửi chưa",
"mồ côi không cha mẹ đổ thừa cay bố m kìa",
"‎‎tao thánh chửi mà :))‎‎",  
"tây tạng béo mỡ cha chọc chết tươi rồi😹",
"m còn trò j thể hiện nhanh lên ơ kìa",
"óc chó ko trình lên đây sủa mạnh mẽ lên anh chơi mày cả ngày mà😹",
"ơ hay óc chó ơi m sủa mạnh mẽ lên sao lại bị dập rồi",
"lêu lêu thằng ngu không làm gì được cay anh kìa",
"haha óc chó gà bị chửi cay cú ớt mẹ rồi: )))",
"óc chó ngu nghèo cay cha bán mạng đi chửi cha má kìa: ))))",
"m chạy đâu v con chó ngu ơi không được chạy mà: (((",
"ai đụng gì óc chó để nó sợ rồi chạy thục mạng kìa",
"culi ngu bị anh chửi té tát nước vô mặt m kìa: )))",
"culi bị chửi mất xác kìa😹😹😹",
"thằng nguuu giết cha bóp cổ má để cầu win anh à 😏 👉",
"hi vọng làm dân war của con ngu bị t dập tắt từ khi nó sủa điên trước mặt t ae=)))",  
"bà nội m loạn luân vs bố m còn ông ngoại m loạn luân vs mẹ m mà thg não cún =)) 🤪",
"Cn thú mại dâm bán dâm mà như bán trinh hoa hậu v🤣",
"con ngu nứng quá đến cả con mom nó gần u60 r nó vẫn ko tha=))",
"Mẹ mày làm con chó canh cửa cho nhà t mà🤣",  
"đáp ngôn nhanh hơn tý đc k tk ngu xuẩn🌬 🤢🤢",
"bắt quả tang con chó chạy bố nè",
"não cún chỉ biết âm thầm seen và ôm gối khóc mà huhuh 👈😜",
"‎‎ con cave này adr 16gb đg kiếm tiền mua ip đk🤣🤣",
" Vào 1 hôm bỗng con đĩ mẹ nhà m die thì lúc đó cha làm bá chủ sàn mẹ r :))",
"‎con đĩ mẹ mày bất lực vì bị tao chửi mà chỉ biết câm lặng:))",
"mẹ mày bị t đụ đột quỵ ngoài nhà nghỉ kìa đem hòm ra nha",
"đem hai cái mày với con mẹ m luôn nha",
"‎‎thời gian trôi qua để  cảm nhận nỗi đau đi ửa à",
"‎‎ nhai t chặt đầu con đĩ má m ra đó",
"thằng ngu lgbt da đen sủa lẹ ai cko mày câm",
"thằng sex thú đang cố làm cha cay hả thằng bại não",
"tao miễn nhiễm mà thằng ngu",
"Anh Bá Vcl Lỡ Đá Chết Mẹ mày Rồi  😝 👎",
"Mẹ Mày Bị Cha Đụ Từ Nam Vào Đến Bắc Mà 🤪 👊",
"Mẹ Mày Banh Háng Cho Khách Đụ Kìa Thằng Óc",
"Tao Lỡ Cho Mẹ Mày Bú Cu Tao Rồi Sướng Vãi Cặc🧐 🤙",
"Lêu Lêu Nhìn Cha Đụ Mẹ Mày Ko Làm Được Gì À Đừng Có Cay Cha Nha 😝 👎",
"‎‎bị tao khủng bố quá nát mẹ cái hộp sọ với não luôn rồi à =))",
"m là con đĩ đầu đinh giết má để loạn luân với bố mà con khốn",
"văn thơ anh lai láng để con mẹ m dạng háng mỗi đêm =)))",
"qua sông thì phải bắc cầu kiều con mẹ mày muốn làm đĩ thì phải yêu chiều các anh mà 🤣👈",
"con lồn ngu này hay đạp xe đạp ngang nhà tao bị tao chọi đá về méc mẹ mà🤣",
"thằng ngu này đang đi bộ bị t đánh úp nó về mách mẹ mà ae 🤣🤣",
"thằng này ăn và khen chubin anh singu khen ngon quá=))",
"thằng đầu đinh ở nhà lá mà ae nó mơ ước dc ở biệt thự như tui:))",
"cả họ nhà mày phải xếp hàng lần lượt bú dái t mà🤣🤣",
"thằng ảo war bị tao chửi cố gắng phản kháng nhưng nút home k cho phép mày cay quá đập cmn máy 🤣👈",
"Sống như 1 con chó ngu dốt như lũ phèn ói chợ búa cầm dao múa kiếm",
"Cha mày hóa thân thành hắc bạch vô thường cha mày bắt hồn đĩ mẹ mày xuống chầu diêm vương",
"Nghèo bần hèn bị cha mày đứng trên đạp đầu lũ đú chúng mày cha đi lên",
"Đú má mày tới tháng xịt nước máu kinh cho thk cha mày uống",
"mày đi học bị bạn bè chê xài nút home mày cay quá về đánh đập bà già kiu bả làm đĩ để có tiền mua dt mới đi sĩ với bạn bè =))",
"Con điếm phò mã bị cha mày cầm cái cây chà bồn cầu cha chà nát lồn mày nè",
"Đừng có lên mạng xã hội tạo nét mà bị anh hành là mếu máo đi cầu cứu ngay",
"mày thấy anh chửi thấm quá và nghĩ trong đầu là : anh này bá vcl đéo chửi lại nó đâu:)))",
"thằng này đang ăn bị t đứng trên nóc nhà nó t ỉa trúng bát cơm nó luôn mà ae",
"mày bí ngôn tới nỗi phải lên gg ghi : những câu chửi nhau hay nhất để phản kháng tao mà🤣👈",
"mày thấy a chửi hay quá nên xin làm đệ của anh để được kéo làm hw:)))",
"mày bị chửi tới nỗi tăng huyết áp phải cầu xin anh tha thứ:)))",
"người yêu nó bị t đụ rên ư ử khen ku a  to và dài thế:))))",
"mẹ nó khen cặk t to chấp nhận bỏ ba nó vì ông ấy ysl:)))",
"cha nó ôm hận t lắm chỉ biết đứng ôm cặk khóc trong vô vọng:)))",
"mẹ nó bị t đụ chán chê xong bị t trap t yêu người mẫu mà 🤣👈",
"con bướm trâu bị gái có cu yêu qua mạng trap=)))Gbao w kayros",
"trăng kia ai vẽ mà tròn loz con mẹ m bị ai địt mà mòn 1 bên 🤣",
"mẹ m có phải còn búp bê tình dục để a lục đục mỗi đêm k 😏?",
"mẹ m thì xóc lọ cho t còn người ta thì kính lão đắc thọ",
"m tin bố lấy yamaha bố đề số 3 bố tông vào loz cn đĩ mẹ m k",
"m gặp các anh đây toàn đấng tối cao a cầm con dao a đâm a thọc a chọc vào cái lỗ loz cn mẹ m mà 🤣👈",
"cha m lấy gạch ống chọi nát cái đầu mu lồn mẹ mày giờ con bẻm đú",
"con mồ côi mày mà rớt là tao lấy chiếc xe rùa t cán lòi mu lồn mẹ m đó gán trụ nha",
"cú đấm sấm sét của anh mtrung đấm nát cái lồn mẹ thằng chó đú nhây như mày🤣👈",
"cú đá cuồng phong đá bung cái lồn mẹ mày nè thằng não cặc🤣👈",
"anh lấy cái ô tô anh đâm thẳng dô cái lồn con gái mẹ thằng súc vật như m",
"hôm nay anh sẽ thay trời hành đạo anh cạo nát cái lông lồn con gái mẹ mày đó nghe chưa",
"anh đẹp trai hai mái quay qua bên trái đái nát dô cái bàn thờ gái mẹ nghe hong con dog=))",
"con đĩ eo di bi ti bị mẹ mày hành cho tới đột quỵ k có tiền lo t//ang lễ phải quỳ qua háng tao van xin tao cho tiền đúng kh",
"thằng cặc chứng kiến cái cảnh mẹ nó bị t cầm bật lửa đốt từng cộng lông bướm:)))",
"Anh gõ chết con đĩ mẹ mày giờ mày sủa ngôn có st tý coi em nhìn em phèn dạ anh mày chửi luôn ông bà mày đái lên mặt mày nè con sút vật yếu kém",
"thằng óc cặc bị tao ném xuống ao nhưng béo quá bị chết chìm🐕",
"mày bị tao hành hung cho sắp đột tử rồi kìa kêu con đĩ mẹ mày qua cứu vãn mày lẹ đi không là tao cho mày nằm quan tài gào khóc thảm thiết trong đó liền ngay 3s nè con đĩ phế",
"nhanh lên con chó lồn khai khắm=))",
"con gái mẹ mày die dưới tay bọn anh kìa",
"thằng bẻm bị t thọc cặc lên ổ cứng phát não rớt ra ngoài=)))",
"cạn bã của XH mà tưởng mình hay hã con thú🤣💨",
"thằng óc dái khi nghe tin cha nó chết kiểu: úi úi thằng già này cuối cùng cũng chết r vui vl=))",
"thằng lồn ảo anime bật gear 5 lên địt con già nó trước bàn thờ tổ tiên=))",
"anh cha dượng của bọn mày mà tụi bú cứt 🤣",
"đây là suy nghĩ của con ngu sau khi nó bị tao sỉ nhục trong đầu nó bây giờ kiểu: quân tử trả thù 10 năm chưa muộn :)))))",
"thằng ngu bị tao áp đảo từ phút 1 tới giờ nó k có cơ hội để sủa luôn ae=)))",
"thằng đú bot mời ae nó sang nhà đụ bà già nó free vì hôm nay là ngày vui vì cha nó mới qua đời=))",
"thằng cặc bị tao hạ đo ván sau 1 cú sút ngoạn mục đến từ vị trí anh trung hw=)))",
"thằng óc cặc đòi va anh và cái kết bị anh chửi chạy khắp nơi=))",
"mẹ mày bị tao địt rách màn trinh mà🤪  ",
"🤭🤭Mày bê đê ngũ sắc dell công khai bị tao chọc quá máu cặc mày dồn lên não choa mày chết hả",
"nhà thằng đú này nghèo không có tiền chơi gái nên phải loạn luân luôn với mẹ nó để giải khát cơn thèm thuồng"
"thằng cầm thú loạn luân some với mẹ ruột và ba ruột còn quay clip",
"m bị óc cứt hay sao z hả mà t nói m dell hiểu hay bố phải nhét cứt vào đầu m thì m mới thông hả con óc lồn ơi",
"Một lũ xam cu lên đây đú ửa ngôn thì nhạt như cái nước lồn của con đỉ mẹ cm v hăng lên đi con mẹ mày bị t xé rách mu sao chối ????",
"bà già mày bị tao treo cổ lên trên trần nhà mà?",
"thằng bất tài vô dụng sủa mạnh lên đi",
"cố gắng để win tao nhá",
"tao bất bại mà thằng ngu?",
"mẹ mày bị t đầu độc đến chết mà",
"mày đàn ông hay đàn bà yếu đuối vậy",
"con chó đầu đinh bị anh cầm cái đinh ba a thọc vào lỗ nhị nó mà ae =))",
"thằng như mày xứng đáng ăn cứt tao á",
"Mấy Con Thú Sài Tool Cha Đòi Bem Cha À",
"Nghe Cha Chửi Chết Con Gái Mẹ Mày Nè Con Ngu",
"Mẹ Mày Bị Tao Lấy Phóng Lợn Chọt Dô Mu Lồn Khi Đang Đi Làm Gái Ở Ngã 3 Trần Duy Hưng🤣👈",
"con mẹ m nghe tin m loạn luân vs bố m nên lấy dao cắt cổ tự tử r kìa con ngu :))",
"m tìm câu nào sát thương tí được k thằng nghịch tử đâm bố đụ mẹ :)) 🤣",
"óc chó bị anh chửi nhớ cha nhớ mẹ nhớ kiếp trước kìa😹😹😹",
    ]    
    

async def show_typing_animation(duration, prefix=""):
    end_time = asyncio.get_event_loop().time() + duration
    for ch in itertools.cycle(['.  ', '.. ', '...']):
        if asyncio.get_event_loop().time() > end_time:
            break
        sys.stdout.write(f"\r{prefix}[Typing] Đang soạn{ch}")
        sys.stdout.flush()
        await asyncio.sleep(0.5)
    sys.stdout.write("\r" + " " * 60 + "\r")


async def spam_worker(token, channel_id, delay, mention_ids, color, semaphore):
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    typing_url = f"https://discord.com/api/v10/channels/{channel_id}/typing"
    send_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    mention_text = " ".join([f"<@{uid}>" for uid in mention_ids]) if mention_ids else ""

    async with aiohttp.ClientSession() as session:
        while True:
            for msg in messages:
                try:
                    await semaphore.acquire()
                    await session.post(typing_url, headers=headers)
                    await show_typing_animation(delay, prefix=color)

                    full_msg = f"{mention_text} {msg}" if mention_text else msg
                    async with session.post(send_url, json={"content": full_msg}, headers=headers) as resp:
                        if resp.status == 200:
                            print(f"{color}[OK] Gửi vào kênh {channel_id}: {msg}")
                        else:
                            print(f"{color}[LỖI {resp.status}] {await resp.text()}")
                except Exception as e:
                    print(f"{color}[LỖI] Token gặp lỗi: {e}")
                    await asyncio.sleep(2)
                    gc.collect()
                finally:
                    semaphore.release()


class NhayDisModal(discord.ui.Modal, title="Spam Discord"):
    token = discord.ui.TextInput(label="Token (cách nhau bởi dấu phẩy)", style=discord.TextStyle.paragraph)
    channel_id = discord.ui.TextInput(label="Channel IDs (cách nhau bởi dấu phẩy)")
    delay = discord.ui.TextInput(label="Delay (giây)")
    mention_ids = discord.ui.TextInput(label="Mention IDs (tùy chọn)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("🚀 Đang tạo tab spam...", ephemeral=True)
        try:
            tokens = [t.strip() for t in self.token.value.strip().split(",") if t.strip()]
            channel_ids = [c.strip() for c in self.channel_id.value.strip().split(",") if c.strip()]
            delay = float(self.delay.value.strip())
            mention_list = [i.strip() for i in self.mention_ids.value.split(",")] if self.mention_ids.value else []
            discord_user_id = str(interaction.user.id)
            start_time = datetime.now()
            semaphore = asyncio.Semaphore(1)

            for token in tokens:
                for channel_id in channel_ids:
                    asyncio.create_task(
                        spam_worker(
                            token=token,
                            channel_id=channel_id,
                            delay=delay,
                            mention_ids=mention_list,
                            color=f"[{discord_user_id}] ",
                            semaphore=semaphore
                        )
                    )

            await interaction.followup.send(
                f"✅ Đã tạo {len(tokens) * len(channel_ids)} tab spam cho <@{discord_user_id}>:\n"
                f"• Kênh: `{', '.join(channel_ids)}`\n"
                f"• Mention: `{', '.join(mention_list) if mention_list else 'Không'}`\n"
                f"• Delay: `{delay}` giây\n"
                f"• Bắt đầu lúc: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi: `{e}`", ephemeral=True)


@tree.command(name="nhaydis", description="Tạo tab spam Discord")
async def nhaydis(interaction: discord.Interaction):
    await interaction.response.send_modal(NhayDisModal())

@tree.command(
    name="tabnhaydis",
    description="Quản lý/dừng tab nhây Discord"
)
async def tabnhaydis(interaction: discord.Interaction):
    if not is_authorized(interaction) and not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot", ephemeral=True)

    discord_user_id = str(interaction.user.id)
    async with NHAYDIS_LOCK:
        tabs = user_nhaydis_tabs.get(discord_user_id, [])

    if not tabs:
        return await interaction.response.send_message("❌ Bạn không có tab nhây Discord nào đang hoạt động.", ephemeral=True)

    msg = "**📌 Danh sách tab nhây Discord của bạn:**\n"
    for i, tab in enumerate(tabs, 1):
        uptime = format_time(int((datetime.now() - tab["start"]).total_seconds()))
        msg += (
            f"> **{i}.** 🧪 Tokens:`{tab['session_count']}` | 🛰 Channels:`{', '.join(tab['channels'])}` | "
            f"⏱ Delay:`{tab['delay']}`s | 🕒 Up:`{uptime}`\n"
        )
    msg += "\n👉 Vui lòng **nhập số thứ tự** tab muốn dừng (trong 30s):"

    await interaction.response.send_message(msg, ephemeral=True)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("⏰ Hết thời gian. Không dừng tab nào.", ephemeral=True)

    choice = reply.content.strip()
    if not choice.isdigit():
        return await interaction.followup.send("❌ Đầu vào không hợp lệ. Không dừng tab nào.", ephemeral=True)
    
    idx = int(choice)
    if not (1 <= idx <= len(tabs)):
        return await interaction.followup.send("❌ Số tab không hợp lệ.", ephemeral=True)

    async with NHAYDIS_LOCK:
        tab = tabs.pop(idx - 1)
        for t in tab["tasks"]:
            t.cancel()
        if not tabs:
            user_nhaydis_tabs.pop(discord_user_id, None)

    return await interaction.followup.send(f"✅ Đã dừng tab nhây số `{idx}` thành công.", ephemeral=True)    
    
def telegram_send_loop(token, chat_ids, caption, photo, delay, stop_event, discord_user_id):
    while not stop_event.is_set():
        for chat_id in chat_ids:
            if stop_event.is_set():
                break
            try:
                if photo:
                    if photo.startswith("http"):
                        url = f"https://api.telegram.org/bot{token}/sendPhoto"
                        data = {"chat_id": chat_id, "caption": caption, "photo": photo}
                        resp = requests.post(url, data=data, timeout=10)
                    else:
                        url = f"https://api.telegram.org/bot{token}/sendPhoto"
                        with open(photo, "rb") as f:
                            files = {"photo": f}
                            data = {"chat_id": chat_id, "caption": caption}
                            resp = requests.post(url, data=data, files=files, timeout=10)
                else:
                    url = f"https://api.telegram.org/bot{token}/sendMessage"
                    data = {"chat_id": chat_id, "text": caption}
                    resp = requests.post(url, data=data, timeout=10)

                if resp.status_code == 200:
                    print(f"[TELE][{discord_user_id}] Gửi thành công → {chat_id}")
                elif resp.status_code == 429:
                    retry = resp.json().get("parameters", {}).get("retry_after", 10)
                    print(f"[TELE][{discord_user_id}] Rate limit {retry}s")
                    time.sleep(retry)
                else:
                    print(f"[TELE][{discord_user_id}] Lỗi {resp.status_code}: {resp.text[:100]}")
            except Exception as e:
                print(f"[TELE][{discord_user_id}] Exception: {e}")
            time.sleep(0.2)
        time.sleep(delay)
        

@tree.command(
    name="treotele",
    description="Treo ngôn telegram"
)
@app_commands.describe(
    tokens="Token Telegram bot (ngăn cách dấu phẩy)",
    chats="ID nhóm chat (ngăn cách dấu phẩy)",
    text="Nội dung tin nhắn",
    delay="Delay giữa mỗi lần gửi (giây)",
    img="Link ảnh đính kèm (tuỳ chọn)"
)
async def treotele(
    interaction: discord.Interaction,
    tokens: str,
    chats: str,
    text: str,
    delay: int,
    img: str = None
):
    
    if not is_authorized(interaction) and not is_admin(interaction):
        return await interaction.response.send_message("❌ Bạn không có quyền sử dụng bot", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    tokens_list = [t.strip() for t in tokens.split(",") if t.strip()]
    chats_list = [c.strip() for c in chats.split(",") if c.strip()]

    if delay < 1:
        return await interaction.followup.send("❌ Delay phải lớn hơn 1 giây")

    valid = []
    for tk in tokens_list:
        try:
            resp = requests.get(f"https://api.telegram.org/bot{tk}/getMe", timeout=5)
            if resp.ok:
                valid.append(tk)
            else:
                await interaction.followup.send(f"⚠️ Token không hợp lệ: `{tk}`")
        except requests.exceptions.ConnectTimeout:
            await interaction.followup.send(f"⚠️ Không thể kiểm tra token `{tk}`: kết nối Telegram bị timeout, vẫn cho phép chạy")
            valid.append(tk)  
        except Exception as e:
            await interaction.followup.send(f"⚠️ Lỗi kiểm tra token `{tk}`: `{e}`")

    if not valid:
        return await interaction.followup.send("❌ Không có token hợp lệ")

    discord_user_id = str(interaction.user.id)
    start_time = datetime.now()

    for tk in valid:
        stop_event = multiprocessing.Event()
        process = multiprocessing.Process(
            target=telegram_send_loop,
            args=(tk, chats_list, text, img, delay, stop_event, discord_user_id),
            daemon=True
        )
        process.start()

        with TREOTELE_LOCK:
            user_treotele_tabs.setdefault(discord_user_id, []).append({
                "process": process,
                "stop_event": stop_event,
                "start": start_time,
                "token": tk,
                "chats": chats_list,
                "text": text,
                "img": img,
                "delay": delay
            })

    await interaction.followup.send(
        f"✅ Đã tạo tab treo Telegram cho <@{discord_user_id}>:\n"
        f"• Chats: `{', '.join(chats_list)}`\n"
        f"• Tokens: `{len(valid)}`\n"
        f"• Delay: `{delay}` giây\n"
        f"• Ảnh: `{img or 'Không có'}`\n"
        f"• Bắt đầu: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`"
    )
                
@tree.command(
    name="tabtreotele",
    description="Quản lý/dừng tab treo telegram"
)
async def tabtreotele(interaction: discord.Interaction):
    if not is_authorized(interaction) and not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot", ephemeral=True)

    discord_user_id = str(interaction.user.id)
    with TREOTELE_LOCK:
        tabs = user_treotele_tabs.get(discord_user_id, [])

    if not tabs:
        return await interaction.response.send_message("Bạn không có tab treo telegram nào đang hoạt động", ephemeral=True)

    msg = "**Danh sách tab treo telegram của bạn:**\n"
    for i, tab in enumerate(tabs, 1):
        elapsed = int((datetime.now() - tab["start"]).total_seconds())
        uptime = time.strftime("%H:%M:%S", time.gmtime(elapsed))
        msg += (
            f"{i}. Token:`{tab['token'][:10]}...` | Chats:`{','.join(tab['chats'])}` | "
            f"Delay:`{tab['delay']}`s | Up:`{uptime}`\n"
        )
    msg += f"\nNhập số tab để dừng tab"

    await interaction.response.send_message(msg, ephemeral=True)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("Hết thời gian. Không dừng tab nào", ephemeral=True)

    choice = reply.content.strip()
    if not choice.isdigit():
        return await interaction.followup.send("Không dừng tab nào", ephemeral=True)
    idx = int(choice)
    if not (1 <= idx <= len(tabs)):
        return await interaction.followup.send("Số không hợp lệ", ephemeral=True)

    with TREOTELE_LOCK:
        tab = tabs.pop(idx-1)
        tab["stop_event"].set()
        if not tabs:
            user_treotele_tabs.pop(discord_user_id, None)

    return await interaction.followup.send(f"Đã dừng tab số {idx}", ephemeral=True)
    

os.makedirs("sessions", exist_ok=True)


def parse_cookie_str(cookie_str):
    return dict(item.strip().split('=', 1) for item in cookie_str.split(';') if '=' in item)

def _ig_spam_loop(task_id, user_id, cl, targets, message, delay, stop_set):
    while True:
        for target in targets:
            try:
                if target in stop_set:
                    continue
                if target.isdigit():
                    cl.direct_send(text=message, user_ids=[int(target)])
                else:
                    uid = cl.user_id_from_username(target)
                    cl.direct_send(text=message, user_ids=[uid])
                print(f"[✓] Gửi IG đến {target}")
            except Exception as e:
                print(f"[×] Lỗi IG với {target}: {e}")
            time.sleep(delay)

@tree.command(
    name="treoig",
    description="Treo ngôn IG"
)
@app_commands.describe(
    cookie="Cookie hoặc username|password, phân cách bằng dấu phẩy",
    targets="Danh sách ID hoặc username IG (phân cách dấu phẩy)",
    message="Nội dung tin nhắn",
    delay="Thời gian delay mỗi vòng (giây)"
)
async def treoig(
    interaction: discord.Interaction,
    cookie: str,
    targets: str,
    message: str,
    delay: float
):
    if not is_authorized(interaction) and not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot", ephemeral=True)
    if delay < 0.5:
        return await interaction.response.send_message("Delay phải lớn hơn 0.5s", ephemeral=True)

    account_lines = [line.strip() for line in cookie.split(",") if line.strip()]
    clients = []

    for line in account_lines:
        try:
            cl = Client()
            cl.delay_range = [1, 3]

            if "|" in line:
                username, password = line.split("|", 1)
                session_path = f"sessions/{username.strip()}.json"
                if os.path.exists(session_path):
                    cl.load_settings(session_path)
                    try:
                        cl.get_timeline_feed()
                        print(f"[✓] Đăng nhập từ session: {username}")
                    except:
                        print(f"[!] Session hết hạn, đăng nhập lại: {username}")
                        cl.login(username.strip(), password.strip())
                        cl.dump_settings(session_path)
                else:
                    cl.login(username.strip(), password.strip())
                    cl.dump_settings(session_path)
                    print(f"[✓] Đăng nhập IG và lưu session: {username}")
            else:
                cookie_dict = parse_cookie_str(line)
                sessionid = cookie_dict.get("sessionid")
                if not sessionid:
                    raise Exception("Không tìm thấy sessionid trong cookie")
                cl.login_by_sessionid(sessionid=sessionid)
                print(f"[✓] Đăng nhập IG bằng sessionid")

            clients.append(cl)

        except Exception as e:
            await interaction.user.send(f"❌ Đăng nhập IG thất bại cho `{line}`:\nLỗi: {e}")
            continue

    if not clients:
        return await interaction.response.send_message("Không có tài khoản IG nào đăng nhập được!", ephemeral=True)

    tgt_list = [t.strip() for t in targets.split(",") if t.strip()]
    if not tgt_list:
        return await interaction.response.send_message("Phải nhập ít nhất 1 target IG", ephemeral=True)

    discord_user_id = str(interaction.user.id)
    task_id = len(SPAM_TASKS.get(discord_user_id, [])) + 1
    stop_set = set()

    for cl in clients:
        thread = threading.Thread(
            target=_ig_spam_loop,
            args=(task_id, discord_user_id, cl, tgt_list, message, delay, stop_set),
            daemon=True
        )

        with IG_LOCK:
            SPAM_TASKS.setdefault(discord_user_id, []).append({
                "id": task_id,
                "thread": thread,
                "stop_targets": stop_set,
                "start": datetime.now(),
                "client": cl,
                "targets": tgt_list,
                "message": message,
                "delay": delay
            })

        thread.start()

    await interaction.response.send_message(
        f"Đã tạo tab treo IG cho <@{discord_user_id}> (Task {task_id}):\n"
        f"• Tài khoản: `{len(clients)}`\n"
        f"• Targets: `{', '.join(tgt_list)}`\n"
        f"• Delay: `{delay}` giây\n"
        f"• Bắt đầu lúc: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        ephemeral=True
    )

    
@tree.command(
    name="tabtreoig",
    description="Quản lý/dừng tab treo ig"
)
async def tabtreoig(interaction: discord.Interaction):
    if not is_authorized(interaction) and not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot", ephemeral=True)

    discord_user_id = str(interaction.user.id)
    with IG_LOCK:
        tasks = SPAM_TASKS.get(discord_user_id, [])

    if not tasks:
        return await interaction.response.send_message("Bạn không có tab treo ig nào đang hoạt động", ephemeral=True)

    msg = "**Danh sách tan treo ig của bạn:**\n"
    for t in tasks:
        uptime = datetime.now() - t["start"]
        msg += (
            f"{t['id']}. Targets:`{','.join(t['targets'])}` | "
            f"Delay:`{t['delay']}`s | Up:`{str(uptime).split('.')[0]}`\n"
        )
    msg += f"\nNhập số tab để dừng tab"

    await interaction.response.send_message(msg, ephemeral=True)

    def check(m: discord.Message):
        return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("Hết thời gian. Không dừng tab nào", ephemeral=True)

    parts = [p.strip() for p in reply.content.split(",",1)]
    if len(parts) != 2 or not parts[0].isdigit():
        return await interaction.followup.send("Không dừng tab nào", ephemeral=True)
    tid = int(parts[0])
    choice = parts[1]

    with IG_LOCK:
        task = next((x for x in tasks if x["id"] == tid), None)
        if not task:
            return await interaction.followup.send("Tab không tồn tại", ephemeral=True)
        if choice.lower() == "all":
            tasks.remove(task)
            return await interaction.followup.send(f"Đã xóa tab {tid}", ephemeral=True)
        if choice in task["targets"]:
            task["stop_targets"].add(choice)
            return await interaction.followup.send(f"Đã dừng spam tới `{choice}` trong tab {tid}", ephemeral=True)
        else:
            return await interaction.followup.send("Target không tồn tại trong tab", ephemeral=True)

@tree.command(
    name="treogmail",
    description="Treo gmail"
)
@app_commands.describe(
    accounts="Email|Passapp",
    to_email="Email nhận",
    content="Nội dung",
    delay="Delay"
)
async def treogmail(
    interaction: discord.Interaction,
    accounts: str,
    to_email: str,
    content: str,
    delay: float
):
    if not is_authorized(interaction) and not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot", ephemeral=True)
    if delay < 1:
        return await interaction.response.send_message("Delay phải trên 1s", ephemeral=True)

    smtp_list = parse_gmail_accounts(accounts)
    if not smtp_list:
        return await interaction.response.send_message("Không parse được tài khoản", ephemeral=True)

    discord_user_id = str(interaction.user.id)
    stop_evt = threading.Event()
    start_time = datetime.now()

    tab = {
        "thread": None,
        "stop_event": stop_evt,
        "start": start_time,
        "smtp_list": smtp_list,
        "to_email": to_email,
        "content": content,
        "delay": delay
    }
    thread = threading.Thread(target=gmail_spam_loop, args=(tab, discord_user_id), daemon=True)
    tab["thread"] = thread

    with TREOGMAIL_LOCK:
        user_treogmail_tabs.setdefault(discord_user_id, []).append(tab)

    thread.start()

    await interaction.response.send_message(
        f"Đã tạo tab treo gmail cho <@{discord_user_id}>:\n"
        f"• Tài khoản: `{len(smtp_list)}`\n"
        f"• To: `{to_email}`\n"
        f"• Delay: `{delay}` giây\n"
        f"• Bắt đầu: `{start_time.strftime('%Y-%m-%d %H:%M:%S')}`",
        ephemeral=True
    )    
    
@tree.command(
    name="tabtreogmail",
    description="Quản lý/dừng tab treo gmail"
)
async def tabtreogmail(interaction: discord.Interaction):
    if not is_authorized(interaction) and not is_admin(interaction):
        return await interaction.response.send_message("Bạn không có quyền sử dụng bot", ephemeral=True)

    discord_user_id = str(interaction.user.id)
    with TREOGMAIL_LOCK:
        tabs = user_treogmail_tabs.get(discord_user_id, [])

    if not tabs:
        return await interaction.response.send_message("Bạn không có tab treo gmail nào đang hoạt động", ephemeral=True)

    msg = "**Danh sách tab treo gmail của bạn:**\n"
    for i, tab in enumerate(tabs, 1):
        up = datetime.now() - tab["start"]
        msg += (
            f"{i}. Accounts:`{len(tab['smtp_list'])}` → `{tab['to_email']}` | "
            f"Delay:`{tab['delay']}`s | Up:`{str(up).split('.')[0]}`\n"
        )
    msg += f"\nNhập số tab để dừng tab"

    await interaction.response.send_message(msg, ephemeral=True)

    def check(m: discord.Message):
        return m.author.id==interaction.user.id and m.channel.id==interaction.channel.id

    try:
        reply = await bot.wait_for("message", check=check, timeout=30.0)
    except asyncio.TimeoutError:
        return await interaction.followup.send("Hết thời gian. Không dừng tab nào", ephemeral=True)

    c = reply.content.strip()
    if not c.isdigit():
        return await interaction.followup.send("Không dừng tab nào", ephemeral=True)
    idx = int(c)
    if not (1<=idx<=len(tabs)):
        return await interaction.followup.send("Số không hợp lệ", ephemeral=True)

    with TREOGMAIL_LOCK:
        tab = tabs.pop(idx-1)
        tab["stop_event"].set()
        if not tabs:
            user_treogmail_tabs.pop(discord_user_id, None)

    return await interaction.followup.send(f"Đã dừng tab số {idx}", ephemeral=True)

@tree.command(name="menu", description="Hiển thị danh sách chức năng của bot")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 MENU BOT",
        description="Bot by **Gia Bảo** - Zalo Admin: `0944716595`",
        color=0x00ff99
    )

    embed.add_field(
        name="💬 Messenger",
        value="1. Treo ngôn\n2. Nhây réo tên",
        inline=False
    )
    embed.add_field(
        name="🎮 Discord",
        value="1. Treo ngôn\n2. Nhây tag fake",
        inline=False
    )
    embed.add_field(
        name="📱 Telegram",
        value="1. Treo ngôn kèm ảnh",
        inline=False
    )
    embed.add_field(
        name="📧 Gmail",
        value="1. Treo spam Gmail",
        inline=False
    )
    embed.add_field(
        name="📸 Instagram",
        value="1. Treo spam Instagram",
        inline=False
    )

    embed.set_footer(text="Sử dụng slash command để truy cập từng chức năng")

    await interaction.response.send_message(embed=embed, ephemeral=True)
                
bot.run(TOKEN)