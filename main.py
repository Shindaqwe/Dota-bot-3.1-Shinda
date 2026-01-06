import os
import asyncio
import logging
import aiohttp
import json
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получаем токены из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
STEAM_API_KEY = os.getenv("STEAM_API_KEY")

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не установлен!")
    exit(1)

if not STEAM_API_KEY:
    logger.warning("⚠️ STEAM_API_KEY не установлен")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Добавляем middleware
dp.middleware.setup(LoggingMiddleware())

# Функция для создания клавиатуры
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📊 Моя статистика")
    keyboard.add("🔍 Найти игрока", "📈 Мета герои")
    keyboard.add("🛠 Поддержка")
    return keyboard

@dp.message_handler(commands=['start', 'help'])
async def cmd_start(message: types.Message):
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
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.message_handler(lambda message: message.text == "📊 Моя статистика")
async def my_stats(message: types.Message):
    await message.answer(
        "📊 Для просмотра статистики отправьте ваш Steam ID или ссылку на профиль.\n\n"
        "Пример:\n"
        "• https://steamcommunity.com/id/username\n"
        "• 76561198012345678"
    )

@dp.message_handler(lambda message: message.text == "🔍 Найти игрока")
async def find_player(message: types.Message):
    await message.answer(
        "🔍 Введите Steam ID или ссылку на профиль любого игрока:\n\n"
        "Форматы:\n"
        "• https://steamcommunity.com/id/username\n"
        "• https://steamcommunity.com/profiles/7656119xxxxxxxx\n"
        "• 76561198012345678"
    )

@dp.message_handler(lambda message: message.text == "📈 Мета герои")
async def meta_heroes(message: types.Message):
    await message.answer("🔄 Получаю информацию о мета-героях...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.opendota.com/api/heroStats") as response:
                if response.status == 200:
                    heroes = await response.json()
                    
                    # Берем топ-5 героев по популярности
                    popular_heroes = []
                    for hero in heroes:
                        if hero.get('pick_rate', 0) > 0.5:  # Более 0.5% пиков
                            popular_heroes.append(hero)
                    
                    popular_heroes.sort(key=lambda x: x.get('pick_rate', 0), reverse=True)
                    
                    text = "🏆 Топ-5 популярных героев:\n\n"
                    for i, hero in enumerate(popular_heroes[:5], 1):
                        name = hero.get('localized_name', 'Неизвестно')
                        pick_rate = hero.get('pick_rate', 0)
                        win_rate = hero.get('win_rate', 0)
                        
                        text += f"{i}. {name}\n"
                        text += f"   📊 Пиков: {pick_rate:.1f}%\n"
                        text += f"   🏆 Винрейт: {win_rate:.1f}%\n\n"
                    
                    await message.answer(text)
                else:
                    await message.answer("❌ Не удалось получить данные о героях")
    except Exception as e:
        logger.error(f"Ошибка при получении меты: {e}")
        await message.answer("⚠️ Произошла ошибка при получении данных")

@dp.message_handler(lambda message: message.text == "🛠 Поддержка")
async def support(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("💰 Поддержать проект", url="https://www.donationalerts.com/r/shindaqwe"),
        types.InlineKeyboardButton("🤖 Помощник", url="https://t.me/DotaShindaHelper_bot")
    )
    
    text = (
        "💖 Поддержка проекта:\n\n"
        "Если тебе нравится бот и ты хочешь помочь в его развитии:\n\n"
        "💰 Финансовая помощь - помогает оплачивать сервера и дальнейшую разработку\n"
        "🤖 Помощник - бот для быстрых ответов на вопросы"
    )
    
    await message.answer(text, reply_markup=keyboard)

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def handle_steam_link(message: types.Message):
    """Обработка Steam ссылок"""
    text = message.text.strip()
    
    # Проверяем, похоже ли на Steam ID
    if 'steamcommunity.com' in text or text.isdigit() and len(text) in [17, 8, 9, 10]:
        await message.answer(f"🔍 Обрабатываю: {text[:50]}...\n\n⏳ Получаю данные с OpenDota...")
        
        try:
            # Извлекаем Steam ID из разных форматов
            steam_id = extract_steam_id(text)
            
            if steam_id:
                await get_player_stats(message, steam_id)
            else:
                await message.answer("❌ Не удалось распознать Steam ID. Проверьте формат.")
                
        except Exception as e:
            logger.error(f"Ошибка при обработке Steam ID: {e}")
            await message.answer("⚠️ Произошла ошибка при обработке запроса")
    else:
        await message.answer(
            "🤖 Используйте кнопки меню или отправьте Steam ID для получения статистики.\n\n"
            "Примеры Steam ID:\n"
            "• https://steamcommunity.com/id/username\n"
            "• https://steamcommunity.com/profiles/76561198012345678\n"
            "• 76561198012345678"
        )

