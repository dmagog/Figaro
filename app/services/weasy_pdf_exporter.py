from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader
import os
from datetime import datetime
from io import BytesIO
import tempfile

class WeasyPDFExporter:
    def __init__(self):
        # Настраиваем Jinja2 для поиска шаблонов
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
    
    def export_route_pdf(self, user_data, concerts_by_day, off_program_events):
        """
        Экспортирует маршрут пользователя в PDF используя WeasyPrint
        """
        try:
            # Получаем шаблон
            template = self.jinja_env.get_template('route_sheet_pdf.html')
            
            # Подготавливаем данные для шаблона
            template_data = {
                'user': user_data,
                'concerts_by_day': concerts_by_day,
                'off_program_events': off_program_events,
                'export_date': datetime.now().strftime('%d.%m.%Y %H:%M')
            }
            
            # Рендерим HTML
            html_content = template.render(**template_data)
            
            # Создаем PDF
            html_doc = HTML(string=html_content)
            
            # Генерируем PDF
            pdf_bytes = html_doc.write_pdf()
            
            # Возвращаем как BytesIO
            pdf_io = BytesIO(pdf_bytes)
            pdf_io.seek(0)
            
            return pdf_io
            
        except Exception as e:
            raise Exception(f"Error generating PDF with WeasyPrint: {str(e)}") 