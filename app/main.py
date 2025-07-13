from database.config import get_settings
from database.database import get_session, init_db, engine
from sqlmodel import Session
import datetime



if __name__ == "__main__":

    settings = get_settings()
    print('gfo gso = ', settings.DB_HOST)
    print('gfo gso = =', settings.DB_NAME)

    init_db(demostart = True)
    print('Init db has been success')


    #print('\n\n2222 Вывод истории операций пользоывателя  222')
    #print(get_bill_operations_list_2(1, session = Session(engine)))

  


 