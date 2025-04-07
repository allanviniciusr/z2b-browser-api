from pathlib import Path
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

class Task:
    """Representa uma tarefa armazenada."""
    def __init__(self, task_id: str, client_id: str, status: str, type: str, data: Dict[str, Any], result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        self.id = task_id
        self.client_id = client_id
        self.status = status
        self.type = type
        self.data = data
        self.result = result
        self.error = error
        
    def to_dict(self) -> Dict[str, Any]:
        """Converte a tarefa para um dicionário."""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "status": self.status,
            "type": self.type,
            "data": self.data,
            "result": self.result,
            "error": self.error
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Cria uma tarefa a partir de um dicionário."""
        return cls(
            task_id=data.get("id"),
            client_id=data.get("client_id"),
            status=data.get("status", "pending"),
            type=data.get("type", "prompt"),
            data=data.get("data", {}),
            result=data.get("result"),
            error=data.get("error")
        )

class StorageManager:
    """
    Gerencia o armazenamento de arquivos para clientes e tarefas.
    
    Esta classe é responsável por criar e gerenciar a estrutura de diretórios
    para armazenamento de dados de clientes e suas tarefas, incluindo logs,
    screenshots, vídeos, traces e arquivos temporários.
    """
    
    def __init__(self, client_id: str, task_id: Optional[str] = None):
        """
        Inicializa o gerenciador de armazenamento.
        
        Args:
            client_id (str): Identificador único do cliente
            task_id (Optional[str]): Identificador único da tarefa. Se None, será gerado automaticamente
        """
        self.client_id = client_id
        self.task_id = task_id or self.generate_task_id()
        self.base_path = Path("data/clients")
        self.client_path = self.base_path / self.client_id
        self.task_path = self.client_path / self.task_id
        
    def init_storage(self) -> None:
        """
        Inicializa a estrutura de diretórios necessária para o cliente e tarefa.
        
        Cria todos os diretórios necessários se eles não existirem:
        - logs/
        - screenshots/
        - videos/
        - traces/
        - tmp/
        """
        directories = [
            self.get_logs_path(),
            self.get_screenshots_path(),
            self.get_videos_path(),
            self.get_traces_path(),
            self.get_tmp_path()
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
    def get_task_path(self) -> Path:
        """
        Retorna o caminho base da tarefa atual.
        
        Returns:
            Path: Caminho completo para o diretório da tarefa
        """
        return self.task_path
    
    def get_videos_path(self) -> Path:
        """
        Retorna o caminho para o diretório de vídeos da tarefa.
        
        Returns:
            Path: Caminho para o diretório de vídeos
        """
        return self.task_path / "videos"
    
    def get_screenshots_path(self) -> Path:
        """
        Retorna o caminho para o diretório de screenshots da tarefa.
        
        Returns:
            Path: Caminho para o diretório de screenshots
        """
        return self.task_path / "screenshots"
    
    def get_logs_path(self) -> Path:
        """
        Retorna o caminho para o diretório de logs da tarefa.
        
        Returns:
            Path: Caminho para o diretório de logs
        """
        return self.task_path / "logs"
    
    def get_traces_path(self) -> Path:
        """
        Retorna o caminho para o diretório de traces da tarefa.
        
        Returns:
            Path: Caminho para o diretório de traces
        """
        return self.task_path / "traces"
    
    def get_tmp_path(self) -> Path:
        """
        Retorna o caminho para o diretório temporário da tarefa.
        
        Returns:
            Path: Caminho para o diretório temporário
        """
        return self.task_path / "tmp"
    
    async def get_task(self) -> Optional[Task]:
        """
        Recupera os dados da tarefa do armazenamento.
        
        Returns:
            Optional[Task]: Objeto Task com os dados da tarefa ou None se não existir
        """
        task_file = self.task_path / "task.json"
        if not task_file.exists():
            # Se o arquivo não existir, cria uma tarefa com valores padrão
            task = Task(
                task_id=self.task_id,
                client_id=self.client_id,
                status="pending",
                type="prompt",
                data={}
            )
            # Inicializa o armazenamento e salva a tarefa
            self.init_storage()
            await self.update_task(task)
            return task
            
        try:
            with open(task_file, "r", encoding="utf-8") as f:
                task_data = json.load(f)
                return Task.from_dict(task_data)
        except Exception as e:
            print(f"Erro ao ler arquivo de tarefa: {e}")
            return None
            
    async def update_task(self, task: Task) -> bool:
        """
        Atualiza os dados da tarefa no armazenamento.
        
        Args:
            task (Task): Objeto Task com os dados atualizados
            
        Returns:
            bool: True se a atualização foi bem-sucedida, False caso contrário
        """
        task_file = self.task_path / "task.json"
        
        # Garante que o diretório exista
        self.init_storage()
        
        try:
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(task.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erro ao atualizar arquivo de tarefa: {e}")
            return False
    
    @staticmethod
    def generate_task_id() -> str:
        """
        Gera um identificador único para uma tarefa.
        
        O ID é composto por:
        - Timestamp atual (YYYYMMDD_HHMMSS)
        - UUID v4 (8 primeiros caracteres)
        
        Returns:
            str: ID único da tarefa no formato YYYYMMDD_HHMMSS_UUID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}" 