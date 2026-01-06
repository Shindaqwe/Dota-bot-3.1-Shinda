import os
import re
import logging
import requests
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

if not STEAM_API_KEY:
    logger.warning("⚠️ STEAM_API_KEY не установлен, обработка пользовательских ссылок будет недоступна")

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

def resolve_vanity_url(vanity_name):
    """Использует Steam API для преобразования пользовательского URL в SteamID64"""
    if not STEAM_API_KEY:
        return None
    
    url = "http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/"
    params = {
        'key': STEAM_API_KEY,
        'vanityurl': vanity_name
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['response']['success'] == 1:
                return data['response']['steamid']
    except Exception as e:
        logger.error(f"Ошибка при разрешении vanity URL: {e}")
    
    return None

def extract_steam_id(steam_input):
    """Извлекает SteamID64 из различных форматов"""
    
    # 1. Цифровой SteamID64 (17 цифр)
    if steam_input.isdigit():
        if len(steam_input) == 17:
            return steam_input
        elif len(steam_input) in [8, 9, 10]:  # Account ID
            account_id = int(steam_input)
            return str(account_id + 76561197960265728)
    
    # 2. URL с цифровым ID
    profile_match = re.search(r'steamcommunity\.com/profiles/(\d+)', steam_input)
    if profile_match:
        return profile_match.group(1)
    
    # 3. Пользовательский URL (нужен Steam API)
    custom_match = re.search(r'steamcommunity\.com/id/([\w-]+)', steam_input)
    if custom_match:
        if not STEAM_API_KEY:
            return None
        return resolve_vanity_url(custom_match.group(1))
    
    return None

async def get_player_stats(steam_input):
    """Получает и форматирует статистику игрока"""
    steam_id = extract_steam_id(steam_input)
    
    if not steam_id:
        if 'steamcommunity.com/id/' in steam_input and not STEAM_API_KEY:
            return "❌ Не удалось обработать пользовательскую ссылку.\nДобавьте STEAM_API_KEY в переменные окружения."
        return "❌ Не удалось распознать Steam ID. Проверьте формат."
    
    try:
        # Получаем основную информацию
        player_url = f"https://api.opendota.com/api/players/{steam_id}"
        player_response = requests.get(player_url, timeout=10)
        
        if player_response.status_code != 200:
            return "❌ Игрок не найден или профиль скрыт (код: " + str(player_response.status_code) + ")"
        
        player_data = player_response.json()
        
        # Получаем винрейт
        wl_url = f"https://api.opendota.com/api/players/{steam_id}/wl"
        wl_response = requests.get(wl_url, timeout=10)
        wl_data = wl_response.json() if wl_response.status_code == 200 else {"win": 0, "lose": 0}
        
        # Получаем последние матчи
        matches_url = f"https://api.opendota.com/api/players/{steam_id}/recentMatches"
        matches_response = requests.get(matches_url, timeout=10)
        matches = matches_response.json() if matches_response.status_code == 200 else []
        
        # Форматируем ответ
        profile = player_data.get("profile", {})
        persona_name = profile.get("personaname", "Неизвестно")
        mmr_estimate = player_data.get("mmr_estimate", {}).get("estimate", "Неизвестно")
        
        wins = wl_data.get("win", 0)
        losses = wl_data.get("lose", 0)
        total_matches = wins + losses
        win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
        
        text = f"👤 Игрок: {persona_name}\n"
        text += f"🎯 Примерный MMR: {mmr_estimate}\n"
        text += f"🔥 Винрейт: {win_rate:.1f}% ({wins}W - {losses}L)\n\n"
        
        if matches:
            text += f"📊 Последние {min(5, len(matches))} игр:\n\n"
            
            # Получаем список всех героев один раз
            heroes_response = requests.get("https://api.opendota.com/api/heroes", timeout=5)
            heroes_map = {}
            if heroes_response.status_code == 200:
                heroes = heroes_response.json()
                heroes_map = {hero['id']: hero['localized_name'] for hero in heroes}
            
            for match in matches[:5]:
                player_slot = match.get("player_slot", 0)
                radiant_win = match.get("radiant_win", False)
                
                # Определяем победу/поражение
                if player_slot < 128:  # Radiant
                    win = radiant_win
                else:  # Dire
                    win = not radiant_win
                
                hero_id = match.get("hero_id", 0)
                hero_name = heroes_map.get(hero_id, f"Герой {hero_id}")
                
                kills = match.get("kills", 0)
                deaths = match.get("deaths", 0)
                assists = match.get("assists", 0)
                duration = match.get("duration", 0)
                
                minutes = duration // 60
                seconds = duration % 60
                
                text += f"{'✅' if win else '❌'} | {hero_name}\n"
                text += f"📊 KDA: {kills}/{deaths}/{assists} | 🕒 {minutes}:{seconds:02d}\n"
                text += "----------------------------\n"
        
        return text
        
    except requests.exceptions.Timeout:
        return "⏱️ Таймаут при запросе к OpenDota. Попробуйте позже."
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return "⚠️ Произошла ошибка при получении статистики"

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
        response = requests.get("https://api.opendota.com/api/heroStats", timeout=10)
        if response.status_code == 200:
            heroes = response.json()
            
            # Фильтруем героев с разумной популярностью (более 1% пиков)
            # pick_rate здесь уже в процентах (например, 5.12 для 5.12%)
            popular_heroes = [
                hero for hero in heroes 
                if hero.get('pick_rate', 0) > 1.0  # Исправлено: > 1% вместо > 0.5
            ]
            
            # Сортируем по популярности
            popular_heroes.sort(key=lambda x: x.get('pick_rate', 0), reverse=True)
            
            text = "🏆 Топ-5 популярных героев:\n\n"
            
            if not popular_heroes:
                # Если почему-то фильтр оставил пустой список, покажем топ-5 всех героев
                all_heroes_sorted = sorted(heroes, key=lambda x: x.get('pick_rate', 0), reverse=True)
                popular_heroes = all_heroes_sorted[:5]
                text = "🏆 Топ-5 героев по популярности:\n\n"
            
            for i, hero in enumerate(popular_heroes[:5], 1):
                name = hero.get('localized_name', 'Неизвестно')
                pick_rate = hero.get('pick_rate', 0)
                win_rate = hero.get('win_rate', 0)
                
                text += f"{i}. {name}\n"
                text += f"   📊 Пиков: {pick_rate:.1f}%\n"
                text += f"   🏆 Винрейт: {win_rate:.1f}%\n\n"
            
            await message.reply_text(text)
        else:
            await message.reply_text(f"❌ Не удалось получить данные о героях (код: {response.status_code})")
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
    if ('steamcommunity.com' in text) or (text.isdigit() and len(text) in [17, 8, 9, 10]):
        await message.reply_text(f"🔍 Обрабатываю запрос...\n\n⏳ Получаю данные...")
        
        try:
            # Получаем статистику
            stats = await get_player_stats(text)
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

if __name__ == "__main__":
    logger.info("🚀 Запуск DotaStats бота на Pyrogram...")
    app.run()
