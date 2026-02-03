import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend

from models import Order
from database import DatabaseManager

# Регистрация шрифтов (если нужны кириллические шрифты)
try:
    pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
except:
    pass  # Используем стандартные шрифты

class PDFGenerator:
    """Генератор PDF отчетов"""
    
    @staticmethod
    def generate_order_pdf(order: Order) -> bytes:
        """Сгенерировать PDF отчет по заказу"""
        buffer = io.BytesIO()
        
        # Создаем документ
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Стили
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'Heading',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=12,
            textColor=colors.HexColor('#2C3E50')
        )
        
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Заголовок
        title = Paragraph(f"ОТЧЕТ ПО ЗАКАЗУ: {order.order_number}", title_style)
        story.append(title)
        
        # Информация о компании
        company_info = """
        <b>Margiana Logistic Services</b><br/>
        International Logistics & Transportation<br/>
        +993 61 55 77 79 | @margiana_logistics
        """
        story.append(Paragraph(company_info, normal_style))
        story.append(Spacer(1, 20))
        
        # Основная информация
        story.append(Paragraph("<b>ОСНОВНАЯ ИНФОРМАЦИЯ</b>", heading_style))
        
        basic_data = [
            ["Номер заказа:", order.order_number],
            ["Клиент:", order.client_name],
            ["Тип груза:", order.goods_type or "-"],
            ["Маршрут:", order.route or "-"],
            ["Транзитный порт:", order.transit_port or "-"],
            ["Статус:", order.status],
            ["Дата создания:", order.creation_date.strftime('%d.%m.%Y')],
            ["Контейнеров:", str(order.container_count)]
        ]
        
        basic_table = Table(basic_data, colWidths=[5*cm, 10*cm])
        basic_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('FONTSIZE', (0, 0), (-1, -1), 9)
        ]))
        story.append(basic_table)
        story.append(Spacer(1, 20))
        
        # Даты событий
        story.append(Paragraph("<b>ДАТЫ СОБЫТИЙ</b>", heading_style))
        
        event_dates = [
            ["Событие", "Дата", "Статус"],
            ["Отплытие из Китая (ATD)", 
             order.departure_date.strftime('%d.%m.%Y') if order.departure_date else "-",
             "✓" if order.departure_date else "✗"],
            ["Прибытие в Иран", 
             order.arrival_iran_date.strftime('%d.%m.%Y') if order.arrival_iran_date else "-",
             "✓" if order.arrival_iran_date else "✗"],
            ["Погрузка на грузовик", 
             order.truck_loading_date.strftime('%d.%m.%Y') if order.truck_loading_date else "-",
             "✓" if order.truck_loading_date else "✗"],
            ["Прибытие в Туркменистан", 
             order.arrival_turkmenistan_date.strftime('%d.%m.%Y') if order.arrival_turkmenistan_date else "-",
             "✓" if order.arrival_turkmenistan_date else "✗"],
            ["Получение клиентом (POD)", 
             order.client_receiving_date.strftime('%d.%m.%Y') if order.client_receiving_date else "-",
             "✓" if order.client_receiving_date else "✗"],
            ["Ожидаемое прибытие (ETA)", 
             order.eta_date.strftime('%d.%m.%Y') if order.eta_date else "-",
             ""]
        ]
        
        event_table = Table(event_dates, colWidths=[6*cm, 4*cm, 2*cm])
        event_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (1, 1), (1, -1), colors.HexColor('#F8F9F9')),
            ('BACKGROUND', (2, 1), (2, -1), colors.HexColor('#F8F9F9'))
        ]))
        story.append(event_table)
        story.append(Spacer(1, 20))
        
        # Контейнеры
        if order.containers:
            story.append(Paragraph("<b>КОНТЕЙНЕРЫ</b>", heading_style))
            
            container_headers = ["Контейнер", "Тип", "Вес (кг)", "Объем (м³)"]
            container_data = [container_headers]
            
            for container in order.containers:
                container_data.append([
                    container.container_number,
                    container.container_type,
                    f"{container.weight:.0f}",
                    f"{container.volume:.1f}"
                ])
            
            container_table = Table(container_data, colWidths=[4*cm, 4*cm, 3*cm, 3*cm])
            container_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9F9'))
            ]))
            story.append(container_table)
            
            # Итоги по контейнерам
            total_weight = sum(c.weight for c in order.containers)
            total_volume = sum(c.volume for c in order.containers)
            
            totals = Paragraph(
                f"<b>Итого:</b> {len(order.containers)} контейнеров, "
                f"{total_weight:.0f} кг, {total_volume:.1f} м³",
                normal_style
            )
            story.append(totals)
            story.append(Spacer(1, 20))
        
        # Документы
        story.append(Paragraph("<b>ДОКУМЕНТЫ</b>", heading_style))
        
        docs_data = [
            ["Документ", "Статус"],
            ["Фото загрузки", "✓" if order.has_loading_photo else "✗"],
            ["Местные сборы", "✓" if order.has_local_charges else "✗"],
            ["TLX", "✓" if order.has_tex else "✗"]
        ]
        
        docs_table = Table(docs_data, colWidths=[8*cm, 3*cm])
        docs_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (1, 1), (1, -1), colors.HexColor('#F8F9F9'))
        ]))
        story.append(docs_table)
        story.append(Spacer(1, 20))
        
        # Заметки
        if order.notes:
            story.append(Paragraph("<b>ЗАМЕТКИ</b>", heading_style))
            notes = Paragraph(order.notes, normal_style)
            story.append(notes)
            story.append(Spacer(1, 20))
        
        # Подвал
        footer = Paragraph(
            f"Отчет сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}<br/>"
            "Margiana Logistic Services © 2024",
            ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER
            )
        )
        story.append(footer)
        
        # Собираем PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    @staticmethod
    def generate_summary_pdf(days: int = 30) -> bytes:
        """Сгенерировать сводный PDF отчет"""
        buffer = io.BytesIO()
        
        # Получаем статистику
        db = DatabaseManager()
        stats = db.get_statistics(days)
        active_orders = db.get_active_orders()
        recent_orders = db.get_all_orders()[:10]  # Последние 10 заказов
        
        # Создаем документ
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Стили
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2C3E50')
        )
        
        heading_style = ParagraphStyle(
            'Heading',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=10,
            textColor=colors.HexColor('#2C3E50')
        )
        
        # Заголовок
        title = Paragraph(
            f"СВОДНЫЙ ОТЧЕТ ЗА {days} ДНЕЙ<br/>"
            f"Margiana Logistic Services",
            title_style
        )
        story.append(title)
        story.append(Spacer(1, 30))
        
        # Статистика
        story.append(Paragraph("<b>СТАТИСТИКА</b>", heading_style))
        
        stats_data = [
            ["Показатель", "Значение"],
            ["Всего заказов", str(stats.get('total_orders', 0))],
            ["Активные заказы", str(stats.get('active_orders', 0))],
            ["Завершенные заказы", str(stats.get('completed_orders', 0))],
            ["Всего контейнеров", str(stats.get('total_containers', 0))],
            ["Общий вес", f"{stats.get('total_weight', 0):.0f} кг"],
            ["Общий объем", f"{stats.get('total_volume', 0):.1f} м³"]
        ]
        
        stats_table = Table(stats_data, colWidths=[8*cm, 5*cm])
        stats_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9F9'))
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 30))
        
        # Активные заказы
        story.append(Paragraph(f"<b>АКТИВНЫЕ ЗАКАЗЫ ({len(active_orders)})</b>", heading_style))
        
        if active_orders:
            active_headers = ["№", "Заказ", "Клиент", "Контейнеры", "Статус", "ETA"]
            active_data = [active_headers]
            
            for i, order in enumerate(active_orders[:15], 1):
                active_data.append([
                    str(i),
                    order.order_number,
                    order.client_name[:20] + "..." if len(order.client_name) > 20 else order.client_name,
                    str(order.container_count),
                    order.status,
                    order.eta_date.strftime('%d.%m') if order.eta_date else "-"
                ])
            
            active_table = Table(active_data, colWidths=[1.5*cm, 3*cm, 5*cm, 2.5*cm, 4*cm, 3*cm])
            active_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'LEFT'),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9F9')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ECF0F1')])
            ]))
            story.append(active_table)
        else:
            story.append(Paragraph("Нет активных заказов", styles['Normal']))
        
        story.append(Spacer(1, 30))
        
        # Последние заказы
        story.append(Paragraph(f"<b>ПОСЛЕДНИЕ ЗАКАЗЫ</b>", heading_style))
        
        if recent_orders:
            recent_headers = ["Заказ", "Клиент", "Дата создания", "Статус"]
            recent_data = [recent_headers]
            
            for order in recent_orders[:10]:
                recent_data.append([
                    order.order_number,
                    order.client_name[:25] + "..." if len(order.client_name) > 25 else order.client_name,
                    order.creation_date.strftime('%d.%m.%Y'),
                    order.status
                ])
            
            recent_table = Table(recent_data, colWidths=[4*cm, 6*cm, 4*cm, 4*cm])
            recent_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9F9'))
            ]))
            story.append(recent_table)
        
        # Подвал
        footer = Paragraph(
            f"Отчет сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')} | "
            f"Период: {days} дней | "
            "Margiana Logistic Services © 2024",
            ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER
            )
        )
        story.append(Spacer(1, 20))
        story.append(footer)
        
        # Собираем PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer.getvalue()

# Функции для экспорта
def generate_order_pdf(order: Order) -> bytes:
    """Сгенерировать PDF для заказа"""
    return PDFGenerator.generate_order_pdf(order)

def generate_summary_pdf(days: int = 30) -> bytes:
    """Сгенерировать сводный PDF отчет"""
    return PDFGenerator.generate_summary_pdf(days)