import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
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

# Инициализация менеджеров (упрощенная версия)
class SimpleDB:
    def __init__(self):
        self.orders = []
    
    def get_all_orders(self):
        return self.orders
    
    def get_order_by_number(self, order_number):
        for order in self.orders:
            if order.get('order_number') == order_number:
                return order
        return None

db = SimpleDB()

# Команда /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот логистической компании Margiana Logistic Services.

📋 *Доступные команды:*

*Основные команды:*
/active - Активные заказы
/search <текст> - Поиск заказов
/status <статус> - Заказы по статусу

*Контакты:*
/contacts - Контакты компании
/help - Помощь

💡 *Примеры:*
`/search ORD-001`
`/status In Progress CHN`
"""
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN
    )

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать помощь"""
    help_text = """
📋 *Доступные команды:*

*Основные:*
/start - Начать работу
/active - Активные заказы
/search [текст] - Поиск заказов
/status [статус] - Заказы по статусу

*Контакты:*
/contacts - Контакты компании

💡 *Примеры:*
`/status In Progress CHN`
`/search ORD-001`
"""
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )

# Команда /contacts
async def contacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Контакты компании"""
    contacts_text = """
🏢 *Margiana Logistic Services*

📞 Телефон: +993 61 55 77 79
📧 Email: perman@margianalogistics.com
📱 Telegram: @margiana_logistics

🌐 *Международная логистика и транспорт:*
• Китай → Туркменистан через Иран
• Морские перевозки
• Таможенное оформление
• Сопровождение грузов
"""
    
    await update.message.reply_text(
        contacts_text,
        parse_mode=ParseMode.MARKDOWN
    )

# Команда /active - активные заказы
async def active_orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать активные заказы"""
    try:
        orders = db.get_all_orders()
        
        if not orders:
            await update.message.reply_text("📭 Нет активных заказов.")
            return
        
        text = f"📊 *Активные заказы* ({len(orders)}):\n\n"
        for i, order in enumerate(orders[:10], 1):
            text += f"{i}. 📦 *{order.get('order_number', 'N/A')}*\n"
            text += f"   👤 {order.get('client_name', 'N/A')}\n"
            text += f"   📍 {order.get('route', 'N/A')}\n\n"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in active_orders_command: {e}")
        await update.message.reply_text("❌ Ошибка при получении данных.")

# Команда /search - поиск заказов
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск заказов"""
    if not context.args:
        await update.message.reply_text(
            "🔍 Использование: `/search <текст>`\n\n"
            "Примеры:\n"
            "`/search ORD-001`\n"
            "`/search Company A`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    search_text = ' '.join(context.args)
    try:
        orders = [order for order in db.get_all_orders() 
                 if search_text.lower() in str(order.get('order_number', '')).lower() or 
                    search_text.lower() in str(order.get('client_name', '')).lower()]
        
        if not orders:
            await update.message.reply_text(f"🔍 По запросу '{search_text}' ничего не найдено.")
            return
        
        text = f"🔍 *Результаты поиска* ('{search_text}'):\n\n"
        for i, order in enumerate(orders[:15], 1):
            text += f"{i}. 📦 *{order.get('order_number', 'N/A')}*\n"
            text += f"   👤 {order.get('client_name', 'N/A')}\n"
            text += f"   📍 {order.get('route', 'N/A')}\n\n"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in search_command: {e}")
        await update.message.reply_text("❌ Ошибка при поиске.")

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте позже."
        )

# Основная функция для запуска бота
async def main():
    """Запуск Telegram бота"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    
    # Создание приложения
    application = Application.builder().token(token).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("active", active_orders_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("contacts", contacts_command))
    
    # Регистрация обработчика ошибок
    application.add_error_handler(error_handler)
    
    logger.info("Запуск Telegram бота...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
