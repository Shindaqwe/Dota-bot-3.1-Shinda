import os
import logging
import requests
import json
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup
)
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получаем конфигурацию
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
STEAM_API_KEY = os.getenv("STEAM_API_KEY")

# Проверяем конфигурацию
if not all([API_ID, API_HASH, BOT_TOKEN]):
    logger.error("❌ Не установлены все необходимые переменные окружения!")
    exit(1)

# Создаем клиент бота
app = Client(
    "dotastats_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Главное меню
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["📊 Моя статистика", "🔍 Найти игрока"],
            ["📈 Мета герои", "🛠 Поддержка"]
        ],
        resize_keyboard=True
    )

@app.on_message(filters.command(["start", "help"]))
async def start_command(client, message):
    welcome_text = (
        "Привет!👋\n"
        "Я бот анализатор матчей DotaStats\n"
        "Мой создатель @shindaqwe\n\n"
        "Отправь ссылку на свой Steam профиль для статистики.\n\n"
        "Форматы ссылок:\n"
        "• https://steamcommunity.com/id/username\n"
        "• https://steamcommunity.com/profiles/7656119xxxxxxxx\n"
        "• Просто SteamID (например: 76561198012345678)\n"
        "• Или Account ID (например: 12345678)"
    )
    
    await message.reply_text(welcome_text, reply_markup=get_main_keyboard())

@app.on_message(filters.regex("📊 Моя статистика"))
async def my_stats(client, message):
    await message.reply_text(
        "📊 Для просмотра статистики отправьте ваш Steam ID или ссылку на профиль.\n\n"
        "Пример:\n"
        "• https://steamcommunity.com/id/username\n"
        "• 76561198012345678"
    )

@app.on_message(filters.regex("🔍 Найти игрока"))
async def find_player(client, message):
    await message.reply_text(
        "🔍 Введите Steam ID или ссылку на профиль любого игрока:\n\n"
        "Форматы:\n"
        "• https://steamcommunity.com/id/username\n"
        "• https://steamcommunity.com/profiles/7656119xxxxxxxx\n"
        "• 76561198012345678"
    )

@app.on_message(filters.regex("📈 Мета герои"))
async def meta_heroes(client, message):
    await message.reply_text("🔄 Получаю информацию о мета-героях...")
    
    try:
        response = requests.get("https://api.opendota.com/api/heroStats")
        if response.status_code == 200:
            heroes = response.json()
            
            # Фильтруем и сортируем
            popular_heroes = [
                hero for hero in heroes 
                if hero.get('pick_rate', 0) > 0.5
            ]
            popular_heroes.sort(key=lambda x: x.get('pick_rate', 0), reverse=True)
            
            text = "🏆 Топ-5 популярных героев:\n\n"
            for i, hero in enumerate(popular_heroes[:5], 1):
                name = hero.get('localized_name', 'Неизвестно')
                pick_rate = hero.get('pick_rate', 0)
                win_rate = hero.get('win_rate', 0)
                
                text += f"{i}. {name}\n"
                text += f"   📊 Пиков: {pick_rate:.1f}%\n"
                text += f"   🏆 Винрейт: {win_rate:.1f}%\n\n"
            
            await message.reply_text(text)
        else:
            await message.reply_text("❌ Не удалось получить данные о героях")
    except Exception as e:
        logger.error(f"Ошибка при получении меты: {e}")
        await message.reply_text("⚠️ Произошла ошибка при получении данных")

@app.on_message(filters.regex("🛠 Поддержка"))
async def support(client, message):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💰 Поддержать проект", url="https://www.donationalerts.com/r/shindaqwe"),
                InlineKeyboardButton("🤖 Помощник", url="https://t.me/DotaShindaHelper_bot")
            ]
        ]
    )
    
    text = (
        "💖 Поддержка проекта:\n\n"
        "Если тебе нравится бот и ты хочешь помочь в его развитии:\n\n"
        "💰 Финансовая помощь - помогает оплачивать сервера и дальнейшую разработку\n"
        "🤖 Помощник - бот для быстрых ответов на вопросы"
    )
    
    await message.reply_text(text, reply_markup=keyboard)

