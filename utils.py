from datetime import datetime
from typing import Optional
from models import Order, OrderStatus

def format_date(date: Optional[datetime]) -> str:
    """Форматировать дату в читаемый вид"""
    if not date:
        return "-"
    return date.strftime('%d.%m.%Y')

def format_datetime(dt: Optional[datetime]) -> str:
    """Форматировать дату и время"""
    if not dt:
        return "-"
    return dt.strftime('%d.%m.%Y %H:%M')

def get_status_emoji(status: str) -> str:
    """Получить emoji для статуса"""
    emoji_map = {
        OrderStatus.NEW.value: "🆕",
        OrderStatus.IN_PROGRESS_CHN.value: "🏭",
        OrderStatus.IN_TRANSIT_CHN_IR.value: "🚢",
        OrderStatus.IN_PROGRESS_IR.value: "🏭",
        OrderStatus.IN_TRANSIT_IR_TKM.value: "🚛",
        OrderStatus.COMPLETED.value: "✅",
        OrderStatus.CANCELLED.value: "❌"
    }
    return emoji_map.get(status, "📋")

def format_order_info(order: Order) -> str:
    """Форматировать информацию о заказе"""
    emoji = get_status_emoji(order.status)
    
    text = f"""
{emoji} *ЗАКАЗ: {order.order_number}*

*Основная информация:*
👤 Клиент: {order.client_name}
📦 Контейнеров: {order.container_count}
⚖️ Вес: {order.total_weight:.0f} кг
📏 Объем: {order.total_volume:.1f} м³
📍 Маршрут: {order.route or '-'}
🏁 Транзитный порт: {order.transit_port or '-'}
📦 Груз: {order.goods_type or '-'}
📄 Документ: {order.document_number or '-'}

*Статус и даты:*
📝 Статус: {order.status}
📅 Создан: {format_date(order.creation_date)}
⏳ ETA: {format_date(order.eta_date)}

*Китайская сторона:*
🏢 Компания: {order.chinese_transport_company or '-'}
🚢 Отплытие: {format_date(order.departure_date)}

*Иранская сторона:*
🏢 Компания: {order.iranian_transport_company or '-'}
🏁 Прибытие: {format_date(order.arrival_iran_date)}
🚛 Погрузка: {format_date(order.truck_loading_date)}

*Туркменистан:*
🏁 Прибытие: {format_date(order.arrival_turkmenistan_date)}
✅ Получение: {format_date(order.client_receiving_date)}

*Документы:*
📷 Фото загрузки: {'✅' if order.has_loading_photo else '❌'}
💰 Местные сборы: {'✅' if order.has_local_charges else '❌'}
📠 TLX: {'✅' if order.has_tex else '❌'}

*Дополнительно:*
📅 AN: {format_date(order.arrival_notice_date)}
📅 TKM: {format_date(order.tkm_date)}
"""
    
    if order.notes:
        text += f"\n*Заметки:*\n{order.notes}\n"
    
    return text

def calculate_days_left(target_date: datetime) -> int:
    """Рассчитать количество дней до даты"""
    if not target_date:
        return 0
    
    delta = target_date - datetime.now()
    return max(0, delta.days)

def parse_date(date_str: str) -> Optional[datetime]:
    """Распарсить дату из строки"""
    formats = [
        '%d.%m.%Y',
        '%d.%m.%Y %H:%M',
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None

def validate_order_number(order_number: str) -> bool:
    """Проверить валидность номера заказа"""
    if not order_number:
        return False
    
    # Простая проверка: должен содержать буквы и цифры
    has_letters = any(c.isalpha() for c in order_number)
    has_digits = any(c.isdigit() for c in order_number)
    
    return has_letters and has_digits and len(order_number) >= 3

def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезать текст до максимальной длины"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def format_weight(weight: float) -> str:
    """Форматировать вес"""
    if weight >= 1000:
        return f"{weight/1000:.1f} т"
    return f"{weight:.0f} кг"

def format_volume(volume: float) -> str:
    """Форматировать объем"""
    return f"{volume:.1f} м³"