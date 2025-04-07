import aio_pika
from aio_pika import connect_robust
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractExchange
import os
from dotenv import load_dotenv
import logging

load_dotenv()

class RabbitMQConnection:
    _instance = None
    _connection: AbstractConnection = None
    _channel: AbstractChannel = None
    _exchange: AbstractExchange = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RabbitMQConnection, cls).__new__(cls)
        return cls._instance

    async def connect(self):
        """Estabelece conexão com o RabbitMQ"""
        logger = logging.getLogger(__name__)
        
        if not self._connection or self._connection.is_closed:
            rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
            # Oculta a senha para exibição no log
            safe_url = rabbitmq_url.replace(':'.join(rabbitmq_url.split(':')[1:2]), ':****')
            logger.info(f"Conectando ao RabbitMQ: {safe_url}")
            
            try:
                self._connection = await connect_robust(
                    url=rabbitmq_url,
                    timeout=30
                )
                self._channel = await self._connection.channel()
                
                # Configura exchange do tipo topic
                self._exchange = await self._channel.declare_exchange(
                    "task_exchange",
                    aio_pika.ExchangeType.TOPIC,
                    durable=True
                )
                logger.info("Conexão com RabbitMQ estabelecida com sucesso")
            except Exception as e:
                logger.error(f"Erro ao conectar ao RabbitMQ: {str(e)}")
                raise

    async def get_channel(self) -> AbstractChannel:
        """Retorna o canal atual ou cria um novo se necessário"""
        if not self._channel or self._channel.is_closed:
            await self.connect()
        return self._channel

    async def get_exchange(self) -> AbstractExchange:
        """Retorna o exchange atual ou cria um novo se necessário"""
        if not self._exchange:
            await self.connect()
        return self._exchange

    async def close(self):
        """Fecha a conexão com o RabbitMQ"""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            self._connection = None
            self._channel = None
            self._exchange = None 