"""
Modelo de resultado de tarefas.

Define a estrutura e comportamentos de resultados retornados após execução de tarefas.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Union


class TaskResult:
    """
    Representa o resultado de uma tarefa executada pelo agente.
    """
    
    STATUS_COMPLETED = "completed"
    STATUS_ERROR = "error"
    STATUS_PARTIAL = "partial"
    STATUS_TIMEOUT = "timeout"
    
    def __init__(
        self,
        task_id: str,
        status: str,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration: Optional[float] = None,
        screenshots: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Inicializa um novo resultado de tarefa.
        
        Args:
            task_id: Identificador da tarefa
            status: Status da execução (e.g., "completed", "error", "partial", "timeout")
            data: Dados retornados pela execução
            error: Mensagem de erro, caso ocorra
            duration: Duração da execução em segundos
            screenshots: Lista de screenshots capturados durante a execução
        """
        self.task_id = task_id
        self.status = status
        self.data = data or {}
        self.error = error
        self.duration = duration
        self.screenshots = screenshots or []
        self.timestamp = datetime.now().isoformat()
    
    def add_screenshot(self, screenshot: Union[bytes, str], url: Optional[str] = None, title: Optional[str] = None, step: Optional[int] = None) -> None:
        """
        Adiciona um screenshot ao resultado.
        
        Args:
            screenshot: Dados do screenshot em bytes ou string base64
            url: URL da página quando o screenshot foi capturado
            title: Título da página quando o screenshot foi capturado
            step: Número do passo da execução
        """
        import base64
        
        # Converte para base64 se necessário
        if isinstance(screenshot, bytes):
            screenshot_data = base64.b64encode(screenshot).decode('utf-8')
        else:
            screenshot_data = screenshot
            
        screenshot_info = {
            "data": screenshot_data,
            "timestamp": datetime.now().isoformat()
        }
        
        if url:
            screenshot_info["url"] = url
            
        if title:
            screenshot_info["title"] = title
            
        if step is not None:
            screenshot_info["step"] = step
            
        self.screenshots.append(screenshot_info)
    
    @classmethod
    def create_completed_result(cls, task_id: str, data: Dict[str, Any], duration: Optional[float] = None) -> 'TaskResult':
        """
        Cria um resultado de conclusão bem-sucedida.
        
        Args:
            task_id: Identificador da tarefa
            data: Dados retornados pela execução
            duration: Duração da execução em segundos
            
        Returns:
            TaskResult: O resultado criado
        """
        return cls(
            task_id=task_id,
            status=cls.STATUS_COMPLETED,
            data=data,
            duration=duration
        )
    
    @classmethod
    def create_error_result(cls, task_id: str, error: str, duration: Optional[float] = None) -> 'TaskResult':
        """
        Cria um resultado de erro.
        
        Args:
            task_id: Identificador da tarefa
            error: Mensagem de erro
            duration: Duração da execução em segundos
            
        Returns:
            TaskResult: O resultado criado
        """
        return cls(
            task_id=task_id,
            status=cls.STATUS_ERROR,
            error=error,
            duration=duration
        )
    
    def is_successful(self) -> bool:
        """
        Verifica se a execução foi bem-sucedida.
        
        Returns:
            bool: True se a execução foi bem-sucedida, False caso contrário
        """
        return self.status == self.STATUS_COMPLETED
    
    def has_error(self) -> bool:
        """
        Verifica se ocorreu algum erro durante a execução.
        
        Returns:
            bool: True se ocorreu erro, False caso contrário
        """
        return self.status == self.STATUS_ERROR and self.error is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o resultado para um dicionário.
        
        Returns:
            Dict[str, Any]: Representação do resultado como dicionário
        """
        result_dict = {
            "task_id": self.task_id,
            "status": self.status,
            "data": self.data,
            "timestamp": self.timestamp
        }
        
        if self.error:
            result_dict["error"] = self.error
            
        if self.duration is not None:
            result_dict["duration"] = self.duration
            
        if self.screenshots:
            result_dict["screenshots"] = self.screenshots
            
        return result_dict
    
    def to_json(self) -> str:
        """
        Converte o resultado para uma string JSON.
        
        Returns:
            str: Representação do resultado como JSON
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskResult':
        """
        Cria um resultado a partir de um dicionário.
        
        Args:
            data: Dicionário contendo os dados do resultado
            
        Returns:
            TaskResult: O resultado criado
        """
        result = cls(
            task_id=data["task_id"],
            status=data["status"],
            data=data.get("data", {}),
            error=data.get("error"),
            duration=data.get("duration"),
            screenshots=data.get("screenshots", [])
        )
        
        result.timestamp = data.get("timestamp", datetime.now().isoformat())
        return result
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TaskResult':
        """
        Cria um resultado a partir de uma string JSON.
        
        Args:
            json_str: String JSON contendo os dados do resultado
            
        Returns:
            TaskResult: O resultado criado
        """
        data = json.loads(json_str)
        return cls.from_dict(data) 