import os
import logging
import json
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List
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

from database import DatabaseManager
from models import Order, Container, Task, OrderStatus
from pdf_generator import generate_order_pdf, generate_summary_pdf
from notification_service import NotificationService
from utils import format_date, get_status_emoji, format_order_info

# Создайте FastAPI приложение
app = FastAPI(title="Margiana Logistics API")

# Добавьте CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API ключ для аутентификации (используйте сложный ключ)
API_KEY = "margiana_sync_key_2024_secure"

# Функция для проверки API ключа
def verify_api_key(api_key: str = Header(...)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Эндпоинт для проверки связи
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Margiana Logistics API"}

# Эндпоинт для синхронизации заказа
@app.post("/api/sync/order")
async def sync_order(
    order_data: dict,
    api_key: str = Depends(verify_api_key)
):
    try:
        logger.info(f"Syncing order: {order_data.get('order_number')}")
        
        # Обновляем заказ в базе данных
        success = db.update_order_from_sync(order_data)
        
        if success:
            # Создаем уведомление
            order_number = order_data.get('order_number')
            notification_type = order_data.get('sync_type', 'update')
            
            message = f"""
🔄 *СИНХРОНИЗАЦИЯ: {notification_type.upper()}*

📦 Заказ: *{order_number}*
📝 Статус: {order_data.get('status', 'Updated')}
👤 Пользователь: Desktop App
📅 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

✅ Данные успешно синхронизированы с облаком.
"""
            
            # Отправляем уведомление админам
            admin_ids = os.getenv('ADMIN_CHAT_IDS', '').split(',')
            for chat_id in admin_ids:
                if chat_id.strip():
                    try:
                        await app.bot.send_message(
                            chat_id=chat_id.strip(),
                            text=message,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as e:
                        logger.error(f"Failed to send notification: {e}")
            
            return {"status": "success", "message": "Order synced"}
        else:
            return {"status": "error", "message": "Failed to sync order"}
            
    except Exception as e:
        logger.error(f"Error in sync_order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Эндпоинт для получения заказов
@app.get("/api/orders")
async def get_orders(
    status: str = None,
    limit: int = 100,
    api_key: str = Depends(verify_api_key)
):
    try:
        if status:
            orders = db.get_orders_by_status(status)
        else:
            orders = db.get_all_orders()
        
        # Конвертируем в словари
        orders_data = []
        for order in orders[:limit]:
            order_dict = {
                'id': order.id,
                'order_number': order.order_number,
                'client_name': order.client_name,
                'container_count': order.container_count,
                'status': order.status,
                'route': order.route,
                'creation_date': order.creation_date.isoformat() if order.creation_date else None,
                'eta_date': order.eta_date.isoformat() if order.eta_date else None,
                'total_weight': float(order.total_weight),
                'total_volume': float(order.total_volume),
                'has_loading_photo': order.has_loading_photo,
                'has_local_charges': order.has_local_charges,
                'has_tex': order.has_tex,
                'notes': order.notes
            }
            orders_data.append(order_dict)
        
        return {"status": "success", "count": len(orders_data), "orders": orders_data}
        
    except Exception as e:
        logger.error(f"Error in get_orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Эндпоинт для поиска заказов
@app.get("/api/orders/search")
async def search_orders(
    q: str,
    api_key: str = Depends(verify_api_key)
):
    try:
        orders = db.search_orders(q)
        
        orders_data = []
        for order in orders[:50]:
            order_dict = {
                'id': order.id,
                'order_number': order.order_number,
                'client_name': order.client_name,
                'status': order.status,
                'container_count': order.container_count,
                'route': order.route
            }
            orders_data.append(order_dict)
        
        return {"status": "success", "count": len(orders_data), "orders": orders_data}
        
    except Exception as e:
        logger.error(f"Error in search_orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Эндпоинт для статистики
@app.get("/api/statistics")
async def get_statistics(
    days: int = 30,
    api_key: str = Depends(verify_api_key)
):
    try:
        stats = db.get_statistics(days)
        return {"status": "success", "statistics": stats}
    except Exception as e:
        logger.error(f"Error in get_statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация менеджеров
db = DatabaseManager()
notification_service = NotificationService()

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
/completed - Завершенные заказы (30 дней)
/today - События сегодня
/upcoming - Предстоящие события
/status <статус> - Заказы по статусу
/search <текст> - Поиск заказов

*Отчеты:*
/report <номер_заказа> - PDF отчет по заказу
/summary - Сводный отчет (PDF)
/orders_without_photos - Заказы без фото загрузки
/orders_without_docs - Заказы без документов

*Уведомления:*
/subscribe - Подписаться на уведомления
/unsubscribe - Отписаться от уведомлений
/settings - Настройки уведомлений

*Помощь:*
/help - Показать это сообщение
/contacts - Контакты компании

💡 *Примеры:*
`/status In Transit CHN-IR`
`/search ORD-001`
`/report ORD-001`
"""
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📊 Активные заказы", callback_data="active_orders"),
            InlineKeyboardButton("📅 Сегодня", callback_data="today_events")
        ]])
    )

# Команда /active - активные заказы
async def active_orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать активные заказы"""
    try:
        orders = db.get_orders_by_statuses([
            OrderStatus.NEW,
            OrderStatus.IN_PROGRESS_CHN,
            OrderStatus.IN_TRANSIT_CHN_IR,
            OrderStatus.IN_PROGRESS_IR,
            OrderStatus.IN_TRANSIT_IR_TKM
        ])
        
        if not orders:
            await update.message.reply_text("📭 Нет активных заказов.")
            return
        
        text = f"📊 *Активные заказы* ({len(orders)}):\n\n"
        for i, order in enumerate(orders[:20], 1):  # Ограничиваем вывод
            text += f"{i}. {get_status_emoji(order.status)} *{order.order_number}*\n"
            text += f"   👤 {order.client_name}\n"
            text += f"   📦 Контейнеров: {order.container_count}\n"
            text += f"   📍 {order.route}\n"
            
            if order.eta_date:
                days_left = (order.eta_date - datetime.now()).days
                if days_left > 0:
                    text += f"   ⏳ ETA: {format_date(order.eta_date)} ({days_left} дн.)\n"
            
            text += f"   📝 {order.status}\n\n"
        
        if len(orders) > 20:
            text += f"\n_... и еще {len(orders) - 20} заказов_"
        
        keyboard = [
            [InlineKeyboardButton(f"📋 {order.order_number}", 
              callback_data=f"order_{order.id}") 
             for order in orders[:3]]
        ]
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        )
        
    except Exception as e:
        logger.error(f"Error in active_orders_command: {e}")
        await update.message.reply_text("❌ Ошибка при получении данных.")

# Команда /completed - завершенные заказы
async def completed_orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершенные заказы за последние 30 дней"""
    try:
        from_date = datetime.now() - timedelta(days=30)
        orders = db.get_completed_orders(from_date)
        
        if not orders:
            await update.message.reply_text("📭 Нет завершенных заказов за последние 30 дней.")
            return
        
        text = f"✅ *Завершенные заказы (30 дней)* ({len(orders)}):\n\n"
        for i, order in enumerate(orders[:15], 1):
            completed_date = order.client_receiving_date or order.updated_at
            text += f"{i}. *{order.order_number}* - {order.client_name}\n"
            text += f"   📅 {format_date(completed_date)}\n"
            text += f"   📦 Контейнеров: {order.container_count}\n"
            text += f"   ⚖️ Вес: {order.total_weight:.0f} кг\n\n"
        
        total_weight = sum(order.total_weight for order in orders)
        total_containers = sum(order.container_count for order in orders)
        
        text += f"📈 *Итого:* {total_containers} контейнеров, {total_weight:.0f} кг"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in completed_orders_command: {e}")
        await update.message.reply_text("❌ Ошибка при получении данных.")

# Команда /today - события сегодня
async def today_events_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """События на сегодня"""
    try:
        today = datetime.now().date()
        events = []
        
        # Заказы с событиями сегодня
        orders = db.get_orders_with_events_today()
        
        for order in orders:
            events_info = []
            
            # Проверяем каждую дату события
            if order.departure_date and order.departure_date.date() == today:
                events_info.append("🚢 Отплытие из Китая")
            
            if order.arrival_iran_date and order.arrival_iran_date.date() == today:
                events_info.append("🏁 Прибытие в Иран")
            
            if order.truck_loading_date and order.truck_loading_date.date() == today:
                events_info.append("🚛 Погрузка на грузовик")
            
            if order.arrival_turkmenistan_date and order.arrival_turkmenistan_date.date() == today:
                events_info.append("🏁 Прибытие в Туркменистан")
            
            if order.client_receiving_date and order.client_receiving_date.date() == today:
                events_info.append("✅ Получение клиентом")
            
            if events_info:
                events.append({
                    'order': order,
                    'events': events_info
                })
        
        if not events:
            await update.message.reply_text(
                "📅 На сегодня нет запланированных событий.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📋 Активные заказы", callback_data="active_orders"),
                    InlineKeyboardButton("⏳ Предстоящие", callback_data="upcoming_events")
                ]])
            )
            return
        
        text = f"📅 *События сегодня* ({len(events)}):\n\n"
        for event in events:
            order = event['order']
            text += f"📦 *{order.order_number}*\n"
            text += f"👤 {order.client_name}\n"
            for ev in event['events']:
                text += f"   {ev}\n"
            text += "\n"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 Все активные", callback_data="active_orders"),
                InlineKeyboardButton("📅 Календарь", callback_data="calendar_view")
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error in today_events_command: {e}")
        await update.message.reply_text("❌ Ошибка при получении данных.")

# Команда /upcoming - предстоящие события
async def upcoming_events_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Предстоящие события (ближайшие 7 дней)"""
    try:
        from_date = datetime.now()
        to_date = datetime.now() + timedelta(days=7)
        events = db.get_upcoming_events(from_date, to_date)
        
        if not events:
            await update.message.reply_text(
                "📭 Нет предстоящих событий на ближайшие 7 дней.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📅 Сегодня", callback_data="today_events"),
                    InlineKeyboardButton("📋 Активные", callback_data="active_orders")
                ]])
            )
            return
        
        # Группируем события по дням
        events_by_day = {}
        for event in events:
            day = event['date'].strftime('%d.%m.%Y')
            if day not in events_by_day:
                events_by_day[day] = []
            events_by_day[day].append(event)
        
        text = "⏳ *Предстоящие события (7 дней):*\n\n"
        
        for day, day_events in sorted(events_by_day.items()):
            text += f"📅 *{day}*:\n"
            for event in day_events:
                text += f"   • {event['order_number']} - {event['event_type']}\n"
            text += "\n"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📅 Сегодня", callback_data="today_events"),
                InlineKeyboardButton("📋 Все заказы", callback_data="all_orders")
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error in upcoming_events_command: {e}")
        await update.message.reply_text("❌ Ошибка при получении данных.")

# Команда /status - заказы по статусу
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Заказы по определенному статусу"""
    if not context.args:
        status_options = [
            ["New", "In Progress CHN"],
            ["In Transit CHN-IR", "In Progress IR"],
            ["In Transit IR-TKM", "Completed"],
            ["Cancelled", "Все статусы"]
        ]
        
        keyboard = [
            [InlineKeyboardButton(status, callback_data=f"status_{status}") 
             for status in row]
            for row in status_options
        ]
        
        await update.message.reply_text(
            "📋 Выберите статус для фильтрации:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    status = ' '.join(context.args)
    await show_orders_by_status(update, status)

async def show_orders_by_status(update: Update, status: str):
    """Показать заказы по статусу"""
    try:
        if status == "Все статусы":
            orders = db.get_all_orders()
            status_text = "всех статусов"
        else:
            orders = db.get_orders_by_status(status)
            status_text = status
        
        if not orders:
            await update.message.reply_text(f"📭 Нет заказов со статусом '{status}'.")
            return
        
        text = f"📋 *Заказы ({status_text})* ({len(orders)}):\n\n"
        for i, order in enumerate(orders[:10], 1):
            text += f"{i}. {get_status_emoji(order.status)} *{order.order_number}*\n"
            text += f"   👤 {order.client_name}\n"
            text += f"   📦 {order.container_count} контейнеров\n"
            
            if order.eta_date:
                eta_str = format_date(order.eta_date)
                text += f"   ⏳ ETA: {eta_str}\n"
            
            text += f"   📍 {order.route}\n\n"
        
        if len(orders) > 10:
            text += f"\n_... и еще {len(orders) - 10} заказов_"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in show_orders_by_status: {e}")
        await update.message.reply_text("❌ Ошибка при получении данных.")

# Команда /search - поиск заказов
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск заказов"""
    if not context.args:
        await update.message.reply_text(
            "🔍 Использование: `/search <текст>`\n\n"
            "Примеры:\n"
            "`/search ORD-001`\n"
            "`/search Company A`\n"
            "`/search Shanghai`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    search_text = ' '.join(context.args)
    try:
        orders = db.search_orders(search_text)
        
        if not orders:
            await update.message.reply_text(f"🔍 По запросу '{search_text}' ничего не найдено.")
            return
        
        text = f"🔍 *Результаты поиска* ('{search_text}'):\n\n"
        for i, order in enumerate(orders[:15], 1):
            text += f"{i}. {get_status_emoji(order.status)} *{order.order_number}*\n"
            text += f"   👤 {order.client_name}\n"
            text += f"   📦 {order.container_count} контейнеров\n"
            text += f"   📍 {order.route}\n"
            text += f"   📝 {order.status}\n\n"
        
        if len(orders) > 15:
            text += f"\n_... и еще {len(orders) - 15} заказов_"
        
        keyboard = []
        for order in orders[:3]:
            keyboard.append([
                InlineKeyboardButton(
                    f"📋 {order.order_number}", 
                    callback_data=f"order_{order.id}"
                )
            ])
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        )
        
    except Exception as e:
        logger.error(f"Error in search_command: {e}")
        await update.message.reply_text("❌ Ошибка при поиске.")

# Команда /report - отчет по заказу в PDF
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерация PDF отчета по заказу"""
    if not context.args:
        await update.message.reply_text(
            "📄 Использование: `/report <номер_заказа>`\n\n"
            "Пример: `/report ORD-001`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    order_number = context.args[0]
    try:
        order = db.get_order_by_number(order_number)
        if not order:
            await update.message.reply_text(f"❌ Заказ '{order_number}' не найден.")
            return
        
        # Генерируем PDF
        pdf_bytes = generate_order_pdf(order)
        
        # Отправляем PDF
        await update.message.reply_document(
            document=pdf_bytes,
            filename=f"{order.order_number}_report.pdf",
            caption=f"📄 Отчет по заказу {order.order_number}\n"
                   f"👤 {order.client_name}\n"
                   f"📦 {order.container_count} контейнеров\n"
                   f"📝 {order.status}"
        )
        
    except Exception as e:
        logger.error(f"Error in report_command: {e}")
        await update.message.reply_text(f"❌ Ошибка при генерации отчета: {str(e)}")

# Команда /summary - сводный отчет
async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сводный отчет по всем заказам"""
    try:
        # Параметры отчета
        days_back = 30
        if context.args:
            try:
                days_back = int(context.args[0])
            except:
                pass
        
        # Генерируем PDF
        pdf_bytes = generate_summary_pdf(days_back)
        
        # Отправляем PDF
        await update.message.reply_document(
            document=pdf_bytes,
            filename=f"summary_report_{datetime.now().strftime('%Y%m%d')}.pdf",
            caption=f"📊 Сводный отчет за {days_back} дней\n"
                   f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
    except Exception as e:
        logger.error(f"Error in summary_command: {e}")
        await update.message.reply_text("❌ Ошибка при генерации отчета.")

# Команда /orders_without_photos - заказы без фото
async def orders_without_photos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Заказы без фото загрузки"""
    try:
        orders = db.get_orders_without_photos()
        
        if not orders:
            await update.message.reply_text("✅ Все заказы имеют фото загрузки!")
            return
        
        text = f"📷 *Заказы без фото загрузки* ({len(orders)}):\n\n"
        for i, order in enumerate(orders[:15], 1):
            text += f"{i}. *{order.order_number}* - {order.client_name}\n"
            text += f"   📦 {order.container_count} контейнеров\n"
            text += f"   📍 {order.route}\n"
            text += f"   📝 {order.status}\n\n"
        
        if len(orders) > 15:
            text += f"\n_... и еще {len(orders) - 15} заказов_"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in orders_without_photos_command: {e}")
        await update.message.reply_text("❌ Ошибка при получении данных.")

# Команда /orders_without_docs - заказы без документов
async def orders_without_docs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Заказы без необходимых документов"""
    try:
        orders = db.get_orders_without_documents()
        
        if not orders:
            await update.message.reply_text("✅ Все заказы имеют необходимые документы!")
            return
        
        text = "📋 *Заказы без документов:*\n\n"
        
        # Группируем по типу недостающего документа
        no_local_charges = [o for o in orders if not o.has_local_charges]
        no_tex = [o for o in orders if not o.has_tex]
        
        if no_local_charges:
            text += "📄 *Без местных сборов:*\n"
            for i, order in enumerate(no_local_charges[:10], 1):
                text += f"{i}. {order.order_number} - {order.client_name}\n"
        
        if no_tex:
            text += "\n📄 *Без TLX:*\n"
            for i, order in enumerate(no_tex[:10], 1):
                text += f"{i}. {order.order_number} - {order.client_name}\n"
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in orders_without_docs_command: {e}")
        await update.message.reply_text("❌ Ошибка при получении данных.")

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать помощь"""
    help_text = """
📋 *Доступные команды:*

*Основные:*
/start - Начать работу
/active - Активные заказы
/completed - Завершенные заказы (30 дней)
/today - События сегодня
/upcoming - Предстоящие события (7 дней)
/status [статус] - Заказы по статусу
/search [текст] - Поиск заказов

*Отчеты:*
/report [номер] - PDF отчет по заказу
/summary [дней] - Сводный PDF отчет
/orders_without_photos - Без фото загрузки
/orders_without_docs - Без документов

*Уведомления:*
/subscribe - Подписаться
/unsubscribe - Отписаться
/settings - Настройки

*Контакты:*
/contacts - Контакты компании

💡 *Примеры:*
`/status In Progress CHN`
`/search ORD-001`
`/report ORD-001`
`/summary 30`
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

📍 *Маршруты:*
Shanghai → Vladivostok → Moscow
Guangzhou → Helsinki → St. Petersburg
и другие
"""
    
    await update.message.reply_text(
        contacts_text,
        parse_mode=ParseMode.MARKDOWN
    )

# Обработчик callback-запросов
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("status_"):
        status = data.replace("status_", "")
        await show_orders_by_status(update, status)
    
    elif data == "active_orders":
        await active_orders_command(update, context)
    
    elif data == "today_events":
        await today_events_command(update, context)
    
    elif data == "upcoming_events":
        await upcoming_events_command(update, context)
    
    elif data.startswith("order_"):
        order_id = int(data.replace("order_", ""))
        order = db.get_order_by_id(order_id)
        if order:
            await send_order_details(query.message, order)
    
    elif data == "calendar_view":
        await upcoming_events_command(update, context)

async def send_order_details(message, order):
    """Отправить детали заказа"""
    text = format_order_info(order)
    
    keyboard = [
        [InlineKeyboardButton("📄 PDF отчет", callback_data=f"pdf_{order.id}")],
        [InlineKeyboardButton("📅 События", callback_data=f"events_{order.id}")],
        [InlineKeyboardButton("📦 Контейнеры", callback_data=f"containers_{order.id}")]
    ]
    
    await message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте позже."
        )

# Функция проверки и отправки уведомлений
async def check_and_send_notifications(context: ContextTypes.DEFAULT_TYPE):
    """Проверка и отправка уведомлений о событиях"""
    try:
        notifications = notification_service.get_upcoming_notifications()
        
        for notification in notifications:
            chat_id = notification['chat_id']
            message = notification['message']
            
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
                notification_service.mark_notification_sent(notification['id'])
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
    
    except Exception as e:
        logger.error(f"Error in check_and_send_notifications: {e}")

# Основная функция
def main():
    """Запуск бота"""
    # Получение токена бота
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    
    # Создание приложения
    application = Application.builder().token(token).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("active", active_orders_command))
    application.add_handler(CommandHandler("completed", completed_orders_command))
    application.add_handler(CommandHandler("today", today_events_command))
    application.add_handler(CommandHandler("upcoming", upcoming_events_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("summary", summary_command))
    application.add_handler(CommandHandler("orders_without_photos", orders_without_photos_command))
    application.add_handler(CommandHandler("orders_without_docs", orders_without_docs_command))
    application.add_handler(CommandHandler("contacts", contacts_command))
    
    # Регистрация обработчика callback-запросов
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Регистрация обработчика ошибок
    application.add_error_handler(error_handler)
    
    # Настройка планировщика для проверки уведомлений
    job_queue = application.job_queue
    if job_queue:
        # Проверка каждые 15 минут
        job_queue.run_repeating(
            check_and_send_notifications,
            interval=900,  # 15 минут в секундах
            first=10
        )
    
    # Запуск бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
# В конец файла bot.py, перед main(), добавьте:

# Глобальная переменная для бота
bot_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск при старте
    global bot_instance
    bot_instance = application.bot
    
    # Запускаем бота в фоне
    bot_task = asyncio.create_task(application.run_polling())
    
    yield
    
    # Очистка при остановке
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        pass

# Обновите app с lifespan
app = FastAPI(lifespan=lifespan)
app.bot = None  # Будет установлен в lifespan

# В функции main() измените последние строки:
def main():
    """Запуск бота и API"""
    # Получение токена бота
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    
    # Создание приложения бота
    telegram_app = Application.builder().token(token).build()
    
    # Регистрация обработчиков команд (ваш существующий код)
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("help", help_command))
    # ... добавьте все ваши обработчики ...
    
    # Регистрация обработчика callback-запросов
    telegram_app.add_handler(CallbackQueryHandler(button_callback))
    
    # Регистрация обработчика ошибок
    telegram_app.add_error_handler(error_handler)
    
    # Сохраняем приложение в глобальной переменной
    application = telegram_app
    
    # Запускаем API сервер
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    
    logger.info(f"Запуск API сервера на порту {port}...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
    main()