"""
Templates de prompts para diferentes situações.

Este módulo contém os templates de prompts utilizados pelo sistema,
incluindo prompts de sistema e prompts específicos para tarefas.
"""

from .system_prompts import SYSTEM_PROMPTS
from .task_prompts import TASK_TEMPLATES

# Exportar os dicionários de templates
__all__ = ['SYSTEM_PROMPTS', 'TASK_TEMPLATES'] 