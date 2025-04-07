from pydantic import BaseModel
from typing import Dict, Any, Optional, List, Literal, Union
from src.api.llm import LLMProvider

class PromptData(BaseModel):
    prompt: str

class PlanData(BaseModel):
    steps: List[str]
    max_iterations: int = 3

class TaskData(BaseModel):
    prompt: Optional[str] = None
    plan: Optional[PlanData] = None

class LLMOptions(BaseModel):
    """Configurações do LLM que podem ser passadas na requisição"""
    provider: Optional[str] = None
    model: Optional[str] = None 
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

class TaskRequest(BaseModel):
    client_id: str
    task_type: Literal["prompt", "plan"]
    data: TaskData
    llm_options: Optional[LLMOptions] = None

class QueueInfo(BaseModel):
    queue_name: str
    position: int
    estimated_time: str

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    queue_info: Optional[QueueInfo] = None

class TaskStatus(BaseModel):
    task_id: str
    client_id: str
    status: str
    type: Literal["prompt", "plan"]
    data: TaskData
    queue_info: Optional[QueueInfo] = None