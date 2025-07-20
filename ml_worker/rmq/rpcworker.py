import pika
import time
import logging
from rmq.rmqconf import RabbitMQConfig
from llm import do_task
from typing import Optional
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

# Настраиваем общий уровень логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Устанавливаем уровень WARNING для логов pika
logging.getLogger('pika').setLevel(logging.INFO)

logger = logging.getLogger(__name__)

class RPCWorker:
    """
    Рабочий класс для обработки RPC задач из RabbitMQ.
    Обеспечивает обработку текстовых запросов через RPC механизм.
    """

    def __init__(self, config: RabbitMQConfig, max_retries: int = 3):
        """
        Инициализация RPC обработчика с заданной конфигурацией.

        Аргументы:
            config: Объект конфигурации RabbitMQ
            max_retries: Максимальное количество попыток переподключения
        """
        self.config = config
        # Соединение с RabbitMQ
        self.connection: Optional[pika.BlockingConnection] = None
        # Канал для работы с RabbitMQ
        self.channel: Optional[BlockingChannel] = None
        self.max_retries = max_retries

    def connect(self) -> None:
        """
        Установка соединения с сервером RabbitMQ с поддержкой повторных попыток.

        Raises:
            Exception: Если не удалось установить соединение после всех попыток
        """
        for attempt in range(self.max_retries):
            try:
                # Параметры подключения к RabbitMQ
                connection_params = pika.ConnectionParameters(
                    host=self.config.host,
                    port=self.config.port,
                    virtual_host=self.config.virtual_host,
                    credentials=pika.PlainCredentials(
                        username=self.config.username,
                        password=self.config.password
                    ),
                    heartbeat=self.config.heartbeat,
                    blocked_connection_timeout=self.config.connection_timeout
                )

                # Устанавливаем соединение и создаем канал
                self.connection = pika.BlockingConnection(connection_params)
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue=self.config.rpc_queue_name)
                logger.info("Успешно подключились к RabbitMQ")
                return
            except Exception as e:
                logger.error(f"Попытка подключения {attempt + 1} не удалась: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Экспоненциальная задержка между попытками
                else:
                    raise

    def process_text(self, text: str) -> str:
        """
        Обработка входящего текста.

        Аргументы:
            text: Входящий текст для обработки

        Возвращает:
            str: Обработанный текст
        """
        #return '[RESULT] Просто офигенский результат работы модели, который так понравится пользователю, что прям вах!'
        return do_task(text)
    
    
    def on_request(self, ch: BlockingChannel, method: Basic.Deliver,
                  props: BasicProperties, body: bytes) -> None:
        """
        Обработчик входящих RPC запросов.

        Аргументы:
            ch: Канал RabbitMQ
            method: Информация о доставке сообщения
            props: Свойства сообщения
            body: Тело сообщения
        """
        try:
            text = body.decode()
            logger.info(f"Получен RPC запрос: {text}")

            response = self.process_text(text)

            # Отправляем ответ обратно
            ch.basic_publish(
                exchange='',
                routing_key=props.reply_to,
                properties=pika.BasicProperties(correlation_id=props.correlation_id),
                body=response.encode()
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Ошибка при обработке RPC запроса: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag)
            time.sleep(0.5)  # Небольшая задержка перед следующей попыткой

    def start_consuming(self) -> None:
        """Запуск прослушивания RPC запросов."""
        try:
            if not self.channel:
                self.connect()

            # Настраиваем очередь и начинаем прослушивание
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=self.config.rpc_queue_name,
                on_message_callback=self.on_request
            )

            logger.info("Начали прослушивание RPC запросов. Нажмите Ctrl+C для выхода.")
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Завершение работы RPC обработчика...")
        except Exception as e:
            logger.error(f"Ошибка во время прослушивания: {e}")
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Безопасное закрытие соединений."""
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("Соединения успешно закрыты")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединений: {e}")
