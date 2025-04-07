from fastapi import APIRouter, HTTPException
from src.api.models.task import TaskRequest, TaskResponse
from src.api.services.task_service import TaskService

router = APIRouter()
task_service = TaskService()

@router.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskRequest):
    """Cria uma nova tarefa"""
    return await task_service.create_task(task)

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """Obtém o status de uma tarefa específica"""
    return await task_service.get_task_status(task_id)

@router.get("/tasks/queue")
async def get_queue_status():
    """Obtém o status de todas as filas"""
    return await task_service.get_queue_status()

@router.get("/tasks/status")
async def get_tasks_status():
    """Obtém o status de todas as tarefas"""
    return task_service.tasks 