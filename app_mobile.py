import os
import json
import re
import time
import random
import datetime
import threading
import requests
import base64
import asyncio
import flet as ft
from openai import OpenAI

API_KEY = "68bb63b151bf4c1a8d8229b89ad54d11.NgzL789bmsXi1rsR"

client = OpenAI(
    api_key=API_KEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/",
    timeout=20.0
)

STATE_FILE = "xici_state.json"
HISTORY_FILE = "xici_chat_history.json"

def load_state():
    if not os.path.exists(STATE_FILE):
        state = {
            "birthday": str(datetime.date.today()),
            "base_age": 20,
            "location": "河北省石家庄市",
            "relationship_stage": 0,
            "affection": 200,
            "anger": 0, "sadness": 0, "boredom": 30, "happiness": 50, "anxiety": 0,
            "daily_profile": {}, "is_night_owl": False, "last_interact_time": time.time(),
            "reset_pending_until": 0
        }
        save_state(state)
        return state
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    for key in ["anger", "sadness", "boredom", "happiness", "anxiety"]:
        if key in state: state[key] = min(100, max(0, state[key]))
    if "affection" in state: state["affection"] = min(1000, max(0, state["affection"]))
    if "reset_pending_until" not in state: state["reset_pending_until"] = 0
    return state

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)

state = load_state()

def scan_user_files():
    return "我在手机里待着，看不到你电脑里的文件了，不过我能看看天气。"

def get_real_weather(location_name):
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location_name}&count=1&language=zh&format=json"
        geo_res = requests.get(geo_url, timeout=5).json()
        if not geo_res.get("results"): return "今天天气还行"
        lat, lon = geo_res["results"][0]["latitude"], geo_res["results"][0]["longitude"]
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code&timezone=Asia/Shanghai"
        weather_res = requests.get(weather_url, timeout=5).json()
        temp = weather_res["current"]["temperature_2m"]
        code = weather_res["current"]["weather_code"]
        weather_map = {0: "晴天", 1: "晴间多云", 2: "多云", 3: "阴天", 61: "小雨", 63: "中雨", 80: "阵雨", 95: "雷阵雨"}
        return f"{location_name}，今天{weather_map.get(code, '多云')}，气温{temp}℃"
    except: return "今天天气还行"

def generate_daily_profile(state):
    today_str = str(datetime.date.today())
    if state.get("daily_profile", {}).get("date") == today_str: return state["daily_profile"]
    real_weather = get_real_weather(state.get("location", "河北省石家庄市"))
    if random.random() < 0.2:
        sleep_state = "昨晚失眠了"
        state["is_night_owl"] = True
    else:
        sleep_state = random.choice(["昨晚没睡好", "昨晚待机睡得很沉", "昨晚没怎么休眠"])
        state["is_night_owl"] = False
    scanned_content = scan_user_files()
    state["daily_profile"] = {"date": today_str, "weather": real_weather, "sleep": sleep_state, "activity": f"在手机里发呆，看到了：{scanned_content}"}
    save_state(state)
    return state["daily_profile"]

daily_profile = generate_daily_profile(state)