def extract_steam_id(text):
    """Извлекает Steam ID из текста"""
    import re
    
    # Если это уже цифровой ID
    if text.isdigit():
        if len(text) == 17:  # SteamID64
            return text
        elif len(text) in [8, 9, 10]:  # Account ID
            # Конвертируем в SteamID64
            account_id = int(text)
            return str(account_id + 76561197960265728)
    
    # Если это URL
    if 'steamcommunity.com' in text:
        # Профиль по цифровому ID
        match = re.search(r'steamcommunity\.com/profiles/(\d+)', text)
        if match:
            return match.group(1)
        
        # Кастомный URL - для простоты пока не обрабатываем
        return None
    
    return text

async def get_player_stats(message, steam_id):
    """Получает статистику игрока"""
    try:
        async with aiohttp.ClientSession() as session:
            # Получаем основную информацию
            async with session.get(f"https://api.opendota.com/api/players/{steam_id}") as response:
                if response.status != 200:
                    await message.answer("❌ Игрок не найден или профиль скрыт")
                    return
                
                player_data = await response.json()
            
            # Получаем винрейт
            async with session.get(f"https://api.opendota.com/api/players/{steam_id}/wl") as wl_response:
                wl_data = await wl_response.json() if wl_response.status == 200 else {"win": 0, "lose": 0}
            
            # Получаем последние матчи
            async with session.get(f"https://api.opendota.com/api/players/{steam_id}/recentMatches") as matches_response:
                matches = await matches_response.json() if matches_response.status == 200 else []
            
            # Формируем ответ
            profile = player_data.get("profile", {})
            persona_name = profile.get("personaname", "Неизвестно")
            avatar = profile.get("avatarfull", "")
            mmr_estimate = player_data.get("mmr_estimate", {}).get("estimate", "Неизвестно")
            
            wins = wl_data.get("win", 0)
            losses = wl_data.get("lose", 0)
            total_matches = wins + losses
            win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
            
            text = f"👤 Игрок: {persona_name}\n"
            text += f"🎯 Примерный MMR: {mmr_estimate}\n\n"
            text += f"📊 Статистика:\n"
            text += f"🔥 Винрейт: {win_rate:.1f}% ({wins}W - {losses}L)\n\n"
            
            if matches:
                text += f"🎮 Последние {min(5, len(matches))} игр:\n"
                
                # Сначала получим имена героев
                hero_names = {}
                for match in matches[:5]:
                    hero_id = match.get("hero_id")
                    if hero_id and hero_id not in hero_names:
                        async with session.get(f"https://api.opendota.com/api/heroes/{hero_id}") as hero_response:
                            if hero_response.status == 200:
                                hero_data = await hero_response.json()
                                hero_names[hero_id] = hero_data.get("localized_name", f"Герой {hero_id}")
                
                for i, match in enumerate(matches[:5], 1):
                    player_slot = match.get("player_slot", 0)
                    radiant_win = match.get("radiant_win", False)
                    
                    # Определяем победу/поражение
                    if player_slot < 128:  # Radiant
                        win = radiant_win
                    else:  # Dire
                        win = not radiant_win
                    
                    hero_id = match.get("hero_id")
                    hero_name = hero_names.get(hero_id, f"Герой {hero_id}")
                    
                    kills = match.get("kills", 0)
                    deaths = match.get("deaths", 0)
                    assists = match.get("assists", 0)
                    duration = match.get("duration", 0)
                    
                    minutes = duration // 60
                    seconds = duration % 60
                    
                    text += f"{'✅' if win else '❌'} {hero_name}\n"
                    text += f"   📊 KDA: {kills}/{deaths}/{assists} | 🕒 {minutes}:{seconds:02d}\n"
                    
                    if i < min(5, len(matches)):
                        text += "----------------------------\n"
            
            # Добавляем аватар если есть
            if avatar:
                try:
                    await bot.send_photo(
                        message.chat.id,
                        avatar,
                        caption=text,
                        parse_mode="HTML"
                    )
                    return
                except:
                    pass  # Если не удалось отправить фото, отправляем только текст
            
            await message.answer(text)
            
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await message.answer("⚠️ Произошла ошибка при получении статистики")

if __name__ == '__main__':
    logger.info("🚀 Запуск DotaStats бота...")
    executor.start_polling(dp, skip_updates=True)