@app.on_message(filters.text & ~filters.command(["start", "help"]))
async def handle_steam_link(client, message):
    """Обработка Steam ссылок"""
    text = message.text.strip()
    
    # Игнорируем кнопки меню
    if text in ["📊 Моя статистика", "🔍 Найти игрока", "📈 Мета герои", "🛠 Поддержка"]:
        return
    
    # Проверяем, похоже ли на Steam ID
    if 'steamcommunity.com' in text or (text.isdigit() and len(text) in [17, 8, 9, 10]):
        await message.reply_text(f"🔍 Обрабатываю запрос...\n\n⏳ Получаю данные...")
        
        try:
            # Получаем статистику
            stats = await get_player_stats_simple(text)
            await message.reply_text(stats, reply_markup=get_main_keyboard())
                
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await message.reply_text("⚠️ Произошла ошибка. Проверьте Steam ID и попробуйте снова.")
    else:
        await message.reply_text(
            "🤖 Отправьте Steam ID для получения статистики.\n\n"
            "Примеры:\n"
            "• https://steamcommunity.com/id/username\n"
            "• https://steamcommunity.com/profiles/76561198012345678\n"
            "• 76561198012345678",
            reply_markup=get_main_keyboard()
        )

def extract_steam_id_simple(text):
    """Простой извлечение Steam ID"""
    import re
    
    # Цифровой ID
    if text.isdigit():
        if len(text) == 17:  # SteamID64
            return text
        elif len(text) in [8, 9, 10]:  # Account ID
            account_id = int(text)
            return str(account_id + 76561197960265728)
    
    # URL
    if 'steamcommunity.com' in text:
        # Цифровой профиль
        match = re.search(r'steamcommunity\.com/profiles/(\d+)', text)
        if match:
            return match.group(1)
    
    return text

async def get_player_stats_simple(steam_input):
    """Простое получение статистики"""
    steam_id = extract_steam_id_simple(steam_input)
    
    if not steam_id or not steam_id.isdigit():
        return "❌ Неверный формат Steam ID"
    
    try:
        # Получаем основную информацию
        player_url = f"https://api.opendota.com/api/players/{steam_id}"
        player_response = requests.get(player_url, timeout=10)
        
        if player_response.status_code != 200:
            return "❌ Игрок не найден или профиль скрыт"
        
        player_data = player_response.json()
        
        # Получаем винрейт
        wl_url = f"https://api.opendota.com/api/players/{steam_id}/wl"
        wl_response = requests.get(wl_url, timeout=10)
        wl_data = wl_response.json() if wl_response.status_code == 200 else {"win": 0, "lose": 0}
        
        # Получаем последние матчи
        matches_url = f"https://api.opendota.com/api/players/{steam_id}/recentMatches"
        matches_response = requests.get(matches_url, timeout=10)
        matches = matches_response.json() if matches_response.status_code == 200 else []
        
        # Формируем ответ
        profile = player_data.get("profile", {})
        persona_name = profile.get("personaname", "Неизвестно")
        mmr_estimate = player_data.get("mmr_estimate", {}).get("estimate", "Неизвестно")
        
        wins = wl_data.get("win", 0)
        losses = wl_data.get("lose", 0)
        total_matches = wins + losses
        win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
        
        text = f"👤 Игрок: {persona_name}\n"
        text += f"🎯 MMR: ~{mmr_estimate}\n"
        text += f"🔥 Винрейт: {win_rate:.1f}% ({wins}W - {losses}L)\n\n"
        
        if matches:
            text += f"📊 Последние {min(5, len(matches))} игр:\n\n"
            
            for match in matches[:5]:
                player_slot = match.get("player_slot", 0)
                radiant_win = match.get("radiant_win", False)
                
                # Определяем победу/поражение
                if player_slot < 128:  # Radiant
                    win = radiant_win
                else:  # Dire
                    win = not radiant_win
                
                hero_id = match.get("hero_id", 0)
                kills = match.get("kills", 0)
                deaths = match.get("deaths", 0)
                assists = match.get("assists", 0)
                duration = match.get("duration", 0)
                
                minutes = duration // 60
                seconds = duration % 60
                
                # Получаем имя героя
                hero_name = f"Герой {hero_id}"
                try:
                    heroes_response = requests.get("https://api.opendota.com/api/heroes", timeout=5)
                    if heroes_response.status_code == 200:
                        heroes = heroes_response.json()
                        for hero in heroes:
                            if hero.get("id") == hero_id:
                                hero_name = hero.get("localized_name", f"Герой {hero_id}")
                                break
                except:
                    pass
                
                text += f"{'✅' if win else '❌'} | {hero_name}\n"
                text += f"📊 KDA: {kills}/{deaths}/{assists} | 🕒 {minutes}:{seconds:02d}\n"
                text += "----------------------------\n"
        
        return text
        
    except requests.exceptions.Timeout:
        return "⏱️ Таймаут при запросе к OpenDota. Попробуйте позже."
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return "⚠️ Произошла ошибка при получении статистики"

if __name__ == "__main__":
    logger.info("🚀 Запуск DotaStats бота на Pyrogram...")
    app.run()
