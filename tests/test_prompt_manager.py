#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testes para o módulo de gerenciamento de prompts.
"""

import os
import sys
import unittest
import json
from pathlib import Path

# Adicionar diretório pai ao path para importar módulos de src/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prompt import PromptManager, PromptLibrary, PromptRenderer
from src.prompt.templates import SYSTEM_PROMPTS, TASK_TEMPLATES


class TestPromptManager(unittest.TestCase):
    """Testes para o PromptManager."""

    def setUp(self):
        """Configuração para cada teste."""
        self.manager = PromptManager()
    
    def test_get_system_prompt_default(self):
        """Testa a obtenção do prompt de sistema padrão."""
        prompt = self.manager.get_system_prompt()
        self.assertIsNotNone(prompt)
        self.assertIn("agente de automação web", prompt.lower())
    
    def test_get_system_prompt_with_context(self):
        """Testa a obtenção do prompt de sistema com contexto."""
        context = {
            "agent_name": "TestAgent",
            "capabilities": ["navegação", "extração", "formulários"]
        }
        prompt = self.manager.get_system_prompt(context=context)
        self.assertIsNotNone(prompt)
        # Verificação básica de conteúdo
        self.assertIn("automação web", prompt)
    
    def test_get_task_prompt(self):
        """Testa a obtenção de um prompt de tarefa específica."""
        context = {
            "url": "https://example.com",
            "additional_instructions": "Verifique se o título da página contém 'Example Domain'."
        }
        prompt = self.manager.get_task_prompt("navigation", context)
        self.assertIsNotNone(prompt)
        self.assertIn("https://example.com", prompt)
        self.assertIn("Verifique se o título", prompt)
    
    def test_enhanced_prompt(self):
        """Testa a melhoria de um prompt base."""
        base_prompt = "Navegue para https://example.com e clique no link 'More information'."
        enhanced = self.manager.get_enhanced_prompt(base_prompt)
        self.assertIsNotNone(enhanced)
        self.assertIn(base_prompt, enhanced)
        self.assertIn("Instruções adicionais", enhanced)
    
    def test_custom_template_registration(self):
        """Testa o registro de templates personalizados."""
        template = "Olá {{name}}, bem-vindo ao {{service}}!"
        result = self.manager.register_custom_template("greeting", template)
        self.assertTrue(result)
        
        # Verificar se está disponível na biblioteca
        self.assertIsNotNone(self.manager.library.get_template("greeting"))


class TestPromptRenderer(unittest.TestCase):
    """Testes para o PromptRenderer."""
    
    def setUp(self):
        """Configuração para cada teste."""
        self.renderer = PromptRenderer()
    
    def test_simple_variable_replacement(self):
        """Testa a substituição simples de variáveis."""
        template = "Olá {{name}}, bem-vindo ao {{service}}!"
        context = {"name": "João", "service": "Z2B"}
        result = self.renderer.render(template, context)
        self.assertEqual(result, "Olá João, bem-vindo ao Z2B!")
    
    def test_conditional_rendering(self):
        """Testa a renderização condicional."""
        template = """
        Olá {{name}}!
        {% if is_admin %}
        Você tem acesso administrativo.
        {% else %}
        Você tem acesso regular.
        {% endif %}
        """
        # Teste com admin = True
        context_admin = {"name": "Admin", "is_admin": True}
        result_admin = self.renderer.render(template, context_admin)
        self.assertIn("acesso administrativo", result_admin)
        
        # Teste com admin = False
        context_user = {"name": "User", "is_admin": False}
        result_user = self.renderer.render(template, context_user)
        self.assertIn("acesso regular", result_user)
    
    def test_loop_rendering(self):
        """Testa a renderização de loops."""
        template = """
        Itens da lista:
        {% for item in items %}
        - {{item.name}}: {{item.value}}
        {% endfor %}
        """
        context = {
            "items": [
                {"name": "Item 1", "value": "Valor 1"},
                {"name": "Item 2", "value": "Valor 2"},
                {"name": "Item 3", "value": "Valor 3"}
            ]
        }
        result = self.renderer.render(template, context)
        self.assertIn("- Item 1: Valor 1", result)
        self.assertIn("- Item 2: Valor 2", result)
        self.assertIn("- Item 3: Valor 3", result)
    
    def test_filter_application(self):
        """Testa a aplicação de filtros."""
        template = "Nome: {{name|uppercase}}, Email: {{email|lowercase}}"
        context = {"name": "João Silva", "email": "JOAO@EXAMPLE.COM"}
        result = self.renderer.render(template, context)
        self.assertIn("Nome: JOÃO SILVA", result)
        self.assertIn("Email: joao@example.com", result)


if __name__ == "__main__":
    unittest.main() 