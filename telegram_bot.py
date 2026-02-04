import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from telegram.constants import ParseMode

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Команды
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")
    
    welcome_text = f"""
👋 *Добро пожаловать, {user.first_name}!*

Я — телеграм-бот для логистической компании *Margiana Logistic Services*.

*Доступные команды:*
/start - Начать работу
/help - Помощь по командам
/active - Показать активные заказы
/search - Поиск заказов
/contacts - Контакты компании

*Примеры использования:*
`/search ORD-001`
`/active`

📞 *Техническая поддержка:* @margiana_logistics
"""
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📦 Активные заказы"), KeyboardButton("🔍 Поиск")],
            [KeyboardButton("📞 Контакты"), KeyboardButton("🆘 Помощь")]
        ], resize_keyboard=True)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать справку по командам"""
    help_text = """
*📋 Доступные команды:*

*Основные команды:*
/start - Начать работу с ботом
/active - Показать активные заказы
/search <текст> - Поиск заказов
/contacts - Контакты компании

*Примеры использования:*
`/search ORD-001` - найти заказ по номеру
`/search Клиент` - найти заказы клиента
`/active` - показать все активные заказы

*Для разработчиков WPF программы:*
API доступен по адресу: https://ваш-проект.railway.app/api/sync/order
Ключ API: margiana_sync_key_2024_secure_change_this
"""
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def active_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать активные заказы"""
    try:
        # Временная заглушка - покажем тестовые данные
        active_orders_text = """
*📊 Активные заказы:*

1. *ORD-2024-001*
   👤 Клиент: ООО "Туркмен Транс"
   📦 Контейнеров: 2
   📍 Маршрут: Shanghai → Bandar Abbas → Ashgabat
   📅 Статус: В пути CHN-IR
   ⏳ ETA: 15.02.2024

2. *ORD-2024-002*
   👤 Клиент: Азия Логистик
   📦 Контейнеров: 1
   📍 Маршрут: Ningbo → Vladivostok → Moscow
   📅 Статус: Погрузка в Китае
   ⏳ ETA: 20.02.2024

3. *ORD-2024-003*
   👤 Клиент: ТМ Транс
   📦 Контейнеров: 3
   📍 Маршрут: Guangzhou → Helsinki → St. Petersburg
   📅 Статус: Таможня Иран
   ⏳ ETA: 12.02.2024

*Всего активных заказов: 3*
"""
        
        await update.message.reply_text(
            active_orders_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in active_command: {e}")
        await update.message.reply_text(
            "❌ Ошибка при получении данных. Пожалуйста, попробуйте позже."
        )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск заказов"""
    if not context.args:
        await update.message.reply_text(
            "🔍 *Использование команды /search:*\n\n"
            "`/search <текст>`\n\n"
            "*Примеры:*\n"
            "`/search ORD-2024-001` - поиск по номеру заказа\n"
            "`/search Туркмен` - поиск по имени клиента\n"
            "`/search Shanghai` - поиск по маршруту",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    search_query = ' '.join(context.args)
    
    try:
        # Временная заглушка - покажем результат поиска
        if "ORD" in search_query.upper():
            result_text = f"""
*🔍 Результаты поиска по запросу: "{search_query}"*

*Найден заказ: ORD-2024-001*
👤 Клиент: ООО "Туркмен Транс"
📦 Контейнеров: 2
📍 Маршрут: Shanghai → Bandar Abbas → Ashgabat
📅 Статус: В пути CHN-IR
📅 Дата создания: 01.02.2024
⏳ ETA: 15.02.2024

*Контейнеры:*
1. TGHU-1234567 (20ft)
2. MSCU-7654321 (20ft)

*Контактная информация:*
📞 +993 61 55 77 79
📧 perman@margianalogistics.com
"""
        else:
            result_text = f"""
*🔍 Результаты поиска по запросу: "{search_query}"*

Найдено 2 заказа:

1. *ORD-2024-001* - ООО "Туркмен Транс"
   📦 2 контейнера, статус: В пути CHN-IR

2. *ORD-2024-004* - "Туркмен Карго"
   📦 1 контейнер, статус: Новый

*Итого: 2 заказа*
"""
        
        await update.message.reply_text(
            result_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in search_command: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при поиске: {str(e)}"
        )

async def contacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Контакты компании"""
    contacts_text = """
*🏢 Margiana Logistic Services*

*Контакты:*
📞 Телефон: +993 61 55 77 79
📧 Email: perman@margianalogistics.com
📱 Telegram: @margiana_logistics
🌐 Сайт: margianalogistics.com

*Режим работы:*
Понедельник - Пятница: 9:00 - 18:00
Суббота: 10:00 - 16:00
Воскресенье: выходной

*Наши услуги:*
• Международные перевозки
• Таможенное оформление
• Логистическое сопровождение
• Страхование грузов
• Складские услуги

*Основные маршруты:*
Китай → Иран → Туркменистан
Россия → Туркменистан
Европа → Средняя Азия
"""
    
    await update.message.reply_text(
        contacts_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    text = update.message.text
    
    if text == "📦 Активные заказы":
        await active_command(update, context)
    elif text == "🔍 Поиск":
        await update.message.reply_text(
            "Введите текст для поиска (например, номер заказа или имя клиента):"
        )
    elif text == "📞 Контакты":
        await contacts_command(update, context)
    elif text == "🆘 Помощь":
        await help_command(update, context)
    else:
        await update.message.reply_text(
            f"Вы написали: {text}\n\n"
            "Используйте команды из меню или введите /help для списка команд."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Ошибка: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )

def main():
    """Основная функция запуска бота"""
    # Получаем токен бота
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        return
    
    logger.info(f"Запуск бота с токеном: {TOKEN[:10]}...")
    
    try:
        # Создаем приложение
        application = Application.builder().token(TOKEN).build()
        
        # Регистрируем обработчики команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("active", active_command))
        application.add_handler(CommandHandler("search", search_command))
        application.add_handler(CommandHandler("contacts", contacts_command))
        
        # Регистрируем обработчик текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        # Регистрируем обработчик ошибок
        application.add_error_handler(error_handler)
        
        # Запускаем бота
        logger.info("Бот запущен и ожидает сообщений...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise

if __name__ == '__main__':
    main()
