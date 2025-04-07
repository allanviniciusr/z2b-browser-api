from typing import Dict, Any, Optional
import uuid
from datetime import datetime
import asyncio
from src.api.rabbitmq.queue_manager import QueueManager
from src.api.models.task import TaskRequest, TaskResponse, TaskStatus, QueueInfo, LLMOptions
from src.agent.agent import Agent
import logging
import traceback
from src.storage.storage_manager import StorageManager
from src.api.rabbitmq.event_publisher import EventPublisher

logger = logging.getLogger(__name__)

class TaskService:
    def __init__(self):
        """Inicializa o serviço de tarefas"""
        self.tasks = {}
        self.queue_manager = QueueManager()
        self.agents = {}
        # Configurações globais do LLM que podem ser modificadas via API
        self.llm_settings = {
            "api_url": None,
            "api_key": None
        }
        self.event_publisher = EventPublisher()
        self.logger = logger

    async def create_task(self, task_request: TaskRequest) -> TaskResponse:
        """
        Cria uma nova tarefa e a envia para processamento
        """
        # Gera um ID único para a tarefa
        task_id = f"task_{len(self.tasks) + 1}"
        self.logger.info(f"Criando tarefa com ID: {task_id}")
        
        # Armazena a tarefa
        task_data = {
            "client_id": task_request.client_id,
            "status": "pending",
            "data": task_request.data.dict(),  # Convertendo TaskData para dict
            "type": task_request.task_type
        }
        
        # Adiciona configurações de LLM se presentes na requisição
        if task_request.llm_options:
            task_data["llm_options"] = task_request.llm_options.dict(exclude_none=True)
            self.logger.info(f"Configurações de LLM recebidas: {task_data['llm_options']}")
        
        # Armazena a tarefa
        self.tasks[task_id] = task_data
        self.logger.info(f"Tarefa armazenada: {self.tasks[task_id]}")
        
        # Cria a fila e publica a tarefa no RabbitMQ
        try:
            await self.queue_manager.publish_task(task_id, self.tasks[task_id])
            self.logger.info(f"Tarefa publicada no RabbitMQ: {task_id}")
        except Exception as e:
            self.logger.error(f"Erro ao publicar tarefa no RabbitMQ: {str(e)}")
            self.logger.error(traceback.format_exc())
        
        # Obtém informações da fila após criá-la
        try:
            queue_data = await self.queue_manager.get_queue_info(task_id)
            self.logger.info(f"Informações da fila obtidas: {queue_data}")
            
            # Mapeia os campos do RabbitMQ para nosso modelo QueueInfo
            queue_info = QueueInfo(
                queue_name=queue_data["name"],
                position=queue_data["messages"],
                estimated_time=f"{queue_data['messages'] * 5}s"  # Estimativa de 5s por mensagem
            )
        except Exception as e:
            self.logger.error(f"Erro ao obter informações da fila: {str(e)}")
            self.logger.error(traceback.format_exc())
            queue_info = None
        
        # Inicia o processamento da tarefa em background
        try:
            self.logger.info(f"Iniciando processamento da tarefa em background: {task_id}")
            asyncio.create_task(self.process_task(task_id))
            self.logger.info(f"Tarefa enviada para processamento em background: {task_id}")
        except Exception as e:
            self.logger.error(f"Erro ao iniciar processamento em background: {str(e)}")
            self.logger.error(traceback.format_exc())
        
        return TaskResponse(
            task_id=task_id,
            status="accepted",
            message="Tarefa criada com sucesso",
            queue_info=queue_info
        )

    async def process_task(self, task_id: str):
        """
        Processa uma tarefa com o ID fornecido.
        
        Args:
            task_id (str): ID da tarefa a ser processada
        """
        self.logger.info(f"Iniciando processamento da tarefa: {task_id}")
        
        if task_id not in self.tasks:
            self.logger.error(f"Tarefa não encontrada em memória: {task_id}")
            return
            
        # Obtém o client_id da tarefa armazenada
        client_id = self.tasks[task_id].get("client_id", "default")
        
        # Inicializa o storage com client_id e task_id
        storage = StorageManager(client_id=client_id, task_id=task_id)
        task = await storage.get_task()
        
        if not task:
            self.logger.error(f"Tarefa não encontrada no storage: {task_id}")
            return
        
        # Atualiza status para processando
        task.status = "processing"
        await storage.update_task(task)
        
        # Callback para publicar eventos durante o processamento
        async def callback(event_data):
            event_type = event_data.get("event_type", "")
            
            # Adiciona ids necessários se não estiverem presentes
            if "task_id" not in event_data:
                event_data["task_id"] = task_id
            if "client_id" not in event_data and task.client_id:
                event_data["client_id"] = task.client_id
                
            # Publica o evento no RabbitMQ usando o método correto
            try:
                if event_type == "task.completed":
                    await self.event_publisher.publish_task_completed(
                        task_id=event_data["task_id"],
                        client_id=event_data["client_id"],
                        result=event_data.get("data", {})
                    )
                elif event_type == "task.error":
                    await self.event_publisher.publish_task_error(
                        task_id=event_data["task_id"],
                        client_id=event_data["client_id"],
                        error=event_data.get("data", {}).get("error", "Erro desconhecido")
                    )
                elif event_type == "task.screenshot":
                    await self.event_publisher.publish_agent_event(
                        event_type=event_type,
                        task_id=event_data["task_id"],
                        client_id=event_data["client_id"],
                        data={},
                        screenshot_data=event_data.get("screenshot"),
                        current_url=event_data.get("current_url")
                    )
                else:
                    # Para outros tipos de evento, usa o publish_agent_event genérico
                    await self.event_publisher.publish_agent_event(
                        event_type=event_type,
                        task_id=event_data["task_id"],
                        client_id=event_data["client_id"],
                        data=event_data.get("data", {})
                    )
            except Exception as e:
                self.logger.error(f"Erro ao publicar evento: {str(e)}")
        
        try:
            # Cria agent com nova implementação simplificada
            agent = Agent()
            
            # Processa a tarefa com base no tipo
            result = None
            if task.type == "prompt":
                prompt = task.data.get("prompt", "")
                self.logger.info(f"Executando prompt: {prompt}")
                result = await agent.execute_prompt_task(
                    prompt=prompt,
                    client_id=task.client_id,
                    task_id=task_id,
                    callback=callback
                )
            elif task.type == "plan":
                plan = task.data.get("plan", {})
                self.logger.info(f"Executando plano com {len(plan.get('steps', []))} passos")
                # Implementar processamento de plano aqui, se necessário
                pass
            else:
                self.logger.error(f"Tipo de tarefa não suportado: {task.type}")
                result = {
                    "status": "error",
                    "error": f"Tipo de tarefa não suportado: {task.type}"
                }
            
            # Limpa o agente após a execução
            await agent.cleanup()
            
            # Atualiza o status da tarefa
            if result:
                if result.get("status") == "error":
                    task.status = "error"
                    task.error = result.get("error", "Erro não especificado")
                else:
                    task.status = "completed"
                    task.result = result
                    
                await storage.update_task(task)
                self.logger.info(f"Tarefa {task_id} concluída com status: {task.status}")
            
        except Exception as e:
            self.logger.error(f"Erro ao processar tarefa {task_id}: {str(e)}", exc_info=True)
            
            # Atualiza status para erro
            task.status = "error"
            task.error = str(e)
            await storage.update_task(task)
            
            # Publica evento de erro
            await callback({
                "event_type": "task.error",
                "data": {"error": str(e)}
            })

    async def update_llm_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza as configurações globais do LLM
        
        Args:
            settings: Dicionário com as configurações a serem atualizadas
            
        Returns:
            Dict[str, Any]: Configurações atuais
        """
        for key, value in settings.items():
            if key in self.llm_settings:
                self.llm_settings[key] = value
                self.logger.info(f"Configuração global de LLM atualizada: {key}={value}")
        
        return self.llm_settings.copy()
    
    async def get_llm_settings(self) -> Dict[str, Any]:
        """
        Retorna as configurações globais do LLM
        
        Returns:
            Dict[str, Any]: Configurações atuais
        """
        return self.llm_settings.copy()

    async def get_task_status(self, task_id: str) -> TaskResponse:
        """
        Obtém o status de uma tarefa específica
        """
        if task_id not in self.tasks:
            return TaskResponse(
                task_id=task_id,
                status="not_found",
                message="Tarefa não encontrada"
            )
        
        task = self.tasks[task_id]
        queue_data = await self.queue_manager.get_queue_info(task_id)
        
        # Mapeia os campos do RabbitMQ para nosso modelo QueueInfo
        queue_info = QueueInfo(
            queue_name=queue_data["name"],
            position=queue_data["messages"],
            estimated_time=f"{queue_data['messages'] * 5}s"  # Estimativa de 5s por mensagem
        )
        
        return TaskResponse(
            task_id=task_id,
            status=task["status"],
            message=f"Status da tarefa: {task['status']}",
            queue_info=queue_info
        )

    async def get_queue_status(self) -> dict:
        """
        Obtém o status de todas as filas
        """
        try:
            results = await self.queue_manager.get_all_queues_info()
            if not results or not isinstance(results, dict):
                # Retorna um dicionário vazio mas válido
                return {}
            return results
        except Exception as e:
            self.logger.error(f"Erro ao obter status das filas: {str(e)}")
            self.logger.error(traceback.format_exc())
            # Em caso de erro, retorna um dicionário vazio
            return {}