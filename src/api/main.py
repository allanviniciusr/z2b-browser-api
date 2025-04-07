import os
import sys
import logging
import asyncio

# Configurar event loop para Windows ANTES de qualquer outra importação
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import json
from dotenv import load_dotenv
from src.api.routes import task_routes
from src.api.models.task import TaskRequest, TaskResponse, TaskStatus, QueueInfo
from src.api.services.task_service import TaskService
from src.api.rabbitmq.consumer import TaskConsumer
from src.api.websocket.rabbitmq_bridge import rabbitmq_bridge, get_rabbitmq_bridge, RabbitMQWebSocketBridge
from src.api.routes.static_routes import router as static_router

# Carrega as variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=os.getenv("API_LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger("api")

# Define o gerenciador de contexto do ciclo de vida da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação FastAPI
    """
    logger.info("Inicializando aplicação...")
    
    # Define o callback para o consumidor
    async def task_callback(data: Dict[str, Any]):
        task_id = data.get("task_id")
        if task_id:
            logger.info(f"Processando tarefa {task_id} em background")
            asyncio.create_task(task_service.process_task(task_id))
    
    # Inicia o consumidor RabbitMQ em background
    task_consumer = TaskConsumer(callback=task_callback)
    consumer_task = asyncio.create_task(task_consumer.start())
    
    # Inscreve-se na fila padrão
    queue_task = asyncio.create_task(task_consumer.subscribe_to_queue("tasks_default"))
    
    # Inicia o bridge WebSocket-RabbitMQ
    bridge_task = asyncio.create_task(rabbitmq_bridge.start_rabbitmq_consumer())
    
    # Armazena as tasks para poder cancelá-las depois
    background_tasks = [consumer_task, queue_task, bridge_task]
    
    yield  # Aqui a aplicação está rodando
    
    logger.info("Encerrando aplicação...")
    
    # Encerra o bridge WebSocket-RabbitMQ
    await rabbitmq_bridge.stop_rabbitmq_consumer()
    
    # Cancela tarefas em background
    for task in background_tasks:
        if not task.done():
            task.cancel()
    
    logger.info("Aplicação encerrada com sucesso")

# Cria a aplicação FastAPI com o novo lifespan
app = FastAPI(
    title="Z2B Browser API",
    description="API para controle do navegador e processamento de tarefas",
    version="0.1.0",
    lifespan=lifespan
)

# Adiciona middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cria o serviço de tarefas
task_service = TaskService()

# Adiciona os roteadores
app.include_router(task_routes.router, prefix="/api")
app.include_router(static_router)

# Monta arquivos estáticos
app.mount("/static", StaticFiles(directory="src/api/static"), name="static")

# Endpoint WebSocket para RabbitMQ
@app.websocket("/ws/rabbitmq")
async def websocket_rabbitmq_endpoint(websocket: WebSocket, bridge: RabbitMQWebSocketBridge = Depends(get_rabbitmq_bridge)):
    """
    Endpoint WebSocket para receber eventos do RabbitMQ.
    Este endpoint é útil para a página de testes visualizar eventos em tempo real.
    """
    await bridge.handle_client(websocket)

def main():
    """
    Função principal para iniciar a aplicação com Hypercorn.
    Essa função facilita a execução direta do módulo com 'python -m src.api.main'
    ou através do arquivo de ponte na raiz com 'python main.py'.
    """
    from hypercorn.config import Config
    from hypercorn.asyncio import serve
    import asyncio
    
    config = Config()
    config.bind = [f"{os.getenv('API_HOST', '0.0.0.0')}:{int(os.getenv('API_PORT', '8000'))}"]
    config.use_reloader = True  # Equivalente ao reload=True do uvicorn
    config.accesslog = "-"  # Log para stdout
    
    # Configuração adicional para melhor performance
    config.workers = int(os.getenv("API_WORKERS", "1"))
    config.keep_alive_timeout = 75  # segundos
    
    # Executar a aplicação com hypercorn
    return asyncio.run(serve(app, config))

if __name__ == "__main__":
    from hypercorn.config import Config
    from hypercorn.asyncio import serve
    import asyncio
    
    config = Config()
    config.bind = [f"{os.getenv('API_HOST', '0.0.0.0')}:{int(os.getenv('API_PORT', '8000'))}"]
    config.use_reloader = True  # Equivalente ao reload=True do uvicorn
    config.accesslog = "-"  # Log para stdout
    
    # Configuração adicional para melhor performance
    config.workers = int(os.getenv("API_WORKERS", "1"))
    config.keep_alive_timeout = 75  # segundos
    
    # Executar a aplicação com hypercorn
    asyncio.run(serve(app, config))