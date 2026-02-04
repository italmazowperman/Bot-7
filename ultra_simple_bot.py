import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен из переменных окружения
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} sent /start")
    await update.message.reply_text(
        "✅ Бот работает!\n"
        f"Ваш ID: {update.effective_user.id}\n"
        f"Имя: {update.effective_user.first_name}"
    )

def main():
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден!")
        return
    
    logger.info(f"🚀 Запуск бота с токеном: {TOKEN[:10]}...")
    
    try:
        # Создаем приложение
        app = Application.builder().token(TOKEN).build()
        
        # Добавляем только одну команду
        app.add_handler(CommandHandler("start", start))
        
        # Запускаем
        logger.info("✅ Бот запущен")
        app.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    main()
