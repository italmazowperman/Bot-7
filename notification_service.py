import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import create_engine, func, and_, or_
from sqlalchemy.orm import sessionmaker
from database import DatabaseManager
from models import Notification, Subscription, Base, Order

class NotificationService:
    """Сервис уведомлений"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.engine = create_engine(self.database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db_session = SessionLocal()
        
        # Создание таблиц если их нет
        Base.metadata.create_all(bind=self.engine)
        
        self.db_manager = DatabaseManager()
    
    def get_upcoming_notifications(self) -> List[Dict]:
        """Получить предстоящие уведомления"""
        try:
            now = datetime.now()
            future = now + timedelta(minutes=5)  # Проверяем на 5 минут вперед
            
            notifications = self.db_session.query(Notification).filter(
                and_(
                    Notification.scheduled_time >= now,
                    Notification.scheduled_time <= future,
                    Notification.sent == False
                )
            ).all()
            
            return [
                {
                    'id': n.id,
                    'chat_id': n.chat_id,
                    'message': n.message,
                    'scheduled_time': n.scheduled_time
                }
                for n in notifications
            ]
            
        except Exception as e:
            print(f"Error getting upcoming notifications: {e}")
            return []
    
    def mark_notification_sent(self, notification_id: int) -> bool:
        """Пометить уведомление как отправленное"""
        try:
            notification = self.db_session.query(Notification).filter(
                Notification.id == notification_id
            ).first()
            
            if notification:
                notification.sent = True
                self.db_session.commit()
                return True
            return False
            
        except Exception as e:
            print(f"Error marking notification as sent: {e}")
            self.db_session.rollback()
            return False
    
    def create_event_notification(self, order: Order, event_type: str, event_date: datetime) -> bool:
        """Создать уведомление о событии"""
        try:
            # Получаем всех подписчиков
            subscriptions = self.db_session.query(Subscription).filter(
                Subscription.is_active == True,
                Subscription.notify_events == True
            ).all()
            
            for subscription in subscriptions:
                message = self._format_event_message(order, event_type, event_date)
                
                notification = Notification(
                    chat_id=subscription.chat_id,
                    message=message,
                    notification_type='event',
                    scheduled_time=event_date,
                    sent=False
                )
                
                self.db_session.add(notification)
            
            self.db_session.commit()
            return True
            
        except Exception as e:
            print(f"Error creating event notification: {e}")
            self.db_session.rollback()
            return False
    
    def create_reminder_notification(self, order: Order, event_type: str, event_date: datetime) -> bool:
        """Создать напоминание о предстоящем событии"""
        try:
            # Получаем подписчиков с настройками напоминаний
            subscriptions = self.db_session.query(Subscription).filter(
                Subscription.is_active == True,
                Subscription.notify_reminders == True
            ).all()
            
            for subscription in subscriptions:
                # Рассчитываем время напоминания
                reminder_time = event_date - timedelta(hours=subscription.hours_before)
                
                # Создаем напоминание только если оно в будущем
                if reminder_time > datetime.now():
                    message = self._format_reminder_message(order, event_type, event_date, subscription.hours_before)
                    
                    notification = Notification(
                        chat_id=subscription.chat_id,
                        message=message,
                        notification_type='reminder',
                        scheduled_time=reminder_time,
                        sent=False
                    )
                    
                    self.db_session.add(notification)
            
            self.db_session.commit()
            return True
            
        except Exception as e:
            print(f"Error creating reminder notification: {e}")
            self.db_session.rollback()
            return False
    
    def create_alert_notification(self, order: Order, alert_type: str, alert_message: str) -> bool:
        """Создать оповещение об изменении статуса или проблеме"""
        try:
            subscriptions = self.db_session.query(Subscription).filter(
                Subscription.is_active == True,
                Subscription.notify_alerts == True
            ).all()
            
            for subscription in subscriptions:
                message = self._format_alert_message(order, alert_type, alert_message)
                
                notification = Notification(
                    chat_id=subscription.chat_id,
                    message=message,
                    notification_type='alert',
                    scheduled_time=datetime.now(),
                    sent=False
                )
                
                self.db_session.add(notification)
            
            self.db_session.commit()
            return True
            
        except Exception as e:
            print(f"Error creating alert notification: {e}")
            self.db_session.rollback()
            return False
    
    def subscribe_user(self, chat_id: str) -> bool:
        """Подписать пользователя на уведомления"""
        try:
            existing = self.db_session.query(Subscription).filter(
                Subscription.chat_id == chat_id
            ).first()
            
            if existing:
                existing.is_active = True
                existing.updated_at = datetime.now()
            else:
                subscription = Subscription(
                    chat_id=chat_id,
                    is_active=True,
                    notify_events=True,
                    notify_reminders=True,
                    notify_alerts=True,
                    hours_before=24
                )
                self.db_session.add(subscription)
            
            self.db_session.commit()
            return True
            
        except Exception as e:
            print(f"Error subscribing user: {e}")
            self.db_session.rollback()
            return False
    
    def unsubscribe_user(self, chat_id: str) -> bool:
        """Отписать пользователя от уведомлений"""
        try:
            subscription = self.db_session.query(Subscription).filter(
                Subscription.chat_id == chat_id
            ).first()
            
            if subscription:
                subscription.is_active = False
                subscription.updated_at = datetime.now()
                self.db_session.commit()
                return True
            
            return False
            
        except Exception as e:
            print(f"Error unsubscribing user: {e}")
            self.db_session.rollback()
            return False
    
    def get_user_settings(self, chat_id: str) -> Optional[Dict]:
        """Получить настройки пользователя"""
        try:
            subscription = self.db_session.query(Subscription).filter(
                Subscription.chat_id == chat_id
            ).first()
            
            if subscription:
                return {
                    'is_active': subscription.is_active,
                    'notify_events': subscription.notify_events,
                    'notify_reminders': subscription.notify_reminders,
                    'notify_alerts': subscription.notify_alerts,
                    'hours_before': subscription.hours_before
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting user settings: {e}")
            return None
    
    def update_user_settings(self, chat_id: str, settings: Dict) -> bool:
        """Обновить настройки пользователя"""
        try:
            subscription = self.db_session.query(Subscription).filter(
                Subscription.chat_id == chat_id
            ).first()
            
            if subscription:
                for key, value in settings.items():
                    if hasattr(subscription, key):
                        setattr(subscription, key, value)
                
                subscription.updated_at = datetime.now()
                self.db_session.commit()
                return True
            
            return False
            
        except Exception as e:
            print(f"Error updating user settings: {e}")
            self.db_session.rollback()
            return False
    
    def check_and_create_notifications(self):
        """Проверить и создать уведомления о предстоящих событиях"""
        try:
            # Проверяем события на ближайшие 48 часов
            from_date = datetime.now()
            to_date = datetime.now() + timedelta(hours=48)
            
            events = self.db_manager.get_upcoming_events(from_date, to_date)
            
            for event in events:
                order = self.db_manager.get_order_by_number(event['order_number'])
                if order:
                    # Создаем уведомление о событии
                    self.create_event_notification(order, event['event_type'], event['event_date'])
                    
                    # Создаем напоминание
                    self.create_reminder_notification(order, event['event_type'], event['event_date'])
            
            return True
            
        except Exception as e:
            print(f"Error checking and creating notifications: {e}")
            return False
    
    def _format_event_message(self, order: Order, event_type: str, event_date: datetime) -> str:
        """Форматировать сообщение о событии"""
        emoji = {
            'Отплытие из Китая': '🚢',
            'Прибытие в Иран': '🏁',
            'Погрузка на грузовик': '🚛',
            'Прибытие в Туркменистан': '🏁',
            'Получение клиентом': '✅'
        }.get(event_type, '📅')
        
        return f"""
{emoji} *СОБЫТИЕ: {event_type}*

