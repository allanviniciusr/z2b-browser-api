"""
Base de agentes do Zap2B.

Este pacote contém as classes base e abstratas para implementação de agentes.
"""

from .agent import BaseAgent
from .task import Task
from .result import TaskResult
from .prompt import BasePrompt, SystemPrompt, PromptManager
from . import browser_utils

__all__ = [
    'BaseAgent',
    'Task',
    'TaskResult',
    'BasePrompt',
    'SystemPrompt',
    'PromptManager',
    'browser_utils'
] 