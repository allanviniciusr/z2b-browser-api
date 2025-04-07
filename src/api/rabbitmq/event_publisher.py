import logging
import json
import base64
from typing import Dict, Any, Optional, List
import aio_pika
import asyncio
from datetime import datetime

from src.api.rabbitmq.connection import RabbitMQConnection

logger = logging.getLogger(__name__)

class EventPublisher:
    """
    Classe para publicar eventos relacionados ao agente no RabbitMQ,
    incluindo planejamento de etapas, progresso da execução e screenshots.
    """
    def __init__(self):
        self.connection = RabbitMQConnection()
        
    async def publish_agent_event(
        self,
        event_type: str,
        task_id: str,
        client_id: str,
        data: Dict[str, Any],
        step_description: Optional[str] = None,
        screenshot_data: Optional[str] = None,
        current_url: Optional[str] = None,
        model_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Publica um evento relacionado ao agente.
        
        Args:
            event_type: Tipo do evento (task.started, task.thinking, task.action, task.screenshot, etc)
            task_id: ID da tarefa
            client_id: ID do cliente
            data: Dados específicos do evento
            step_description: Descrição da etapa atual (opcional)
            screenshot_data: Screenshot codificado em base64 (opcional)
            current_url: URL atual do navegador (opcional)
            model_info: Informações sobre o modelo LLM utilizado (opcional)
        """
        exchange = await self.connection.get_exchange()
        routing_key = f"event.{task_id}"
        
        timestamp = datetime.now().isoformat()
        
        # Construir a mensagem de evento
        event_data = {
            "event_type": event_type,
            "task_id": task_id,
            "client_id": client_id,
            "timestamp": timestamp,
            "data": data
        }
        
        # Adiciona campos opcionais se fornecidos
        if step_description:
            event_data["step_description"] = step_description
            
        if screenshot_data:
            event_data["screenshot"] = screenshot_data
            
        if current_url:
            event_data["current_url"] = current_url
            
        if model_info:
            event_data["model_info"] = model_info
        
        # Publica a mensagem
        logger.debug(f"Publicando evento {event_type} para tarefa {task_id}")
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(event_data).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=routing_key
        )
        logger.debug(f"Evento {event_type} publicado com sucesso")
    
    async def publish_task_plan(
        self,
        task_id: str,
        client_id: str,
        plan: Any,
        prompt: str,
        model_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Publica o plano inicial de execução da tarefa.
        
        Args:
            task_id: ID da tarefa
            client_id: ID do cliente
            plan: Plano de execução gerado pelo agente
            prompt: Prompt original da tarefa
            model_info: Informações sobre o modelo LLM utilizado (opcional)
        """
        # Formata o plano para garantir que seja um formato serializável
        if hasattr(plan, "model_dump"):
            plan_data = plan.model_dump()
        elif hasattr(plan, "dict"):
            plan_data = plan.dict()
        else:
            plan_data = plan
            
        data = {
            "prompt": prompt,
            "plan": plan_data
        }
        
        await self.publish_agent_event(
            event_type="task.plan",
            task_id=task_id,
            client_id=client_id,
            data=data,
            step_description="Planejamento inicial da tarefa",
            model_info=model_info
        )
    
    async def publish_task_started(
        self,
        task_id: str,
        client_id: str,
        task_data: Dict[str, Any]
    ) -> None:
        """
        Publica evento de início da tarefa.
        
        Args:
            task_id: ID da tarefa
            client_id: ID do cliente
            task_data: Dados da tarefa
        """
        await self.publish_agent_event(
            event_type="task.started",
            task_id=task_id,
            client_id=client_id,
            data=task_data,
            step_description="Tarefa iniciada"
        )
    
    async def publish_task_thinking(
        self,
        task_id: str,
        client_id: str,
        thought: str,
        model_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Publica pensamento do agente.
        
        Args:
            task_id: ID da tarefa
            client_id: ID do cliente
            thought: Pensamento do agente
            model_info: Informações sobre o modelo LLM utilizado (opcional)
        """
        data = {
            "thought": thought
        }
        
        await self.publish_agent_event(
            event_type="task.thinking",
            task_id=task_id,
            client_id=client_id,
            data=data,
            step_description="Analisando próxima ação",
            model_info=model_info
        )
    
    async def publish_task_action(
        self,
        task_id: str,
        client_id: str,
        action: Dict[str, Any],
        step_description: str,
        model_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Publica ação do agente.
        
        Args:
            task_id: ID da tarefa
            client_id: ID do cliente
            action: Ação executada
            step_description: Descrição da ação
            model_info: Informações sobre o modelo LLM utilizado (opcional)
        """
        await self.publish_agent_event(
            event_type="task.action",
            task_id=task_id,
            client_id=client_id,
            data=action,
            step_description=step_description,
            model_info=model_info
        )
    
    async def publish_task_screenshot(
        self,
        task_id: str,
        client_id: str,
        screenshot_data: str,
        current_url: str,
        step_description: Optional[str] = None
    ) -> None:
        """
        Publica screenshot do navegador.
        
        Args:
            task_id: ID da tarefa
            client_id: ID do cliente
            screenshot_data: Screenshot em base64
            current_url: URL atual
            step_description: Descrição da etapa (opcional)
        """
        data = {"url": current_url}
        
        await self.publish_agent_event(
            event_type="task.screenshot",
            task_id=task_id,
            client_id=client_id,
            data=data,
            screenshot_data=screenshot_data,
            current_url=current_url,
            step_description=step_description or "Captura de tela"
        )
    
    async def publish_task_completed(
        self,
        task_id: str,
        client_id: str,
        result: Dict[str, Any],
        screenshot_data: Optional[str] = None,
        current_url: Optional[str] = None,
        model_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Publica conclusão da tarefa.
        
        Args:
            task_id: ID da tarefa
            client_id: ID do cliente
            result: Resultado da tarefa
            screenshot_data: Screenshot final em base64 (opcional)
            current_url: URL final (opcional)
            model_info: Informações sobre o modelo LLM utilizado (opcional)
        """
        await self.publish_agent_event(
            event_type="task.completed",
            task_id=task_id,
            client_id=client_id,
            data=result,
            step_description="Tarefa concluída",
            screenshot_data=screenshot_data,
            current_url=current_url,
            model_info=model_info
        )
    
    async def publish_task_error(
        self,
        task_id: str,
        client_id: str,
        error: str,
        screenshot_data: Optional[str] = None,
        current_url: Optional[str] = None
    ) -> None:
        """
        Publica erro da tarefa.
        
        Args:
            task_id: ID da tarefa
            client_id: ID do cliente
            error: Mensagem de erro
            screenshot_data: Screenshot em base64 (opcional)
            current_url: URL atual (opcional)
        """
        data = {"error": error}
        
        await self.publish_agent_event(
            event_type="task.error",
            task_id=task_id,
            client_id=client_id,
            data=data,
            step_description="Erro durante a execução",
            screenshot_data=screenshot_data,
            current_url=current_url
        ) 