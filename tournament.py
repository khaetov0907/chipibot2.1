# tournament_v3.3 — стабильная версия с красивым экспортом TXT
import os
import asyncio
import logging
from aiohttp import web
import json
import re
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile

# ========== НАСТРОЙКИ ==========
TOKEN = "8132715978:AAHztRVmUQsnXsNtQaOyS6yGAdicZY53Swk"  # <-- твой токен
ADMIN_ID = [6904742757, 1450296021]  # <-- список админов
DATA_FILE = Path("players.json")

# ----- ФИКТИВНЫЙ WEB-СЕРВЕР ДЛЯ RENDER -----
async def handle(request):
    return web.Response(text="Bot is alive ✅")

async def start_fake_server():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Fake server running on port {port}")
# ---------------------------------------------
# ========== ФАЙЛОВЫЕ ОПЕРАЦИИ ==========
def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ERROR] cannot read {DATA_FILE}: {e}", file=sys.stderr)
            return {"tournament_name": None, "tournament_active": False, "players": []}
    return {"tournament_name": None, "tournament_active": False, "players": []}

def save_data(data):
    try:
        DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] cannot write {DATA_FILE}: {e}", file=sys.stderr)

# ========== БОТ ==========
bot = Bot(token=TOKEN)
dp = Dispatcher()

def log(s: str):
    print(s)

# ========== ОБРАБОТЧИК ==========
# ========== ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ ==========
@dp.message()
async def main_handler(message: Message):
    try:
        user_id = message.from_user.id if message.from_user else None
        text_raw = (message.text or "") + " " + (message.caption or "")
        text = text_raw.strip()
        text_lower = text.lower()
        chat = message.chat
        log(f"[MSG] from={user_id} chat={chat.id} text={text!r}")

        data = load_data()

        # ===== Команды админа =====
        if text.startswith("/") and user_id in ADMIN_ID:

            # /start_tournament
            if text_lower.startswith("/start_tournament"):
                dp.tournament_name_wait = True
                await message.reply("🎯 Введите название нового турнира (просто текст, без /команд).")
                log("[ACTION] waiting for tournament name from admin")
                return

            # /stop_tournament
            if text_lower.startswith("/stop_tournament"):
                if not data.get("tournament_active"):
                    await message.reply("⚠️ Турнир уже остановлен.")
                    return
                data["tournament_active"] = False
                save_data(data)
                dp.tournament_name_wait = False
                await message.reply("🛑 Турнир остановлен. Новые участники не принимаются.")
                log("[ACTION] tournament stopped")
                return

            # /list
            if text_lower.startswith("/list"):
                players = data.get("players", [])
                name = data.get("tournament_name") or "Без названия"
                if not players:
                    await message.reply(f"📭 В турнире «{name}» пока нет участников.")
                else:
                    text_out = (
                        f"📋 Турнир: {name}\n"
                        + "\n".join([f"{i+1}. {p}" for i, p in enumerate(players)])
                    )
                    await message.reply(text_out)
                log("[ACTION] list shown")
                return

            # /add
            if text_lower.startswith("/add"):
                parts = text.split()
                if len(parts) < 2:
                    await message.reply("⚠️ Используй: /add @username")
                    return
                username = parts[1]
                if username not in data["players"]:
                    data["players"].append(username)
                    save_data(data)
                    await message.reply(f"✅ Добавлен: {username}")
                    log(f"[ACTION] added {username}")
                else:
                    await message.reply(f"⚠️ {username} уже есть в списке.")
                return

            # /remove
            if text_lower.startswith("/remove"):
                parts = text.split()
                if len(parts) < 2:
                    await message.reply("⚠️ Используй: /remove @username")
                    return
                username = parts[1]
                if username in data["players"]:
                    data["players"].remove(username)
                    save_data(data)
                    await message.reply(f"🗑 Удалён: {username}")
                    log(f"[ACTION] removed {username}")
                else:
                    await message.reply("⚠️ Такого участника нет.")
                return

    
                        # /clear
            if text_lower.startswith("/clear"):
                if not data.get("tournament_active"):
                    await message.reply("⚠️ Турнир остановлен. Очистка списка недоступна.")
                    log("[INFO] clear ignored — tournament inactive")
                    return

                data["players"] = []
                save_data(data)
                await message.reply("🧹 Список очищен.")
                log("[ACTION] cleared list")
                return
            
            
            # /export — красивый экспорт
            if text_lower.startswith("/export"):
                players = data.get("players", [])
                name = data.get("tournament_name", "Без названия")
                timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")

                lines = [
                    f"🏆 Турнир: {name}",
                    f"📅 Экспорт от: {timestamp}",
                    "",
                    "👥 Участники:",
                ]
                if players:
                    lines += [f"{i+1}. {p}" for i, p in enumerate(players)]
                else:
                    lines.append("— пока нет участников —")

                content = "\n".join(lines)
                export_path = Path("players.txt")
                export_path.write_text(content, encoding="utf-8")

                file = FSInputFile(str(export_path))
                await message.reply_document(document=file, caption="📄 Список участников турнира")
                log("[ACTION] exported TXT file")
                return

            # /status
            if text_lower.startswith("/status"):
                name = data.get("tournament_name", "Без названия")
                state = "🟢 Активен" if data.get("tournament_active") else "🔴 Остановлен"
                await message.reply(f"🏆 Турнир: {name}\nСтатус: {state}")
                return

            # /help
            if text_lower.startswith("/help"):
                await message.reply(
                    "📘 Команды (для админов):\n"
                    "/start_tournament — начать новый турнир\n"
                    "/stop_tournament — остановить турнир\n"
                    "/add @user — добавить участника\n"
                    "/remove @user — удалить участника\n"
                    "/list — показать список\n"
                    "/clear — очистить список\n"
                    "/export — скачать список\n"
                    "/status — состояние турнира"
                )
                return

            await message.reply("❓ Неизвестная команда. /help")
            return

        # ===== Название турнира =====
        if getattr(dp, "tournament_name_wait", False) and user_id in ADMIN_ID:
            if text.startswith("/"):
                await message.reply("⚠️ Введите название турнира без /команды.")
                return
            data["tournament_name"] = text
            data["players"] = []
            data["tournament_active"] = True
            save_data(data)
            dp.tournament_name_wait = False
            await message.reply(f"✅ Турнир «{text}» начат!\nОтправляйте юзернеймы (@username) в чат.")
            log(f"[ACTION] tournament started: {text}")
            return

        # ===== Добавление участников (в тексте или подписях к фото) =====
        if data.get("tournament_active"):
            usernames = re.findall(r"@\w+", text)
            if usernames:
                added = []
                for u in usernames:
                    if u not in data["players"]:
                        data["players"].append(u)
                        added.append(u)
                if added:
                    save_data(data)
                    await message.reply(f"✅ Добавлено: {', '.join(added)}")
                    log(f"[ACTION] users added: {added}")
            return

    except Exception as exc:
        import traceback
        traceback.print_exc()
        try:
            await message.reply("⚠️ Ошибка в обработке сообщения. Смотри логи на сервере.")
        except Exception:
            pass

# ========== ЗАПУСК ==========


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    log("🤖 Бот запущен...")

    # Запускаем фиктивный веб-сервер, чтобы Render не ругался
    asyncio.create_task(start_fake_server())

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

