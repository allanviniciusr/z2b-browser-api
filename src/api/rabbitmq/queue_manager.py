import aio_pika
from aio_pika.abc import AbstractQueue, AbstractChannel
from typing import Dict, Any, Optional
import json
from src.api.rabbitmq.connection import RabbitMQConnection

class QueueManager:
    def __init__(self):
        self.connection = RabbitMQConnection()
        self.queues: Dict[str, AbstractQueue] = {}

    async def declare_queue(self, queue_name: str, routing_key: str) -> AbstractQueue:
        """Declara uma nova fila e a vincula ao exchange"""
        channel = await self.connection.get_channel()
        exchange = await self.connection.get_exchange()

        # Declara a fila como durável
        queue = await channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                "x-message-ttl": 86400000,  # 24 horas em milissegundos
                "x-dead-letter-exchange": "task_exchange",
                "x-dead-letter-routing-key": f"{queue_name}.dead"
            }
        )

        # Vincula a fila ao exchange com o routing key
        await queue.bind(exchange, routing_key)
        self.queues[queue_name] = queue
        return queue

    async def publish_task(self, queue_name: str, task_data: Dict[str, Any]) -> None:
        """Publica uma tarefa na fila especificada"""
        exchange = await self.connection.get_exchange()
        routing_key = f"task.{queue_name}"

        # Garante que a fila existe
        if queue_name not in self.queues:
            await self.declare_queue(queue_name, routing_key)

        # Publica a mensagem
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(task_data).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=routing_key
        )

    async def get_queue_info(self, queue_name: str) -> Dict[str, Any]:
        """Obtém informações sobre uma fila específica"""
        channel = await self.connection.get_channel()
        queue = await channel.declare_queue(queue_name, passive=True)
        
        return {
            "name": queue_name,
            "messages": queue.declaration_result.message_count,
            "consumers": queue.declaration_result.consumer_count
        }

    async def get_all_queues(self) -> Dict[str, Dict[str, Any]]:
        """Obtém informações sobre todas as filas"""
        channel = await self.connection.get_channel()
        queues = {}
        
        for queue_name in self.queues:
            queues[queue_name] = await self.get_queue_info(queue_name)
            
        return queues 