📦 Заказ: *{order.order_number}*
👤 Клиент: {order.client_name}
📅 Дата: {event_date.strftime('%d.%m.%Y %H:%M')}
📍 Маршрут: {order.route}

🔄 Статус обновлен автоматически.
        """
    
    def _format_reminder_message(self, order: Order, event_type: str, event_date: datetime, hours_before: int) -> str:
        """Форматировать сообщение-напоминание"""
        emoji = {
            'Отплытие из Китая': '🚢',
            'Прибытие в Иран': '🏁',
            'Погрузка на грузовик': '🚛',
            'Прибытие в Туркменистан': '🏁',
            'Получение клиентом': '✅'
        }.get(event_type, '⏰')
        
        return f"""
{emoji} *НАПОМИНАНИЕ: {event_type}*

📦 Заказ: *{order.order_number}*
👤 Клиент: {order.client_name}
📅 Событие: {event_date.strftime('%d.%m.%Y %H:%M')}
⏳ Через: {hours_before} часов

📍 Маршрут: {order.route}
📦 Контейнеров: {order.container_count}

🔔 Не забудьте подготовиться к событию!
        """
    
    def _format_alert_message(self, order: Order, alert_type: str, alert_message: str) -> str:
        """Форматировать сообщение-оповещение"""
        emoji = {
            'status_change': '🔄',
            'problem': '⚠️',
            'update': '📝',
            'delay': '⏳'
        }.get(alert_type, '🔔')
        
        return f"""
{emoji} *ОПОВЕЩЕНИЕ: {alert_type.upper()}*

📦 Заказ: *{order.order_number}*
👤 Клиент: {order.client_name}

📝 Сообщение:
{alert_message}

📋 Текущий статус: {order.status}
        """
    
    def close(self):
        """Закрыть соединения"""
        try:
            self.db_session.close()
            self.db_manager.close()
        except:
            pass