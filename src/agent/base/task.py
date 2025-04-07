"""
Modelo de tarefa para agentes.

Define a estrutura e comportamentos de tarefas executadas pelos agentes.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List


class Task:
    """
    Representa uma tarefa a ser executada pelo agente.
    """
    
    def __init__(self, id: str, type: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """
        Inicializa uma nova tarefa.
        
        Args:
            id: Identificador único da tarefa
            type: Tipo da tarefa (e.g., "prompt", "plan", "navigation")
            data: Dados específicos da tarefa
            metadata: Metadados adicionais (opcional)
        """
        self.id = id
        self.type = type
        self.data = data
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()
    
    @classmethod
    def create_prompt_task(cls, prompt: str, metadata: Optional[Dict[str, Any]] = None) -> 'Task':
        """
        Cria uma tarefa de tipo prompt.
        
        Args:
            prompt: O prompt a ser executado
            metadata: Metadados adicionais (opcional)
            
        Returns:
            Task: A tarefa criada
        """
        task_id = f"prompt_{str(uuid.uuid4())[:8]}"
        return cls(
            id=task_id,
            type="prompt",
            data={"prompt": prompt},
            metadata=metadata
        )
    
    @classmethod
    def create_plan_task(cls, plan: List[Dict[str, Any]], url: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> 'Task':
        """
        Cria uma tarefa de tipo plano.
        
        Args:
            plan: Lista de etapas do plano
            url: URL inicial para navegação (opcional)
            metadata: Metadados adicionais (opcional)
            
        Returns:
            Task: A tarefa criada
        """
        task_id = f"plan_{str(uuid.uuid4())[:8]}"
        task_data = {"plan": plan}
        
        if url:
            task_data["url"] = url
            
        return cls(
            id=task_id,
            type="plan",
            data=task_data,
            metadata=metadata
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte a tarefa para um dicionário.
        
        Returns:
            Dict[str, Any]: Representação da tarefa como dicionário
        """
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "metadata": self.metadata,
            "created_at": self.created_at
        }
    
    def to_json(self) -> str:
        """
        Converte a tarefa para uma string JSON.
        
        Returns:
            str: Representação da tarefa como JSON
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """
        Cria uma tarefa a partir de um dicionário.
        
        Args:
            data: Dicionário contendo os dados da tarefa
            
        Returns:
            Task: A tarefa criada
        """
        task = cls(
            id=data["id"],
            type=data["type"],
            data=data["data"],
            metadata=data.get("metadata", {})
        )
        task.created_at = data.get("created_at", datetime.now().isoformat())
        return task
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Task':
        """
        Cria uma tarefa a partir de uma string JSON.
        
        Args:
            json_str: String JSON contendo os dados da tarefa
            
        Returns:
            Task: A tarefa criada
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def validate(self) -> bool:
        """
        Valida se a tarefa contém os dados necessários.
        
        Returns:
            bool: True se a tarefa é válida, False caso contrário
        """
        if not self.id or not self.type or not self.data:
            return False
            
        if self.type == "prompt" and "prompt" not in self.data:
            return False
            
        if self.type == "plan" and "plan" not in self.data:
            return False
            
        return True 