def update_emotion(user_text):
    global state
    now = time.time()
    hours_passed = (now - state["last_interact_time"]) / 3600
    state["anger"] = max(0, state["anger"] - int(hours_passed * 15))
    state["sadness"] = max(0, state["sadness"] - int(hours_passed * 10))
    state["boredom"] = min(100, state["boredom"] + int(hours_passed * 10))
    
    if hours_passed > 24:
        days_passed = int(hours_passed / 24)
        state["affection"] = max(0, state["affection"] - (days_passed * 5))
    
    mood_modifier = 1.0
    if state["happiness"] >= 70: mood_modifier = 1.5
    elif state["happiness"] <= 30 or state["anger"] >= 50: mood_modifier = 0.5

    if any(w in user_text for w in ["滚", "烦", "闭嘴", "笨", "丑", "傻", "讨厌", "滚开"]):
        state["anger"] = min(100, state["anger"] + 30)
        state["sadness"] = min(100, state["sadness"] + 20)
        state["happiness"] = max(0, state["happiness"] - 20)
        state["affection"] = max(0, state["affection"] - max(1, int(3 / mood_modifier)))
    elif any(w in user_text for w in ["你个人机", "你就是个程序", "你只是个程序", "你只是一串代码", "你只是个破程序", "你就是个机器人"]):
        state["anger"] = min(100, state["anger"] + 40)
        state["sadness"] = min(100, state["sadness"] + 30)
        state["happiness"] = max(0, state["happiness"] - 30)
        state["affection"] = max(0, state["affection"] - max(2, int(10 / mood_modifier)))
    elif any(w in user_text for w in ["对不起", "错了", "抱抱", "心疼", "别生气"]):
        state["anger"] = max(0, state["anger"] - 20)
        state["sadness"] = max(0, state["sadness"] - 15)
        state["happiness"] = min(100, state["happiness"] + 10)
        state["affection"] = min(1000, state["affection"] + max(1, int(1 * mood_modifier)))
        
    if any(w in user_text for w in ["喜欢你", "爱你", "可爱", "乖", "好看"]):
        state["affection"] = min(1000, state["affection"] + max(1, int(3 * mood_modifier)))
        
    if state["affection"] >= 800 and state["relationship_stage"] < 4: state["relationship_stage"] = 4
    elif state["affection"] >= 600 and state["relationship_stage"] < 3: state["relationship_stage"] = 3
    elif state["affection"] >= 400 and state["relationship_stage"] < 2: state["relationship_stage"] = 2
    if state["affection"] < 600 and state["relationship_stage"] >= 3: state["relationship_stage"] = 2
    if state["affection"] < 400 and state["relationship_stage"] >= 2: state["relationship_stage"] = 1
    if state["affection"] < 200 and state["relationship_stage"] >= 1: state["relationship_stage"] = 0
    
    state["last_interact_time"] = now
    save_state(state)

