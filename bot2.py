import json
import os
import requests
from dotenv import load_dotenv

# Автоматически загружаем переменные из файла .env в окружение
load_dotenv()

# Безопасное получение данных
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_LINK = os.getenv("CHANNEL_LINK")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")
MASTER_KEY = os.getenv("MASTER_KEY")

# Проверка, что токен загрузился
if not BOT_TOKEN:
    raise ValueError("ОШИБКА: BOT_TOKEN не найден в переменной окружения или файле .env!")

BASE_URL = f"https://telegram.org{BOT_TOKEN}"
offset = 0
user_lang = {}

def send(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        r = requests.post(f"{BASE_URL}/sendMessage", data=payload, timeout=10)
        print(f"[SEND] chat={chat_id} status={r.status_code} resp={r.text[:100]}")
    except Exception as e:
        print(f"[SEND ERROR] {e}")

def edit(chat_id, msg_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        r = requests.post(f"{BASE_URL}/editMessageText", data=payload, timeout=10)
        print(f"[EDIT] msg={msg_id} status={r.status_code} resp={r.text[:100]}")
    except Exception as e:
        print(f"[EDIT ERROR] {e}")

def answer(cb_id):
    try:
        requests.post(f"{BASE_URL}/answerCallbackQuery", data={"callback_query_id": cb_id}, timeout=5)
    except: 
        pass

def is_subscribed(uid):
    try:
        r = requests.post(f"{BASE_URL}/getChatMember", data={"chat_id": CHANNEL_ID, "user_id": uid}, timeout=10)
        data = r.json()
        status = data.get("result", {}).get("status", "")
        return status in ["member", "creator", "administrator"]
    except:
        return False

def get_lang(uid):
    return user_lang.get(uid, None)

def set_lang(uid, lang):
    user_lang[uid] = lang

def t(uid, key):
    lang = get_lang(uid) or "en"
    texts = {
        "ru": {
            "start": f"🔐 <b>BroodScript</b>\nПривет!\nПодпишись на канал {CHANNEL_LINK} и получи ключ.",
            "not_subscribed": f"❌ Ты не подписан!\n{CHANNEL_LINK}",
            "subscribed": f"✅ Подписка оформлена!\n🔑 <code>{PUBLIC_KEY}</code>",
            "copied": f"📋 Ключ: <code>{PUBLIC_KEY}</code>",
            "choose_lang": "Выбери язык / Choose language:",
            "btn_channel": "📢 Канал",
            "btn_check": "✅ Проверить подписку",
            "btn_get_key": "🔄 Получить ключ",
            "btn_copy": "📋 Копировать",
            "btn_subscribe": "📢 Подписаться"
        },
        "en": {
            "start": f"🔐 <b>BroodScript</b>\nHello!\nSubscribe to {CHANNEL_LINK} and get the key.",
            "not_subscribed": f"❌ Not subscribed!\n{CHANNEL_LINK}",
            "subscribed": f"✅ Subscribed!\n🔑 <code>{PUBLIC_KEY}</code>",
            "copied": f"📋 Key: <code>{PUBLIC_KEY}</code>",
            "choose_lang": "Choose language:",
            "btn_channel": "📢 Channel",
            "btn_check": "✅ Check Subscription",
            "btn_get_key": "🔄 Get Key",
            "btn_copy": "📋 Copy",
            "btn_subscribe": "📢 Subscribe"
        }
    }
    return texts[lang].get(key, key)

def process_message(msg):
    global offset
    txt = msg.get("text", "")
    chat_id = msg["chat"]["id"]
    uid = msg["from"]["id"]

    print(f"[MSG] uid={uid} text={txt}")

    if txt.startswith("/start"):
        lang = get_lang(uid)
        if lang is None:
            kb = {"inline_keyboard": [[{"text":"🇷🇺 Русский","callback_data":"lang_ru"},{"text":"🇺🇸 English","callback_data":"lang_en"}]]}
            send(chat_id, t(uid, "choose_lang"), kb)
        else:
            kb = {"inline_keyboard": [
                [{"text": t(uid, "btn_channel"), "url": CHANNEL_LINK}],
                [{"text": t(uid, "btn_check"), "callback_data": "check"}],
                [{"text": t(uid, "btn_get_key"), "callback_data": "get"}]
            ]}
            send(chat_id, t(uid, "start"), kb)

def process_callback(cb):
    global offset
    data = cb["data"]
    chat_id = cb["message"]["chat"]["id"]
    msg_id = cb["message"]["message_id"]
    uid = cb["from"]["id"]

    print(f"[CB] uid={uid} data={data}")

    answer(cb["id"])

    if data.startswith("lang_"):
        lang = data.split("_")[1]
        set_lang(uid, lang)
        send(chat_id, "🇷🇺 Русский" if lang=="ru" else "🇺🇸 English")
        kb = {"inline_keyboard": [
            [{"text": t(uid, "btn_channel"), "url": CHANNEL_LINK}],
            [{"text": t(uid, "btn_check"), "callback_data": "check"}],
            [{"text": t(uid, "btn_get_key"), "callback_data": "get"}]
        ]}
        send(chat_id, t(uid, "start"), kb)

    elif data in ("check", "get"):
        if not is_subscribed(uid):
            kb = {"inline_keyboard": [
                [{"text": t(uid, "btn_subscribe"), "url": CHANNEL_LINK}],
                [{"text": t(uid, "btn_check"), "callback_data": "check"}]
            ]}
            edit(chat_id, msg_id, t(uid, "not_subscribed"), kb)
        else:
            kb = {"inline_keyboard": [[{"text": t(uid, "btn_copy"), "callback_data": "copy"}]]}
            edit(chat_id, msg_id, t(uid, "subscribed"), kb)

    elif data == "copy":
        edit(chat_id, msg_id, t(uid, "copied"))

def main():
    global offset
    print(f"🤖 Minimal bot started. Key: {PUBLIC_KEY}")
    while True:
        try:
            r = requests.get(f"{BASE_URL}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            updates = r.json().get("result", [])
            for upd in updates:
                offset = upd["update_id"] + 1
                if "message" in upd and "text" in upd["message"]:
                    process_message(upd["message"])
                elif "callback_query" in upd:
                    process_callback(upd["callback_query"])
        except Exception as e:
            print(f"[LOOP ERROR] {e}")

if __name__ == "__main__":
    main()