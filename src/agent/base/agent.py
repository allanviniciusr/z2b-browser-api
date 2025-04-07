"""
Implementação da classe base abstrata para agentes.

Este módulo define a interface e comportamentos fundamentais para todos os agentes do sistema.
"""

import abc
import logging
import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union

from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig

from .task import Task
from .result import TaskResult


class BaseAgent(abc.ABC):
    """
    Classe base abstrata para todos os agentes do sistema.
    
    Define a interface e comportamentos fundamentais que todos os agentes devem implementar.
    """
    
    def __init__(
        self,
        task: Optional[Union[str, Task]] = None,
        browser_context: Optional[BrowserContext] = None,
        browser: Optional[Browser] = None
    ):
        """
        Inicializa o agente.
        
        Args:
            task: Tarefa a ser executada, pode ser um prompt ou objeto Task
            browser_context: Contexto do navegador já inicializado (opcional)
            browser: Instância do navegador já inicializada (opcional)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.task = task
        self.browser_context = browser_context
        self.browser = browser
        self.status = "idle"
        self.start_time = None
        self.end_time = None
    
    @abc.abstractmethod
    async def setup(self) -> bool:
        """
        Configura o ambiente do agente, inicializando recursos necessários.
        
        Returns:
            bool: True se a configuração foi bem-sucedida, False caso contrário
        """
        pass
    
    @abc.abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """
        Executa uma tarefa específica.
        
        Args:
            task: A tarefa a ser executada
            
        Returns:
            TaskResult: O resultado da execução da tarefa
        """
        pass
    
    @abc.abstractmethod
    async def cleanup(self) -> None:
        """
        Limpa recursos utilizados pelo agente.
        """
        pass
    
    async def run(self, task: Optional[Task] = None) -> TaskResult:
        """
        Configura o ambiente, executa a tarefa e limpa os recursos.
        
        Este método implementa o ciclo de vida padrão do agente:
        1. Configuração
        2. Execução da tarefa
        3. Limpeza
        
        Args:
            task: A tarefa a ser executada, se não fornecida, usa self.task
            
        Returns:
            TaskResult: O resultado da execução
        """
        self.start_time = time.time()
        self.status = "running"
        
        if task is None and isinstance(self.task, str):
            # Cria uma Task a partir do prompt
            task_id = f"task_{int(time.time())}"
            task = Task(id=task_id, type="prompt", data={"prompt": self.task})
        elif task is None and isinstance(self.task, Task):
            task = self.task
        elif task is None:
            raise ValueError("Nenhuma tarefa fornecida para execução")
        
        try:
            self.logger.info(f"Iniciando execução da tarefa: {task.id}")
            
            # Configuração do ambiente
            if not await self.setup():
                self.logger.error("Falha na configuração do ambiente")
                return TaskResult(
                    task_id=task.id,
                    status="error",
                    error="Falha na configuração do ambiente",
                    duration=time.time() - self.start_time
                )
            
            # Execução da tarefa
            result = await self.execute(task)
            return result
            
        except Exception as e:
            self.logger.error(f"Erro durante execução: {str(e)}")
            traceback.print_exc()
            return TaskResult(
                task_id=task.id if task else "unknown",
                status="error",
                error=str(e),
                duration=time.time() - self.start_time
            )
        finally:
            self.status = "completed"
            self.end_time = time.time()
            
            # Limpeza de recursos
            try:
                await self.cleanup()
            except Exception as cleanup_error:
                self.logger.error(f"Erro durante limpeza: {str(cleanup_error)}")
    
    @abc.abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """
        Retorna o status atual do agente.
        
        Returns:
            Dict[str, Any]: Informações sobre o status atual do agente
        """
        pass
    
    @abc.abstractmethod
    async def create_browser_and_context(self) -> Tuple[Browser, BrowserContext]:
        """
        Cria uma instância do navegador e um contexto.
        
        Returns:
            Tuple[Browser, BrowserContext]: Browser e BrowserContext inicializados
        """
        pass 