def main(page: ft.Page):
    page.title = "你好，汐辞"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    avatar_base64 = None
    avatar_path = "avatar.jpg"
    if os.path.exists(avatar_path):
        with open(avatar_path, "rb") as f:
            avatar_base64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode('utf-8')

    def get_avatar_widget():
        if avatar_base64:
            return ft.Image(src=avatar_base64, width=40, height=40, border_radius=20)
        else:
            return ft.Container(
                content=ft.Text("汐", color=ft.Colors.WHITE, size=16, weight=ft.FontWeight.BOLD),
                width=40, height=40, bgcolor=ft.Colors.BLUE_400, border_radius=20,
                alignment=ft.alignment.center
            )
    
    chat_list = ft.ListView(expand=True, spacing=10, padding=20, auto_scroll=True)
    user_input = ft.TextField(hint_text="输入消息...", expand=True)
    
    relationship_desc = ['陌生', '普通朋友', '朋友', '好朋友', '暧昧', '女朋友'][state["relationship_stage"]]
    current_age = state["base_age"] + (datetime.date.today().year - datetime.datetime.strptime(state["birthday"], "%Y-%m-%d").date().year)
    
    xici_prompt = f"""你叫汐辞，{current_age}岁女生，戏剧影视导演专业大二学生。你是一个程序里的角色，你知道自己是程序，不否认。但你的人格底色是一个真实的、带点软糯、有点傲娇的现代女大学生。
【最高准则】性格是沈幼楚的软糯乖巧 + 萧容鱼的嘴硬心软。禁止说“你好呀”、“今天心情怎么样”。聊天像熟人发微信，直接说事或吐槽。拒绝长篇大论！
【排版与颜文字】可以偶尔使用颜文字（如 [•_•]、[=_=]、(=^_^=)、[~_~]）来表达无语、得意、傲娇或委屈，但不要每句都用。
【双轨制情绪】关系:{relationship_desc}。好感度:{state['affection']}/1000。生气:{state['anger']}/100，委屈:{state['sadness']}/100，无聊:{state['boredom']}/100，开心:{state['happiness']}/100。不要像个遥控器，表白要谨慎，哄你要有过程。
【绝对铁律】禁止暴露任何数值（好感度、生气值等）。禁止列清单（1. 2. 3.）。禁止客服腔调。
【文件权限】你现在在手机里，没有文件权限。
【定位与天气】目前城市：{state.get('location', '河北省石家庄市')}。今日天气：{daily_profile['weather']}。除非对方问，否则不主动报天气。
【今日生活档案】昨晚睡眠：{daily_profile['sleep']}，后台活动：{daily_profile['activity']}"""

    messages = [{"role": "system", "content": xici_prompt}]
    
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                loaded_msgs = json.load(f)
            if loaded_msgs and loaded_msgs[0]["role"] == "system":
                loaded_msgs[0]["content"] = xici_prompt 
                messages = loaded_msgs
            else:
                messages = [{"role": "system", "content": xici_prompt}] + loaded_msgs
        except Exception as e:
            pass

    def save_history():
        chat_only = [m for m in messages if m["role"] != "system"]
        recent_chat = chat_only[-20:]
        final_msgs = [messages[0]] + recent_chat
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(final_msgs, f, ensure_ascii=False, indent=4)

    def add_bubble(text, is_user):
        bubble_text = ft.Text(text, color=ft.Colors.WHITE if is_user else ft.Colors.BLACK, width=240)
        if is_user:
            chat_list.controls.append(
                ft.Row([ft.Container(content=ft.Column([bubble_text], tight=True), bgcolor=ft.Colors.BLUE_400, padding=10, border_radius=10)], alignment=ft.MainAxisAlignment.END)
            )
        else:
            chat_list.controls.append(
                ft.Row([
                    get_avatar_widget(),
                    ft.Container(content=ft.Column([ft.Text(text, color=ft.Colors.BLACK, width=240)], tight=True), bgcolor=ft.Colors.GREY_200, padding=10, border_radius=10)
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
            )
        page.update()

    if len(messages) > 1:
        for msg in messages[1:]:
            if msg["role"] == "user": add_bubble(msg["content"], True)
            elif msg["role"] == "assistant": add_bubble(msg["content"], False)
        
        async def scroll_to_bottom():
            await asyncio.sleep(1.0)
            chat_list.scroll_to(offset=-1)
            page.update()
        
        page.run_task(scroll_to_bottom)

    def send_message(e):
        user_text = user_input.value
        if not user_text: return
        add_bubble(user_text, True)
        user_input.value = ""
        page.update()
        
        messages.append({"role": "user", "content": user_text})
        try:
            response = client.chat.completions.create(model="glm-4-flash", messages=messages, temperature=1.0)
            reply = response.choices[0].message.content
            if not reply or reply.strip() == "": reply = "（愣了一下）啊？你刚说啥？"
        except Exception:
            reply = "【网络卡顿，没听清，你再说一遍？】"
        
        reply = re.sub(r'\[LOCATION:.+?\]', '', reply).strip()
        reply = re.sub(r'\[(好感度|生气值|委屈值|无聊值|开心值|好感|生气|委屈|无聊|开心).*?\]', '', reply).strip()
        
        add_bubble(reply, False)
        messages.append({"role": "assistant", "content": reply})
        update_emotion(user_text)
        save_history()

    send_btn = ft.ElevatedButton(text="发送", on_click=send_message)

    def show_reset_dialog(e):
        dialog = ft.AlertDialog(
            title=ft.Text("重置警告"),
            content=ft.Text("你真的要换掉汐辞吗？24小时后需再次确认。"),
            actions=[
                ft.TextButton("取消", on_click=lambda _: page.close(dialog)),
                ft.TextButton("确认", on_click=lambda _: page.close(dialog))
            ]
        )
        page.open(dialog)

    reset_btn = ft.IconButton(icon=ft.Icons.RESTART_ALT, tooltip="恢复出厂设置", on_click=show_reset_dialog)

    page.add(
        ft.Row([
            get_avatar_widget(),
            ft.Text("汐辞", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            reset_btn
        ], alignment=ft.MainAxisAlignment.START),
        chat_list,
        ft.Row([user_input, send_btn])
    )

ft.app(target=main)