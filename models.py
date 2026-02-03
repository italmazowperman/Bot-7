from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()

class OrderStatus(enum.Enum):
    """Статусы заказов"""
    NEW = "New"
    IN_PROGRESS_CHN = "In Progress CHN"
    IN_TRANSIT_CHN_IR = "In Transit CHN-IR"
    IN_PROGRESS_IR = "In Progress IR"
    IN_TRANSIT_IR_TKM = "In Transit IR-TKM"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

class Order(Base):
    """Модель заказа"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    order_number = Column(String(50), unique=True, nullable=False)
    client_name = Column(String(200), nullable=False)
    container_count = Column(Integer, default=0)
    goods_type = Column(String(100))
    route = Column(String(200))
    transit_port = Column(String(100))
    document_number = Column(String(100))
    chinese_transport_company = Column(String(200))
    iranian_transport_company = Column(String(200))
    status = Column(String(50), default=OrderStatus.NEW.value)
    status_color = Column(String(20), default="#FFFFFF")
    
    # Даты
    creation_date = Column(DateTime, default=datetime.now)
    loading_date = Column(DateTime)
    departure_date = Column(DateTime)
    arrival_iran_date = Column(DateTime)
    truck_loading_date = Column(DateTime)
    arrival_turkmenistan_date = Column(DateTime)
    client_receiving_date = Column(DateTime)
    arrival_notice_date = Column(DateTime)
    tkm_date = Column(DateTime)
    eta_date = Column(DateTime)
    
    # Флаги
    has_loading_photo = Column(Boolean, default=False)
    has_local_charges = Column(Boolean, default=False)
    has_tex = Column(Boolean, default=False)
    
    # Дополнительная информация
    notes = Column(Text)
    additional_info = Column(Text)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Связи
    containers = relationship("Container", back_populates="order", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="order", cascade="all, delete-orphan")
    
    @property
    def total_weight(self):
        """Общий вес всех контейнеров"""
        return sum(container.weight for container in self.containers)
    
    @property
    def total_volume(self):
        """Общий объем всех контейнеров"""
        return sum(container.volume for container in self.containers)

class Container(Base):
    """Модель контейнера"""
    __tablename__ = 'containers'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    container_number = Column(String(50))
    container_type = Column(String(50), default="20ft Standard")
    weight = Column(Float, default=0.0)
    volume = Column(Float, default=0.0)
    
    # Даты контейнера
    loading_date = Column(DateTime)
    departure_date = Column(DateTime)
    arrival_iran_date = Column(DateTime)
    truck_loading_date = Column(DateTime)
    arrival_turkmenistan_date = Column(DateTime)
    client_receiving_date = Column(DateTime)
    
    # Информация о водителе и грузовике
    driver_first_name = Column(String(100))
    driver_last_name = Column(String(100))
    driver_company = Column(String(200))
    truck_number = Column(String(50))
    driver_iran_phone = Column(String(50))
    driver_turkmenistan_phone = Column(String(50))
    
    # Связи
    order = relationship("Order", back_populates="containers")

class Task(Base):
    """Модель задачи"""
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    description = Column(String(500), nullable=False)
    assigned_to = Column(String(100))
    status = Column(String(50), default="ToDo")
    priority = Column(String(50), default="Medium")
    due_date = Column(DateTime)
    created_date = Column(DateTime, default=datetime.now)
    
    # Связи
    order = relationship("Order", back_populates="tasks")

# Модели для уведомлений и подписок
class Notification(Base):
    """Модель уведомления"""
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50))  # 'event', 'reminder', 'alert'
    scheduled_time = Column(DateTime, nullable=False)
    sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

class Subscription(Base):
    """Модель подписки на уведомления"""
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    notify_events = Column(Boolean, default=True)
    notify_reminders = Column(Boolean, default=True)
    notify_alerts = Column(Boolean, default=True)
    hours_before = Column(Integer, default=24)  # За сколько часов уведомлять
    created_at = Column(Integer, default=datetime.now)
    updated_at = Column(Integer, default=datetime.now, onupdate=datetime.now)