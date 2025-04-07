"""
Gerenciamento de prompts do sistema.

Este módulo é responsável por selecionar, combinar e gerenciar os templates
de prompts apropriados para diferentes situações e contextos.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from .prompt_library import PromptLibrary
from .prompt_renderer import PromptRenderer


logger = logging.getLogger(__name__)


class PromptManager:
    """
    Gerencia prompts do sistema, selecionando e combinando templates apropriados.
    
    Esta classe é responsável por:
    1. Manter uma biblioteca de templates de prompts
    2. Selecionar templates apropriados para cada situação
    3. Combinar e renderizar prompts com dados contextuais
    4. Gerenciar versionamento e atualização de prompts
    """
    
    def __init__(
        self, 
        library_path: Optional[str] = None,
        custom_library: Optional[Dict[str, Any]] = None
    ):
        """
        Inicializa o gerenciador de prompts.
        
        Args:
            library_path: Caminho para o diretório contendo templates de prompts
            custom_library: Biblioteca personalizada de prompts fornecida diretamente
        """
        self.library = PromptLibrary(library_path, custom_library)
        self.renderer = PromptRenderer()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Cache de prompts renderizados
        self._cache = {}
    
    def get_system_prompt(self, 
                          agent_type: str = "default", 
                          context: Optional[Dict[str, Any]] = None) -> str:
        """
        Obtém o prompt de sistema para um tipo específico de agente.
        
        Args:
            agent_type: Tipo de agente (default, browser, extraction, etc)
            context: Dados contextuais para renderização do prompt
            
        Returns:
            str: Prompt de sistema renderizado
        """
        try:
            # Obter template do sistema apropriado
            template_key = f"system_{agent_type}"
            template = self.library.get_template(template_key)
            
            if not template:
                self.logger.warning(f"Template de sistema '{template_key}' não encontrado, usando default")
                template = self.library.get_template("system_default")
                
                if not template:
                    self.logger.error("Template de sistema default não encontrado")
                    return "Você é um agente de automação web. Ajude o usuário a navegar e interagir com páginas web."
            
            # Renderizar o prompt com o contexto fornecido
            context = context or {}
            return self.renderer.render(template, context)
            
        except Exception as e:
            self.logger.error(f"Erro ao obter prompt de sistema: {str(e)}")
            return "Você é um agente de automação web. Ajude o usuário a navegar e interagir com páginas web."
    
    def get_task_prompt(self, 
                        task_type: str, 
                        context: Dict[str, Any]) -> str:
        """
        Obtém um prompt para um tipo específico de tarefa.
        
        Args:
            task_type: Tipo de tarefa (navigation, extraction, form, etc)
            context: Dados contextuais para renderização do prompt
            
        Returns:
            str: Prompt de tarefa renderizado
        """
        try:
            # Obter template de tarefa apropriado
            template_key = f"task_{task_type}"
            template = self.library.get_template(template_key)
            
            if not template:
                self.logger.warning(f"Template de tarefa '{template_key}' não encontrado")
                return context.get("prompt", "")
            
            # Renderizar o prompt com o contexto fornecido
            return self.renderer.render(template, context)
            
        except Exception as e:
            self.logger.error(f"Erro ao obter prompt de tarefa: {str(e)}")
            return context.get("prompt", "")
    
    def get_enhanced_prompt(self, 
                           base_prompt: str, 
                           enhancement_type: str = "general",
                           context: Optional[Dict[str, Any]] = None) -> str:
        """
        Melhora um prompt base com instruções adicionais.
        
        Args:
            base_prompt: O prompt original a ser melhorado
            enhancement_type: Tipo de melhoria (general, detail, step_by_step, etc)
            context: Dados contextuais para renderização
            
        Returns:
            str: Prompt melhorado
        """
        try:
            # Obter template de melhoria apropriado
            template_key = f"enhance_{enhancement_type}"
            template = self.library.get_template(template_key)
            
            if not template:
                self.logger.debug(f"Template de melhoria '{template_key}' não encontrado, retornando prompt original")
                return base_prompt
            
            # Configurar contexto com o prompt base
            context = context or {}
            context["base_prompt"] = base_prompt
            
            # Renderizar o prompt com o contexto fornecido
            return self.renderer.render(template, context)
            
        except Exception as e:
            self.logger.error(f"Erro ao melhorar prompt: {str(e)}")
            return base_prompt
    
    def register_custom_template(self, name: str, template: str) -> bool:
        """
        Registra um template personalizado na biblioteca.
        
        Args:
            name: Nome do template
            template: Conteúdo do template
            
        Returns:
            bool: True se o registro foi bem-sucedido, False caso contrário
        """
        try:
            return self.library.register_template(name, template)
        except Exception as e:
            self.logger.error(f"Erro ao registrar template personalizado: {str(e)}")
            return False
    
    def reload_library(self) -> bool:
        """
        Recarrega a biblioteca de templates do disco.
        
        Returns:
            bool: True se o recarregamento foi bem-sucedido, False caso contrário
        """
        try:
            self.library.reload()
            self._cache = {}  # Limpar cache após recarregar
            return True
        except Exception as e:
            self.logger.error(f"Erro ao recarregar biblioteca: {str(e)}")
            return False 