import asyncio
import json
import logging
from typing import Dict, Any, Callable, Optional
from aio_pika import connect_robust, Message
from src.api.rabbitmq.connection import RabbitMQConnection

logger = logging.getLogger(__name__)

class TaskConsumer:
    def __init__(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Inicializa o consumidor de tarefas
        
        Args:
            callback: Função opcional que será chamada quando uma mensagem for recebida
        """
        self.connection = RabbitMQConnection()
        self.callback = callback
        self.running = False
        self.consumers = {}

    async def start(self):
        """Inicia o consumidor"""
        self.running = True
        logger.info("Iniciando consumidor de tarefas")
        
        # Conecta ao RabbitMQ
        await self.connection.connect()
        
        # Inicia o loop de consumo
        asyncio.create_task(self._consume_loop())

    async def stop(self):
        """Para o consumidor"""
        self.running = False
        logger.info("Parando consumidor de tarefas")
        
        # Fecha a conexão
        await self.connection.close()

    async def subscribe_to_queue(self, queue_name: str):
        """
        Inscreve-se em uma fila específica
        
        Args:
            queue_name: Nome da fila
        """
        if queue_name in self.consumers:
            logger.info(f"Já inscrito na fila {queue_name}")
            return
        
        try:
            # Obtém o canal e o exchange
            channel = await self.connection.get_channel()
            exchange = await self.connection.get_exchange()
            
            # Declara a fila
            queue = await channel.declare_queue(
                queue_name,
                durable=True,
                arguments={
                    "x-message-ttl": 86400000,  # 24 horas em milissegundos
                    "x-dead-letter-exchange": "task_exchange",
                    "x-dead-letter-routing-key": f"{queue_name}.dead"
                }
            )
            
            # Vincula a fila ao exchange
            routing_key = f"task.{queue_name}"
            await queue.bind(exchange, routing_key)
            
            # Inicia o consumo
            consumer = await queue.consume(self._message_handler)
            self.consumers[queue_name] = consumer
            
            logger.info(f"Inscrito na fila {queue_name}")
        except Exception as e:
            logger.error(f"Erro ao se inscrever na fila {queue_name}: {str(e)}")

    async def unsubscribe_from_queue(self, queue_name: str):
        """
        Cancela a inscrição de uma fila específica
        
        Args:
            queue_name: Nome da fila
        """
        if queue_name not in self.consumers:
            logger.info(f"Não inscrito na fila {queue_name}")
            return
        
        try:
            # Cancela o consumo
            consumer = self.consumers[queue_name]
            await consumer.cancel()
            del self.consumers[queue_name]
            
            logger.info(f"Inscrição cancelada na fila {queue_name}")
        except Exception as e:
            logger.error(f"Erro ao cancelar inscrição na fila {queue_name}: {str(e)}")

    async def _consume_loop(self):
        """Loop principal de consumo"""
        while self.running:
            try:
                # Verifica se a conexão está ativa
                if not self.connection._connection or self.connection._connection.is_closed:
                    await self.connection.connect()
                
                await asyncio.sleep(1)  # Evita consumo excessivo de CPU
            except Exception as e:
                logger.error(f"Erro no loop de consumo: {str(e)}")
                await asyncio.sleep(5)  # Espera mais tempo em caso de erro

    async def _message_handler(self, message: Message):
        """
        Manipula mensagens recebidas
        
        Args:
            message: Mensagem recebida
        """
        try:
            # Processa a mensagem
            body = message.body.decode()
            data = json.loads(body)
            
            logger.info(f"Mensagem recebida: {data}")
            
            # Chama o callback se existir
            if self.callback:
                self.callback(data)
            
            # Confirma a mensagem
            await message.ack()
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}")
            # Rejeita a mensagem e a envia para a fila de dead letter
            await message.reject(requeue=False) 