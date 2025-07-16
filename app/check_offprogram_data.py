from database.database import get_session
from models import OffProgram
from sqlmodel import select

def check_offprogram_data():
    """Проверяет наличие данных Офф-программы в базе"""
    
    try:
        session = next(get_session())
        
        # Проверяем количество записей
        events = session.exec(select(OffProgram)).all()
        print(f"📊 Найдено {len(events)} мероприятий Офф-программы")
        
        if events:
            print("\n📋 Примеры мероприятий:")
            for i, event in enumerate(events[:3]):
                print(f"  {i+1}. {event.event_name}")
                print(f"     Дата: {event.event_date}")
                print(f"     Зал: {event.hall_name}")
                print(f"     Формат: {event.format.value if event.format else 'Не указан'}")
                print()
        else:
            print("❌ Данные Офф-программы не найдены в базе")
            print("💡 Нужно загрузить данные через инициализацию базы")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Ошибка при проверке данных: {e}")

if __name__ == "__main__":
    check_offprogram_data() 