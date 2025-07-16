import pandas as pd
import os
from database.database import get_session
from services.crud.data_loader import load_off_program
from models import OffProgram, EventFormat
from sqlmodel import select

def test_offprogram_loading():
    """Тестирует загрузку данных Офф-программы"""
    
    file_path = 'data/OffProgram-good.xlsx'
    
    if not os.path.exists(file_path):
        print(f"❌ Файл {file_path} не найден!")
        return False
    
    try:
        # Читаем Excel файл
        print("📖 Читаем файл Офф-программы...")
        df = pd.read_excel(file_path)
        print(f"✅ Загружено {len(df)} мероприятий из файла")
        
        # Подключаемся к базе данных
        print("🔌 Подключаемся к базе данных...")
        session = next(get_session())
        
        # Загружаем данные
        print("📥 Загружаем данные в базу...")
        load_off_program(session, df)
        
        # Проверяем результат
        print("🔍 Проверяем результат загрузки...")
        events = session.exec(select(OffProgram)).all()
        print(f"✅ В базе данных: {len(events)} мероприятий")
        
        # Показываем статистику
        print("\n📊 Статистика загруженных данных:")
        
        # По форматам
        formats = {}
        for event in events:
            format_name = event.format.value if event.format else "Не указан"
            formats[format_name] = formats.get(format_name, 0) + 1
        
        print("   Форматы мероприятий:")
        for format_name, count in formats.items():
            print(f"     • {format_name}: {count}")
        
        # По рекомендациям
        recommended = sum(1 for event in events if event.recommend)
        print(f"   Рекомендуемых мероприятий: {recommended}")
        
        # По залам
        halls = {}
        for event in events:
            halls[event.hall_name] = halls.get(event.hall_name, 0) + 1
        
        print("   Залы:")
        for hall_name, count in halls.items():
            print(f"     • {hall_name}: {count}")
        
        # Показываем несколько примеров
        print("\n📋 Примеры загруженных мероприятий:")
        for i, event in enumerate(events[:5]):
            print(f"   {i+1}. {event.event_name}")
            print(f"      Дата: {event.event_date.strftime('%d.%m.%Y %H:%M')}")
            print(f"      Зал: {event.hall_name}")
            print(f"      Формат: {event.format.value if event.format else 'Не указан'}")
            print(f"      Рекомендуется: {'Да' if event.recommend else 'Нет'}")
            print()
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

if __name__ == "__main__":
    print("🧪 ТЕСТИРОВАНИЕ ЗАГРУЗКИ ОФФ-ПРОГРАММЫ")
    print("=" * 50)
    
    success = test_offprogram_loading()
    
    if success:
        print("✅ Тестирование завершено успешно!")
    else:
        print("❌ Тестирование завершено с ошибками!") 