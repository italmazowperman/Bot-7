import os
import logging
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    JobQueue
)
from telegram.constants import ParseMode
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен бота
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_CHAT_IDS = os.getenv('ADMIN_CHAT_IDS', '').split(',')

if not TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN не найден!")
    exit(1)

logger.info(f"✅ Токен бота получен: {TOKEN[:10]}...")

# Подключение к Supabase
def get_db_connection():
    """Создать соединение с Supabase"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            database_url = "postgresql://postgres.neypmeacztdapjfrnzgu:margiana0011@aws-1-eu-north-1.pooler.supabase.com:6543/postgres"
        
        conn = psycopg2.connect(
            database_url,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к базе данных: {e}")
        return None

# Команды бота
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"👤 Пользователь {user.id} ({user.first_name}) начал работу с ботом")
    
    welcome_text = f"""
🎉 *Добро пожаловать, {user.first_name}!*

🤖 Я — телеграм-бот для логистической компании *Margiana Logistic Services*.

*📋 Доступные команды:*
/start - Начать работу
/help - Помощь по командам
/active - Активные заказы
/today - События сегодня
/search - Поиск заказов
/contacts - Контакты компании

*🔍 Примеры использования:*
`/search ORD-001`
`/active`
`/today`

📞 *Техническая поддержка:* @margiana_logistics
🕒 *Время работы:* Пн-Пт 9:00-18:00
"""
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📊 Активные"), KeyboardButton("📅 Сегодня")],
            [KeyboardButton("🔍 Поиск"), KeyboardButton("📞 Контакты")],
            [KeyboardButton("🆘 Помощь")]
        ], resize_keyboard=True, one_time_keyboard=False)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать справку по командам"""
    help_text = """
*🆘 Помощь по командам*

*📋 Основные команды:*
/start - Начать работу с ботом
/active - Показать активные заказы
/today - События на сегодня
/search <текст> - Поиск заказов
/contacts - Контакты компании

*🔍 Примеры использования:*
`/search ORD-001` - найти заказ по номеру
`/search Клиент` - найти заказы клиента
`/active` - показать все активные заказы
`/today` - показать события на сегодня

*🔔 Уведомления:*
Бот автоматически отправляет уведомления о:
• Создании новых заказов
• Изменении статусов заказов
• Ключевых событиях (отплытие, прибытие и т.д.)
• Предстоящих событиях (за 24 часа)

*📞 Контакты для поддержки:*
@margiana_logistics
+993 61 55 77 79
"""
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def active_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать активные заказы из базы данных"""
    try:
        conn = get_db_connection()
        if not conn:
            await update.message.reply_text("❌ Ошибка подключения к базе данных")
            return
        
        cursor = conn.cursor()
        
        # Получаем активные заказы (статус не "Completed" и не "Cancelled")
        cursor.execute("""
            SELECT * FROM orders 
            WHERE status NOT IN ('Completed', 'Cancelled')
            ORDER BY creation_date DESC 
            LIMIT 20
        """)
        
        orders = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not orders:
            await update.message.reply_text("📭 Нет активных заказов")
            return
        
        text = f"📊 *Активные заказы* ({len(orders)}):\n\n"
        
        for i, order in enumerate(orders, 1):
            status_emoji = "🟢" if order['status'] == 'New' else "🟡" if 'Progress' in order['status'] else "🔵"
            
            text += f"{i}. {status_emoji} *{order['order_number']}*\n"
            text += f"   👤 {order['client_name']}\n"
            
            if order['container_count']:
                text += f"   📦 Контейнеров: {order['container_count']}\n"
            
            if order['route']:
                text += f"   📍 {order['route']}\n"
            
            text += f"   📝 *{order['status']}*\n"
            
            if order['eta_date']:
                eta = order['eta_date']
                if isinstance(eta, str):
                    try:
                        eta = datetime.fromisoformat(eta.replace('Z', '+00:00'))
                    except:
                        eta = None
                
                if eta and isinstance(eta, datetime):
                    days_left = (eta - datetime.now()).days
                    if days_left > 0:
                        text += f"   ⏳ ETA: {eta.strftime('%d.%m.%Y')} (через {days_left} дн.)\n"
            
            text += "\n"
        
        # Добавляем статистику
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM orders WHERE status NOT IN ('Completed', 'Cancelled')")
        total_active = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM orders")
        total_orders = cursor.fetchone()['total']
        
        cursor.close()
        conn.close()
        
        text += f"📈 *Статистика:* {total_active} активных из {total_orders} заказов"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в active_command: {e}")
        await update.message.reply_text(
            "❌ Ошибка при получении данных из базы. Пожалуйста, попробуйте позже."
        )

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """События на сегодня"""
    try:
        today = datetime.now().date()
        
        conn = get_db_connection()
        if not conn:
            await update.message.reply_text("❌ Ошибка подключения к базе данных")
            return
        
        cursor = conn.cursor()
        
        # Ищем заказы с событиями сегодня
        cursor.execute("""
            SELECT order_number, client_name, status,
                   departure_date, arrival_iran_date,
                   truck_loading_date, arrival_turkmenistan_date,
                   client_receiving_date, eta_date
            FROM orders
            WHERE (
                DATE(departure_date) = %s OR
                DATE(arrival_iran_date) = %s OR
                DATE(truck_loading_date) = %s OR
                DATE(arrival_turkmenistan_date) = %s OR
                DATE(client_receiving_date) = %s OR
                DATE(eta_date) = %s
            )
            LIMIT 10
        """, (today, today, today, today, today, today))
        
        orders = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not orders:
            await update.message.reply_text(
                "📅 На сегодня нет запланированных событий.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = f"📅 *События сегодня* ({len(orders)}):\n\n"
        
        for order in orders:
            text += f"📦 *{order['order_number']}*\n"
            text += f"👤 {order['client_name']}\n"
            
            events = []
            
            # Проверяем каждую дату
            if order['departure_date'] and order['departure_date'].date() == today:
                events.append("🚢 Отплытие из Китая")
            
            if order['arrival_iran_date'] and order['arrival_iran_date'].date() == today:
                events.append("🇮🇷 Прибытие в Иран")
            
            if order['truck_loading_date'] and order['truck_loading_date'].date() == today:
                events.append("🚛 Погрузка на грузовик")
            
            if order['arrival_turkmenistan_date'] and order['arrival_turkmenistan_date'].date() == today:
                events.append("🇹🇲 Прибытие в Туркменистан")
            
            if order['client_receiving_date'] and order['client_receiving_date'].date() == today:
                events.append("✅ Получение клиентом")
            
            if order['eta_date'] and order['eta_date'].date() == today:
                events.append("⏳ Ожидаемое прибытие (ETA)")
            
            for event in events:
                text += f"   • {event}\n"
            
            text += "\n"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в today_command: {e}")
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
            "`/search ORD-001` - поиск по номеру заказа\n"
            "`/search Туркмен` - поиск по имени клиента\n"
            "`/search Shanghai` - поиск по маршруту\n"
            "`/search New` - поиск по статусу",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    search_query = ' '.join(context.args)
    
    try:
        conn = get_db_connection()
        if not conn:
            await update.message.reply_text("❌ Ошибка подключения к базе данных")
            return
        
        cursor = conn.cursor()
        
        # Ищем по номеру заказа, имени клиента, маршруту или статусу
        cursor.execute("""
            SELECT * FROM orders 
            WHERE 
                order_number ILIKE %s OR
                client_name ILIKE %s OR
                route ILIKE %s OR
                status ILIKE %s OR
                goods_type ILIKE %s
            ORDER BY creation_date DESC 
            LIMIT 15
        """, (
            f"%{search_query}%",
            f"%{search_query}%",
            f"%{search_query}%",
            f"%{search_query}%",
            f"%{search_query}%"
        ))
        
        orders = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not orders:
            await update.message.reply_text(
                f"🔍 По запросу '*{search_query}*' ничего не найдено.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = f"🔍 *Результаты поиска* ('{search_query}'):\n\n"
        
        for i, order in enumerate(orders, 1):
            status_emoji = "🟢" if order['status'] == 'New' else "🟡" if 'Progress' in order['status'] else "🔵"
            
            text += f"{i}. {status_emoji} *{order['order_number']}*\n"
            text += f"   👤 {order['client_name']}\n"
            
            if order['container_count']:
                text += f"   📦 {order['container_count']} контейнеров\n"
            
            if order['route']:
                text += f"   📍 {order['route']}\n"
            
            text += f"   📝 {order['status']}\n\n"
        
        text += f"*Найдено заказов:* {len(orders)}"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в search_command: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при поиске: {str(e)}"
        )

async def contacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Контакты компании"""
    contacts_text = """
*🏢 Margiana Logistic Services*

*📍 Контакты:*
📞 Телефон: +993 61 55 77 79
📧 Email: perman@margianalogistics.com
📱 Telegram: @margiana_logistics
🌐 Сайт: margianalogistics.com

*🕒 Режим работы:*
Понедельник - Пятница: 9:00 - 18:00
Суббота: 10:00 - 16:00
Воскресенье: выходной

*🚚 Наши услуги:*
• Международные перевозки (Китай → Иран → Туркменистан)
• Таможенное оформление в 3-х странах
• Логистическое сопровождение грузов
• Страхование грузов
• Складские услуги

*🌍 Основные маршруты:*
→ Китай (Shanghai, Ningbo, Guangzhou) → Иран → Туркменистан
→ Россия → Туркменистан
→ Европа → Средняя Азия

*💼 Для клиентов:*
Мы обеспечиваем полное сопровождение груза от двери до двери, 
включая все формальности и документацию.
"""
    
    await update.message.reply_text(
        contacts_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений (кнопки)"""
    text = update.message.text
    
    if text == "📊 Активные":
        await active_command(update, context)
    elif text == "📅 Сегодня":
        await today_command(update, context)
    elif text == "🔍 Поиск":
        await update.message.reply_text(
            "Введите текст для поиска (например, номер заказа или имя клиента):\n"
            "Или используйте команду /search <текст>"
        )
    elif text == "📞 Контакты":
        await contacts_command(update, context)
    elif text == "🆘 Помощь":
        await help_command(update, context)
    else:
        await update.message.reply_text(
            f"Вы написали: {text}\n\n"
            "Используйте кнопки ниже или команды:\n"
            "/start - меню\n"
            "/help - помощь\n"
            "/active - активные заказы"
        )

# Функция для проверки новых заказов и отправки уведомлений
async def check_new_orders(context: ContextTypes.DEFAULT_TYPE):
    """Проверяет новые заказы и отправляет уведомления"""
    try:
        logger.info("🔍 Проверка новых заказов...")
        
        conn = get_db_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        # Ищем заказы, созданные за последние 5 минут
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        
        cursor.execute("""
            SELECT * FROM orders 
            WHERE sync_timestamp >= %s
            ORDER BY sync_timestamp DESC
            LIMIT 10
        """, (five_minutes_ago,))
        
        new_orders = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if new_orders:
            for order in new_orders:
                # Формируем сообщение об уведомлении
                notification_text = f"""
🆕 *НОВЫЙ ЗАКАЗ СИНХРОНИЗИРОВАН*

📦 *Заказ:* {order['order_number']}
👤 *Клиент:* {order['client_name']}
📦 *Контейнеров:* {order['container_count']}
📍 *Маршрут:* {order['route'] or 'Не указан'}
📝 *Статус:* {order['status']}
📅 *Создан:* {order['creation_date'].strftime('%d.%m.%Y %H:%M') if order['creation_date'] else 'Не указана'}

🔄 *Синхронизировано:* {order['sync_timestamp'].strftime('%d.%m.%Y %H:%M') if order['sync_timestamp'] else 'Только что'}
"""
                
                # Отправляем уведомление администраторам
                for admin_id in ADMIN_CHAT_IDS:
                    if admin_id.strip():
                        try:
                            await context.bot.send_message(
                                chat_id=admin_id.strip(),
                                text=notification_text,
                                parse_mode=ParseMode.MARKDOWN
                            )
                            logger.info(f"✅ Уведомление отправлено администратору {admin_id}")
                        except Exception as e:
                            logger.error(f"❌ Ошибка отправки уведомления администратору {admin_id}: {e}")
        
        logger.info(f"✅ Проверка завершена. Найдено новых заказов: {len(new_orders)}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке новых заказов: {e}")

# Функция для проверки предстоящих событий
async def check_upcoming_events(context: ContextTypes.DEFAULT_TYPE):
    """Проверяет предстоящие события и отправляет уведомления"""
    try:
        logger.info("🔔 Проверка предстоящих событий...")
        
        conn = get_db_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        # События в ближайшие 24 часа
        tomorrow = datetime.now() + timedelta(hours=24)
        
        cursor.execute("""
            SELECT order_number, client_name,
                   departure_date, arrival_iran_date,
                   truck_loading_date, arrival_turkmenistan_date,
                   client_receiving_date, eta_date
            FROM orders
            WHERE status NOT IN ('Completed', 'Cancelled')
            AND (
                (departure_date BETWEEN NOW() AND %s) OR
                (arrival_iran_date BETWEEN NOW() AND %s) OR
                (truck_loading_date BETWEEN NOW() AND %s) OR
                (arrival_turkmenistan_date BETWEEN NOW() AND %s) OR
                (client_receiving_date BETWEEN NOW() AND %s) OR
                (eta_date BETWEEN NOW() AND %s)
            )
            LIMIT 10
        """, (tomorrow, tomorrow, tomorrow, tomorrow, tomorrow, tomorrow))
        
        upcoming_events = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if upcoming_events:
            for order in upcoming_events:
                # Определяем ближайшее событие
                events = []
                
                if order['departure_date'] and order['departure_date'] <= tomorrow:
                    events.append(("🚢 Отплытие из Китая", order['departure_date']))
                
                if order['arrival_iran_date'] and order['arrival_iran_date'] <= tomorrow:
                    events.append(("🇮🇷 Прибытие в Иран", order['arrival_iran_date']))
                
                if order['truck_loading_date'] and order['truck_loading_date'] <= tomorrow:
                    events.append(("🚛 Погрузка на грузовик", order['truck_loading_date']))
                
                if order['arrival_turkmenistan_date'] and order['arrival_turkmenistan_date'] <= tomorrow:
                    events.append(("🇹🇲 Прибытие в Туркменистан", order['arrival_turkmenistan_date']))
                
                if order['client_receiving_date'] and order['client_receiving_date'] <= tomorrow:
                    events.append(("✅ Получение клиентом", order['client_receiving_date']))
                
                if order['eta_date'] and order['eta_date'] <= tomorrow:
                    events.append(("⏳ Ожидаемое прибытие", order['eta_date']))
                
                # Сортируем по дате
                events.sort(key=lambda x: x[1])
                
                for event_name, event_date in events[:1]:  # Берем только ближайшее событие
                    hours_left = int((event_date - datetime.now()).total_seconds() / 3600)
                    
                    if hours_left <= 24 and hours_left > 0:
                        notification_text = f"""
🔔 *НАПОМИНАНИЕ О СОБЫТИИ*

📦 *Заказ:* {order['order_number']}
👤 *Клиент:* {order['client_name']}
📅 *Событие:* {event_name}
⏰ *Когда:* {event_date.strftime('%d.%m.%Y %H:%M')}
⏳ *Осталось:* {hours_left} часов

⚠️ *Не забудьте подготовиться к событию!*
"""
                        
                        # Отправляем уведомление администраторам
                        for admin_id in ADMIN_CHAT_IDS:
                            if admin_id.strip():
                                try:
                                    await context.bot.send_message(
                                        chat_id=admin_id.strip(),
                                        text=notification_text,
                                        parse_mode=ParseMode.MARKDOWN
                                    )
                                    logger.info(f"✅ Напоминание отправлено администратору {admin_id}")
                                except Exception as e:
                                    logger.error(f"❌ Ошибка отправки напоминания администратору {admin_id}: {e}")
        
        logger.info(f"✅ Проверка событий завершена. Найдено: {len(upcoming_events)}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке событий: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"❌ Ошибка: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )

async def post_init(application: Application):
    """Функция, вызываемая после инициализации бота"""
    logger.info("🤖 Бот успешно инициализирован!")
    
    # Запускаем задачи для проверки уведомлений
    job_queue = application.job_queue
    
    if job_queue:
        # Проверка новых заказов каждые 5 минут
        job_queue.run_repeating(check_new_orders, interval=300, first=10)
        
        # Проверка предстоящих событий каждый час
        job_queue.run_repeating(check_upcoming_events, interval=3600, first=30)
        
        logger.info("✅ Задачи уведомлений запланированы")

def main():
    """Основная функция запуска бота"""
    logger.info("🚀 Запуск телеграм-бота...")
    
    try:
        # Создаем приложение с JobQueue
        application = Application.builder().token(TOKEN).post_init(post_init).build()
        
        # Регистрируем обработчики команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("active", active_command))
        application.add_handler(CommandHandler("today", today_command))
        application.add_handler(CommandHandler("search", search_command))
        application.add_handler(CommandHandler("contacts", contacts_command))
        
        # Регистрируем обработчик текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        # Регистрируем обработчик ошибок
        application.add_error_handler(error_handler)
        
        # Запускаем бота
        logger.info("✅ Бот запущен и ожидает сообщений...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True  # Игнорируем старые сообщения при перезапуске
        )
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске бота: {e}")
        raise

if __name__ == '__main__':
    main()
