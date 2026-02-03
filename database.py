import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, func, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import psycopg2
from psycopg2.extras import RealDictCursor

from models import Base, Order, Container, Task, OrderStatus

class DatabaseManager:
    """Менеджер базы данных для работы с заказами"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL не найден в переменных окружения")
        
        # Для PostgreSQL используем psycopg2 напрямую для простоты
        self.conn = psycopg2.connect(self.database_url)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        # Инициализация SQLAlchemy для сложных запросов
        self.engine = create_engine(self.database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db_session = SessionLocal()
        
        # Создание таблиц если их нет
        Base.metadata.create_all(bind=self.engine)
    
    def get_all_orders(self) -> List[Order]:
        """Получить все заказы"""
        try:
            return self.db_session.query(Order).order_by(Order.created_at.desc()).all()
        except SQLAlchemyError as e:
            print(f"Error getting all orders: {e}")
            return []
    
    def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Получить заказ по ID"""
        try:
            return self.db_session.query(Order).filter(Order.id == order_id).first()
        except SQLAlchemyError as e:
            print(f"Error getting order by id: {e}")
            return None
    
    def get_order_by_number(self, order_number: str) -> Optional[Order]:
        """Получить заказ по номеру"""
        try:
            return self.db_session.query(Order).filter(
                Order.order_number == order_number
            ).first()
        except SQLAlchemyError as e:
            print(f"Error getting order by number: {e}")
            return None
    
    def get_orders_by_status(self, status: str) -> List[Order]:
        """Получить заказы по статусу"""
        try:
            return self.db_session.query(Order).filter(
                Order.status == status
            ).order_by(Order.created_at.desc()).all()
        except SQLAlchemyError as e:
            print(f"Error getting orders by status: {e}")
            return []
    
    def get_orders_by_statuses(self, statuses: List[str]) -> List[Order]:
        """Получить заказы по нескольким статусам"""
        try:
            return self.db_session.query(Order).filter(
                Order.status.in_(statuses)
            ).order_by(Order.created_at.desc()).all()
        except SQLAlchemyError as e:
            print(f"Error getting orders by statuses: {e}")
            return []
    
    def get_active_orders(self) -> List[Order]:
        """Получить активные заказы"""
        active_statuses = [
            OrderStatus.NEW,
            OrderStatus.IN_PROGRESS_CHN,
            OrderStatus.IN_TRANSIT_CHN_IR,
            OrderStatus.IN_PROGRESS_IR,
            OrderStatus.IN_TRANSIT_IR_TKM
        ]
        return self.get_orders_by_statuses(active_statuses)
    
    def get_completed_orders(self, from_date: datetime) -> List[Order]:
        """Получить завершенные заказы с даты"""
        try:
            return self.db_session.query(Order).filter(
                Order.status == OrderStatus.COMPLETED,
                Order.updated_at >= from_date
            ).order_by(Order.updated_at.desc()).all()
        except SQLAlchemyError as e:
            print(f"Error getting completed orders: {e}")
            return []
    
    def get_orders_with_events_today(self) -> List[Order]:
        """Получить заказы с событиями сегодня"""
        today = datetime.now().date()
        
        try:
            return self.db_session.query(Order).filter(
                or_(
                    func.date(Order.departure_date) == today,
                    func.date(Order.arrival_iran_date) == today,
                    func.date(Order.truck_loading_date) == today,
                    func.date(Order.arrival_turkmenistan_date) == today,
                    func.date(Order.client_receiving_date) == today
                )
            ).all()
        except SQLAlchemyError as e:
            print(f"Error getting orders with events today: {e}")
            return []
    
    def get_upcoming_events(self, from_date: datetime, to_date: datetime) -> List[Dict]:
        """Получить предстоящие события"""
        try:
            # Создаем UNION запрос для всех дат событий
            query = """
            SELECT 
                order_number,
                'Отплытие из Китая' as event_type,
                departure_date as event_date
            FROM orders 
            WHERE departure_date BETWEEN %s AND %s
            UNION
            SELECT 
                order_number,
                'Прибытие в Иран' as event_type,
                arrival_iran_date as event_date
            FROM orders 
            WHERE arrival_iran_date BETWEEN %s AND %s
            UNION
            SELECT 
                order_number,
                'Погрузка на грузовик' as event_type,
                truck_loading_date as event_date
            FROM orders 
            WHERE truck_loading_date BETWEEN %s AND %s
            UNION
            SELECT 
                order_number,
                'Прибытие в Туркменистан' as event_type,
                arrival_turkmenistan_date as event_date
            FROM orders 
            WHERE arrival_turkmenistan_date BETWEEN %s AND %s
            UNION
            SELECT 
                order_number,
                'Получение клиентом' as event_type,
                client_receiving_date as event_date
            FROM orders 
            WHERE client_receiving_date BETWEEN %s AND %s
            ORDER BY event_date
            """
            
            self.cursor.execute(query, (
                from_date, to_date,
                from_date, to_date,
                from_date, to_date,
                from_date, to_date,
                from_date, to_date
            ))
            
            return self.cursor.fetchall()
            
        except Exception as e:
            print(f"Error getting upcoming events: {e}")
            return []
    
    def search_orders(self, search_text: str) -> List[Order]:
        """Поиск заказов по тексту"""
        try:
            search_pattern = f"%{search_text}%"
            
            return self.db_session.query(Order).filter(
                or_(
                    Order.order_number.ilike(search_pattern),
                    Order.client_name.ilike(search_pattern),
                    Order.goods_type.ilike(search_pattern),
                    Order.route.ilike(search_pattern),
                    Order.document_number.ilike(search_pattern)
                )
            ).order_by(Order.created_at.desc()).all()
            
        except SQLAlchemyError as e:
            print(f"Error searching orders: {e}")
            return []
    
    def get_orders_without_photos(self) -> List[Order]:
        """Получить заказы без фото загрузки"""
        try:
            return self.db_session.query(Order).filter(
                Order.has_loading_photo == False
            ).order_by(Order.created_at.desc()).all()
        except SQLAlchemyError as e:
            print(f"Error getting orders without photos: {e}")
            return []
    
    def get_orders_without_documents(self) -> List[Order]:
        """Получить заказы без необходимых документов"""
        try:
            return self.db_session.query(Order).filter(
                or_(
                    Order.has_local_charges == False,
                    Order.has_tex == False
                )
            ).order_by(Order.created_at.desc()).all()
        except SQLAlchemyError as e:
            print(f"Error getting orders without documents: {e}")
            return []
    
    def update_order_from_sync(self, order_data: Dict) -> bool:
        """Обновить заказ из синхронизации"""
        try:
            order_number = order_data.get('order_number')
            if not order_number:
                return False
            
            # Проверяем существование заказа
            existing_order = self.get_order_by_number(order_number)
            
            if existing_order:
                # Обновляем существующий заказ
                for key, value in order_data.items():
                    if hasattr(existing_order, key) and value is not None:
                        setattr(existing_order, key, value)
                existing_order.updated_at = datetime.now()
            else:
                # Создаем новый заказ
                new_order = Order(**order_data)
                self.db_session.add(new_order)
            
            self.db_session.commit()
            return True
            
        except Exception as e:
            print(f"Error updating order from sync: {e}")
            self.db_session.rollback()
            return False
    
    def get_statistics(self, days: int = 30) -> Dict:
        """Получить статистику за указанный период"""
        from_date = datetime.now() - timedelta(days=days)
        
        try:
            # Общая статистика
            total_orders = self.db_session.query(func.count(Order.id)).filter(
                Order.created_at >= from_date
            ).scalar() or 0
            
            completed_orders = self.db_session.query(func.count(Order.id)).filter(
                Order.status == OrderStatus.COMPLETED,
                Order.updated_at >= from_date
            ).scalar() or 0
            
            active_orders = self.db_session.query(func.count(Order.id)).filter(
                Order.status.in_([
                    OrderStatus.NEW,
                    OrderStatus.IN_PROGRESS_CHN,
                    OrderStatus.IN_TRANSIT_CHN_IR,
                    OrderStatus.IN_PROGRESS_IR,
                    OrderStatus.IN_TRANSIT_IR_TKM
                ])
            ).scalar() or 0
            
            # Статистика по контейнерам
            containers_query = """
            SELECT 
                COUNT(*) as total_containers,
                COALESCE(SUM(weight), 0) as total_weight,
                COALESCE(SUM(volume), 0) as total_volume
            FROM containers c
            JOIN orders o ON c.order_id = o.id
            WHERE o.created_at >= %s
            """
            
            self.cursor.execute(containers_query, (from_date,))
            container_stats = self.cursor.fetchone()
            
            return {
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'active_orders': active_orders,
                'total_containers': container_stats['total_containers'] or 0,
                'total_weight': float(container_stats['total_weight'] or 0),
                'total_volume': float(container_stats['total_volume'] or 0),
                'period_days': days
            }
            
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}
    
    def close(self):
        """Закрыть соединения"""
        try:
            self.db_session.close()
            self.cursor.close()
            self.conn.close()
        except:
            pass