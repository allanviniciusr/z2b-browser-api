import asyncio
import json
import aio_pika
import logging
import os
from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List, Any, Optional

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RabbitMQWebSocketBridge:
    """
    Bridge entre RabbitMQ e WebSocket para transmitir eventos em tempo real
    para a página de testes, mantendo o RabbitMQ como sistema de mensagens principal.
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.rabbitmq_connection = None
        self.channel = None
        self.consumer_tag = None
        self.is_running = False
    
    async def connect(self, websocket: WebSocket):
        """Estabelece conexão com um cliente WebSocket"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Nova conexão WebSocket. Total: {len(self.active_connections)}")
        
        # Se for a primeira conexão, inicia o consumidor RabbitMQ
        if len(self.active_connections) == 1:
            await self.start_rabbitmq_consumer()
    
    async def disconnect(self, websocket: WebSocket):
        """Desconecta um cliente WebSocket"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket desconectado. Restantes: {len(self.active_connections)}")
        
        # Se não houver mais conexões, para o consumidor
        if len(self.active_connections) == 0:
            await self.stop_rabbitmq_consumer()
    
    async def broadcast(self, message: str):
        """Envia mensagem para todos os clientes WebSocket conectados"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem para WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove conexões com erro
        for conn in disconnected:
            await self.disconnect(conn)
    
    async def start_rabbitmq_consumer(self):
        """Inicia o consumidor RabbitMQ que repassará mensagens para os WebSockets"""
        if self.is_running:
            return
        
        try:
            # Obtém a URL do RabbitMQ das variáveis de ambiente
            rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
            logger.info(f"Conectando ao RabbitMQ em: {rabbitmq_url.replace(':'.join(rabbitmq_url.split(':')[1:2]), ':****')}")
            
            # Conecta ao RabbitMQ
            self.rabbitmq_connection = await aio_pika.connect_robust(
                rabbitmq_url,
            )
            self.channel = await self.rabbitmq_connection.channel()
            
            # Declara a exchange para eventos de tarefas
            exchange = await self.channel.declare_exchange(
                "task_exchange", 
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            # Cria uma fila temporária para receber todos os eventos
            queue = await self.channel.declare_queue("websocket_bridge", durable=True)
            await queue.bind(exchange, "event.#")
            
            # Configura o consumidor
            self.consumer_tag = await queue.consume(self.process_rabbitmq_message)
            self.is_running = True
            
            logger.info("Consumidor RabbitMQ iniciado para bridge WebSocket")
            await self.broadcast(json.dumps({
                "type": "system",
                "message": "Conectado ao RabbitMQ - Monitorando eventos de tarefas"
            }))
            
        except Exception as e:
            logger.error(f"Erro ao iniciar consumidor RabbitMQ: {e}")
            await self.broadcast(json.dumps({
                "type": "system",
                "message": f"Erro ao conectar ao RabbitMQ: {str(e)}"
            }))
    
    async def process_rabbitmq_message(self, message: aio_pika.IncomingMessage):
        """Processa mensagens recebidas do RabbitMQ e reenvia via WebSocket"""
        async with message.process():
            try:
                # Decodifica a mensagem
                body = message.body.decode()
                routing_key = message.routing_key.decode()
                
                logger.info(f"Mensagem recebida do RabbitMQ: {routing_key}")
                
                # Repassa a mensagem para todos os WebSockets
                await self.broadcast(body)
            except Exception as e:
                logger.error(f"Erro ao processar mensagem do RabbitMQ: {e}")
    
    async def stop_rabbitmq_consumer(self):
        """Para o consumidor RabbitMQ"""
        if not self.is_running:
            return
        
        try:
            if self.channel and self.consumer_tag:
                await self.channel.cancel(self.consumer_tag)
                self.consumer_tag = None
            
            if self.rabbitmq_connection:
                await self.rabbitmq_connection.close()
                self.rabbitmq_connection = None
            
            self.is_running = False
            logger.info("Consumidor RabbitMQ parado")
        except Exception as e:
            logger.error(f"Erro ao parar consumidor RabbitMQ: {e}")
    
    async def handle_client(self, websocket: WebSocket):
        """Manipula a conexão de um cliente WebSocket"""
        await self.connect(websocket)
        
        try:
            # Enviar status inicial
            await websocket.send_json({
                "type": "system",
                "message": "Conectado ao servidor WebSocket. Aguardando eventos do RabbitMQ."
            })
            
            # Mantém a conexão ativa e processa mensagens do cliente
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    # Se o cliente enviar um comando para simular eventos
                    if message.get("command") == "simulate":
                        # Aqui você poderia publicar uma mensagem no RabbitMQ para que o agente simule eventos
                        # Por hora, apenas informamos que esta funcionalidade não está disponível
                        await websocket.send_json({
                            "type": "system",
                            "message": "A simulação de eventos deve ser feita através do RabbitMQ"
                        })
                except:
                    # Mensagem não é JSON válido, apenas log
                    logger.warning(f"Mensagem inválida recebida: {data}")
                    
        except WebSocketDisconnect:
            logger.info("WebSocket desconectado")
        except Exception as e:
            logger.error(f"Erro na conexão WebSocket: {e}")
        finally:
            await self.disconnect(websocket)

# Instância singleton do bridge
rabbitmq_bridge = RabbitMQWebSocketBridge()

# Função para obter o bridge como dependência
def get_rabbitmq_bridge():
    return rabbitmq_bridge 