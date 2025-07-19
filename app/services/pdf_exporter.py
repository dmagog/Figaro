from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, Frame, PageTemplate
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from io import BytesIO
from datetime import datetime
import os

class PDFExporter:
    def __init__(self):
        # Регистрируем шрифт с поддержкой кириллицы
        try:
            # Пытаемся зарегистрировать Liberation Sans
            pdfmetrics.registerFont(TTFont('LiberationSans', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'))
            self.default_font = 'LiberationSans'
        except:
            try:
                # Альтернативный шрифт DejaVu Sans
                pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                self.default_font = 'DejaVuSans'
            except:
                # Если не получилось, используем стандартный
                self.default_font = 'Helvetica'
        
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Настройка пользовательских стилей с поддержкой кириллицы"""
        # Главный заголовок
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Heading1'],
            fontSize=32,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1e3a8a'),  # Темно-синий
            fontName=self.default_font,
            spaceBefore=20
        ))
        
        # Заголовок раздела
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=20,
            spaceAfter=15,
            spaceBefore=25,
            textColor=colors.HexColor('#1e40af'),  # Синий
            fontName=self.default_font,
            leftIndent=10,
            borderWidth=1,
            borderColor=colors.HexColor('#3b82f6'),
            borderPadding=8,
            backColor=colors.HexColor('#eff6ff')
        ))
        
        # Заголовок дня
        self.styles.add(ParagraphStyle(
            name='DayHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.white,
            backColor=colors.HexColor('#3b82f6'),  # Синий фон
            fontName=self.default_font,
            leftIndent=15,
            rightIndent=15,
            alignment=TA_CENTER,
            borderWidth=1,
            borderColor=colors.HexColor('#1e40af'),
            borderPadding=6
        ))
        
        # Название концерта
        self.styles.add(ParagraphStyle(
            name='ConcertTitle',
            parent=self.styles['Normal'],
            fontSize=14,
            spaceAfter=8,
            textColor=colors.HexColor('#1f2937'),  # Темно-серый
            fontName=self.default_font,
            leftIndent=25,
            spaceBefore=5,
            backColor=colors.HexColor('#f9fafb'),
            borderWidth=0.5,
            borderColor=colors.HexColor('#e5e7eb'),
            borderPadding=4
        ))
        
        # Детали концерта
        self.styles.add(ParagraphStyle(
            name='ConcertDetails',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=4,
            leftIndent=45,
            textColor=colors.HexColor('#6b7280'),  # Серый
            fontName=self.default_font
        ))
        
        # Офф-программа
        self.styles.add(ParagraphStyle(
            name='OffProgram',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=4,
            leftIndent=35,
            textColor=colors.HexColor('#059669'),  # Зеленый
            backColor=colors.HexColor('#d1fae5'),  # Светло-зеленый фон
            fontName=self.default_font,
            spaceBefore=3,
            borderWidth=0.5,
            borderColor=colors.HexColor('#10b981'),
            borderPadding=3
        ))
        
        # Информация о переходе
        self.styles.add(ParagraphStyle(
            name='TransitionInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=4,
            leftIndent=45,
            textColor=colors.HexColor('#dc2626'),  # Красный для предупреждений
            fontName=self.default_font,
            spaceBefore=3,
            backColor=colors.HexColor('#fef2f2'),
            borderWidth=0.5,
            borderColor=colors.HexColor('#fca5a5'),
            borderPadding=3
        ))
        
        # Обычный переход
        self.styles.add(ParagraphStyle(
            name='NormalTransition',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=4,
            leftIndent=45,
            textColor=colors.HexColor('#7c3aed'),  # Фиолетовый
            fontName=self.default_font,
            spaceBefore=3,
            backColor=colors.HexColor('#f3f4f6'),
            borderWidth=0.5,
            borderColor=colors.HexColor('#c4b5fd'),
            borderPadding=3
        ))
        
        # Информация о пользователе
        self.styles.add(ParagraphStyle(
            name='UserInfo',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=8,
            textColor=colors.HexColor('#374151'),  # Темно-серый
            fontName=self.default_font,
            alignment=TA_CENTER,
            backColor=colors.HexColor('#f8fafc'),
            borderWidth=1,
            borderColor=colors.HexColor('#e2e8f0'),
            borderPadding=6
        ))
        
        # Обновляем базовые стили
        self.styles['Normal'].fontName = self.default_font
        self.styles['Heading1'].fontName = self.default_font
        self.styles['Heading2'].fontName = self.default_font
        self.styles['Heading3'].fontName = self.default_font
    
    def export_route_sheet(self, route_data, user_name="Пользователь"):
        """
        Экспортирует маршрутный лист в PDF
        
        Args:
            route_data: Данные маршрутного листа
            user_name: Имя пользователя
            
        Returns:
            BytesIO объект с PDF
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              leftMargin=1*cm, rightMargin=1*cm, 
                              topMargin=1.5*cm, bottomMargin=1.5*cm)
        story = []
        
        # Главный заголовок
        story.append(Paragraph("МАРШРУТНЫЙ ЛИСТ ФЕСТИВАЛЯ", self.styles['MainTitle']))
        story.append(Spacer(1, 15))
        
        # Разделительная линия
        story.append(HRFlowable(width="100%", thickness=3, color=colors.HexColor('#3b82f6')))
        story.append(Spacer(1, 20))
        
        # Информация о пользователе и дате
        current_date = datetime.now().strftime("%d.%m.%Y")
        story.append(Paragraph(f"Пользователь: {user_name}", self.styles['UserInfo']))
        story.append(Paragraph(f"Дата создания: {current_date}", self.styles['UserInfo']))
        story.append(Spacer(1, 25))
        
        # Сводная статистика
        summary = route_data.get('summary', {})
        if summary:
            story.append(Paragraph("СВОДНАЯ СТАТИСТИКА", self.styles['SectionTitle']))
            story.append(Spacer(1, 10))
            
            summary_data = [
                ['Параметр', 'Значение'],
                ['Всего концертов', str(summary.get('total_concerts', 0))],
                ['Дней фестиваля', str(summary.get('total_days', 0))],
                ['Уникальных залов', str(summary.get('total_halls', 0))],
                ['Жанров', str(summary.get('total_genres', 0))],
                ['Потрачено', f"{summary.get('total_spent', 0)} руб."]
            ]
            
            summary_table = Table(summary_data, colWidths=[3.5*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.HexColor('#f1f5f9')]),
                ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#1e3a8a'))
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 25))
        
        # Информация о соответствии маршруту
        match_data = route_data.get('match', {})
        if match_data and match_data.get('found'):
            story.append(Paragraph("СООТВЕТСТВИЕ МАРШРУТУ", self.styles['SectionTitle']))
            story.append(Spacer(1, 10))
            
            if match_data.get('match_type') == 'exact':
                story.append(Paragraph("V Точное совпадение с маршрутом", self.styles['Normal']))
            else:
                story.append(Paragraph("O Частичное совпадение с маршрутом", self.styles['Normal']))
            story.append(Paragraph(f"Причина: {match_data.get('reason', 'Не указано')}", self.styles['Normal']))
            story.append(Spacer(1, 25))
        
        # Концерты по дням
        concerts_by_day = route_data.get('concerts_by_day', {})
        if concerts_by_day:
            story.append(Paragraph("РАСПИСАНИЕ КОНЦЕРТОВ ПО ДНЯМ", self.styles['SectionTitle']))
            story.append(Spacer(1, 15))
            
            concert_counter = 1
            
            for day_index, day_concerts in concerts_by_day.items():
                if not day_concerts:
                    continue
                
                # Заголовок дня
                first_concert = day_concerts[0]
                concert_date = first_concert.get('concert', {}).get('datetime')
                if concert_date:
                    date_str = concert_date.strftime("%d.%m.%Y")
                    day_name = concert_date.strftime("%A")
                    day_header = f"День {day_index} - {date_str} ({day_name})"
                else:
                    day_header = f"День {day_index}"
                
                story.append(Paragraph(day_header, self.styles['DayHeader']))
                
                # Офф-программа до первого концерта
                if day_concerts[0].get('before_concert_events'):
                    story.append(Paragraph("Офф-программа до первого концерта:", self.styles['OffProgram']))
                    for event in day_concerts[0]['before_concert_events']:
                        event_text = f"• {event.get('event_date_display', '')} - {event.get('event_name', '')} ({event.get('format', '')})"
                        story.append(Paragraph(event_text, self.styles['OffProgram']))
                    story.append(Spacer(1, 8))
                
                # Концерты дня
                for i, concert in enumerate(day_concerts):
                    concert_data = concert.get('concert', {})
                    
                    # Время и номер концерта
                    time_str = concert_data.get('datetime', '').strftime("%H:%M") if concert_data.get('datetime') else 'TBD'
                    concert_title = f"[{concert_counter}] {time_str} - Концерт №{concert_data.get('id', '')}: {concert_data.get('name', '')}"
                    story.append(Paragraph(concert_title, self.styles['ConcertTitle']))
                    concert_counter += 1
                    
                    # Детали концерта
                    hall_name = concert_data.get('hall', {}).get('name', 'Зал не указан')
                    genre = concert_data.get('genre', 'Жанр не указан')
                    duration = concert_data.get('duration')
                    
                    if duration and hasattr(duration, 'total_seconds'):
                        duration_str = f"{int(duration.total_seconds() // 60)} мин"
                    else:
                        duration_str = "Длительность не указана"
                    
                    details = [
                        f"Зал: {hall_name}",
                        f"Жанр: {genre}",
                        f"Длительность: {duration_str}"
                    ]
                    
                    for detail in details:
                        story.append(Paragraph(detail, self.styles['ConcertDetails']))
                    
                    # Артисты
                    artists = concert_data.get('artists', [])
                    if artists:
                        artist_names = [artist.get('name', '') for artist in artists]
                        artists_text = f"Артисты: {', '.join(artist_names)}"
                        story.append(Paragraph(artists_text, self.styles['ConcertDetails']))
                    
                    # Информация о переходе к следующему концерту
                    if i < len(day_concerts) - 1:
                        transition_info = concert.get('transition_info')
                        if transition_info:
                            status = transition_info.get('status', '')
                            walk_time = transition_info.get('walk_time', 0)
                            time_between = transition_info.get('time_between', 0)
                            
                            if status == 'overlap':
                                transition_text = f"! ВНИМАНИЕ: наложение концертов по времени!"
                                story.append(Paragraph(transition_text, self.styles['TransitionInfo']))
                            elif status == 'hurry':
                                transition_text = f"-> Переход: {walk_time} мин (нужно поторопиться)"
                                story.append(Paragraph(transition_text, self.styles['TransitionInfo']))
                            elif status == 'tight':
                                transition_text = f"-> Переход: {walk_time} мин (впритык)"
                                story.append(Paragraph(transition_text, self.styles['TransitionInfo']))
                            else:
                                transition_text = f"-> Переход: {walk_time} мин (достаточно времени)"
                                story.append(Paragraph(transition_text, self.styles['NormalTransition']))
                    
                    # Офф-программа между концертами
                    off_program_events = concert.get('off_program_events', [])
                    if off_program_events:
                        story.append(Paragraph("Офф-программа между концертами:", self.styles['OffProgram']))
                        for event in off_program_events:
                            event_text = f"• {event.get('event_date_display', '')} - {event.get('event_name', '')} ({event.get('format', '')})"
                            story.append(Paragraph(event_text, self.styles['OffProgram']))
                        story.append(Spacer(1, 8))
                    
                    story.append(Spacer(1, 10))
                
                # Офф-программа после последнего концерта
                if day_concerts[-1].get('after_concert_events'):
                    story.append(Paragraph("Офф-программа после последнего концерта:", self.styles['OffProgram']))
                    for event in day_concerts[-1]['after_concert_events']:
                        event_text = f"• {event.get('event_date_display', '')} - {event.get('event_name', '')} ({event.get('format', '')})"
                        story.append(Paragraph(event_text, self.styles['OffProgram']))
                    story.append(Spacer(1, 8))
                
                story.append(Spacer(1, 20))
        
        # Создаем PDF
        doc.build(story)
        buffer.seek(0)
        return buffer 