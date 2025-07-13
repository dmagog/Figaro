import logging
from typing import Optional

def get_logger(logger_name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """
    Создает и настраивает логгер для приложения.
    
    Args:
        logger_name: Имя логгера
        level: Уровень логирования
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    logger = logging.getLogger(logger_name)
    
    if not logger.handlers:
        logger.setLevel(level)
        
        # Создаем обработчик для вывода в консоль
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        
        # Создаем форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        # Добавляем обработчик к логгеру
        logger.addHandler(console_handler)
    
    return logger 