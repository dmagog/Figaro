from dataclasses import dataclass
import pika

@dataclass
class RabbitMQConfig:
    """
    Конфигурационные параметры для подключения к RabbitMQ.
    
    Атрибуты:
        host: Адрес сервера RabbitMQ
        port: Порт для подключения
        virtual_host: Виртуальный хост
        username: Имя пользователя
        password: Пароль
        queue_name: Название основной очереди задач
        rpc_queue_name: Название очереди для RPC-запросов
        heartbeat: Интервал проверки соединения в секундах
        connection_timeout: Таймаут подключения в секундах
    """
    # Параметры подключения
    host: str = 'rabbitmq'
    port: int = 5672
    virtual_host: str = '/'
    
    # Параметры аутентификации
    username: str = 'rmuser'
    password: str = 'rmpassword'
    
    # Параметры очередей
    queue_name: str = 'ml_task_queue'
    rpc_queue_name: str = 'rpc_queue'
    
    # Параметры соединения
    heartbeat: int = 30
    connection_timeout: int = 2

    def get_connection_params(self) -> pika.ConnectionParameters:
        """Создает параметры подключения к RabbitMQ."""
        return pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.virtual_host,
            credentials=pika.PlainCredentials(
                username=self.username,
                password=self.password
            ),
            heartbeat=self.heartbeat,
            blocked_connection_timeout=self.connection_timeout
        )
