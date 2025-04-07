"""
Módulo de agentes do Zap2B.

Este pacote contém todas as implementações de agentes, incluindo bases abstratas
e implementações concretas para uso específico.
"""

from .base import BaseAgent, Task, TaskResult, BasePrompt, SystemPrompt, PromptManager, browser_utils
from .custom import BrowserAgent

__all__ = [
    'BaseAgent',
    'Task',
    'TaskResult',
    'BasePrompt',
    'SystemPrompt',
    'PromptManager',
    'browser_utils',
    'BrowserAgent'
]
