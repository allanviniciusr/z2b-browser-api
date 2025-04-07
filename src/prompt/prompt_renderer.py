"""
Renderizador de prompts com dados contextuais para uso em LLMs.

Este módulo é responsável por renderizar templates de prompts
substituindo variáveis por valores de contexto específicos.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Union, Callable
from string import Template


logger = logging.getLogger(__name__)


class PromptRenderer:
    """
    Renderiza prompts com dados contextuais para uso em LLMs.
    
    Esta classe é responsável por:
    1. Substituir variáveis em templates por valores de contexto
    2. Processar lógica condicional em templates
    3. Formatar o prompt final para uso em diferentes LLMs
    """
    
    def __init__(self):
        """
        Inicializa o renderizador de prompts.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.filters = {
            "json": self._filter_json,
            "uppercase": self._filter_uppercase,
            "lowercase": self._filter_lowercase,
            "trim": self._filter_trim,
            "strip": self._filter_trim  # Alias para trim
        }
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """
        Renderiza um template com dados contextuais.
        
        Args:
            template: Template a ser renderizado
            context: Dados contextuais para substituição
            
        Returns:
            str: Prompt renderizado
        """
        try:
            # Processar loops
            rendered = self._process_loops(template, context)
            
            # Processar condicionais
            rendered = self._process_conditionals(rendered, context)
            
            # Substituir variáveis simples (estilo {{var}})
            rendered = self._replace_variables(rendered, context)
            
            # Aplicar filtros (estilo {{var|filter}})
            rendered = self._apply_filters(rendered, context)
            
            # Limpeza final (remover linhas vazias extras)
            rendered = self._clean_output(rendered)
            
            return rendered
        except Exception as e:
            self.logger.error(f"Erro ao renderizar template: {str(e)}")
            # Fallback para substituição básica
            return self._simple_replace(template, context)
    
    def _simple_replace(self, template: str, context: Dict[str, Any]) -> str:
        """
        Realiza substituição simples de variáveis usando string.Template.
        
        Args:
            template: Template a ser renderizado
            context: Dados contextuais para substituição
            
        Returns:
            str: Texto com variáveis substituídas
        """
        try:
            # Converter {{var}} para ${var} para usar com string.Template
            template_str = re.sub(r'\{\{\s*(\w+)\s*\}\}', r'${\1}', template)
            
            # Criar Template e substituir
            t = Template(template_str)
            return t.safe_substitute(context)
        except Exception as e:
            self.logger.error(f"Erro na substituição simples: {str(e)}")
            return template
    
    def _replace_variables(self, template: str, context: Dict[str, Any]) -> str:
        """
        Substitui variáveis no formato {{var}} por seus valores.
        
        Args:
            template: Template a ser processado
            context: Dados contextuais
            
        Returns:
            str: Template com variáveis substituídas
        """
        def replace_var(match):
            var_name = match.group(1).strip()
            if var_name in context:
                value = context[var_name]
                return str(value) if value is not None else ""
            return match.group(0)  # Manter original se não encontrado
        
        return re.sub(r'\{\{\s*([^|{}]+?)\s*\}\}', replace_var, template)
    
    def _apply_filters(self, template: str, context: Dict[str, Any]) -> str:
        """
        Aplica filtros a variáveis no formato {{var|filter}}.
        
        Args:
            template: Template a ser processado
            context: Dados contextuais
            
        Returns:
            str: Template com filtros aplicados
        """
        def apply_filter(match):
            var_parts = match.group(1).split('|')
            var_name = var_parts[0].strip()
            
            if var_name not in context:
                return match.group(0)  # Manter original se variável não encontrada
            
            value = context[var_name]
            
            # Aplicar filtros em sequência
            for i in range(1, len(var_parts)):
                filter_name = var_parts[i].strip()
                if filter_name in self.filters:
                    value = self.filters[filter_name](value)
            
            return str(value) if value is not None else ""
        
        return re.sub(r'\{\{\s*([^{}]+?)\s*\}\}', apply_filter, template)
    
    def _process_loops(self, template: str, context: Dict[str, Any]) -> str:
        """
        Processa loops no formato {% for item in items %} ... {% endfor %}.
        
        Args:
            template: Template a ser processado
            context: Dados contextuais
            
        Returns:
            str: Template com loops processados
        """
        # Encontrar todos os loops no template usando regex
        loop_pattern = r'{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%}(.*?){%\s*endfor\s*%}'
        
        # Função para processar cada loop encontrado
        def process_loop(match):
            loop_var = match.group(1).strip()  # item
            collection_var = match.group(2).strip()  # items
            loop_content = match.group(3)
            
            # Verificar se a coleção existe no contexto
            if collection_var not in context:
                return ""  # Remover loop se coleção não existir
            
            collection = context[collection_var]
            if not isinstance(collection, (list, tuple, dict)):
                return ""  # Remover loop se não for uma coleção
            
            # Construir resultado do loop
            result = []
            
            if isinstance(collection, (list, tuple)):
                for item in collection:
                    # Criar novo conteúdo para este item
                    item_content = loop_content
                    
                    # Substituir as variáveis no formato {{item.name}} ou {{item.value}}
                    # Lidando especificamente com dicionários
                    if isinstance(item, dict):
                        for key, value in item.items():
                            placeholder = f"{{{{\\s*{loop_var}\\.{key}\\s*}}}}"
                            replacement = str(value) if value is not None else ""
                            item_content = re.sub(placeholder, replacement, item_content)
                    
                    result.append(item_content)
            else:  # dict
                for key, value in collection.items():
                    # Criar novo conteúdo para este item
                    item_content = loop_content
                    
                    # Substituir {{item.key}} pelo valor da chave
                    item_content = re.sub(
                        f"{{{{\\s*{loop_var}\\.key\\s*}}}}",
                        str(key),
                        item_content
                    )
                    
                    # Substituir {{item.value}} pelo valor
                    item_content = re.sub(
                        f"{{{{\\s*{loop_var}\\.value\\s*}}}}",
                        str(value) if value is not None else "",
                        item_content
                    )
                    
                    result.append(item_content)
            
            return "".join(result)
        
        # Processar todos os loops encontrados
        result = template
        while re.search(loop_pattern, result, re.DOTALL):
            result = re.sub(loop_pattern, process_loop, result, flags=re.DOTALL)
        
        return result
    
    def _process_conditionals(self, template: str, context: Dict[str, Any]) -> str:
        """
        Processa condicionais no formato {% if condition %} ... {% endif %}.
        
        Args:
            template: Template a ser processado
            context: Dados contextuais
            
        Returns:
            str: Template com condicionais processados
        """
        def process_conditional(match):
            condition = match.group(1).strip()
            if_content = match.group(2)
            else_content = match.group(4) if match.group(3) else None
            
            # Avaliar condição
            condition_met = self._evaluate_condition(condition, context)
            
            if condition_met:
                return if_content
            elif else_content:
                return else_content
            else:
                return ""
        
        # Processar condicionais if/else
        pattern = r'{%\s*if\s+(.+?)\s*%}(.*?)(?:{%\s*else\s*%}(.*?))?{%\s*endif\s*%}'
        return re.sub(pattern, process_conditional, template, flags=re.DOTALL)
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Avalia uma condição simples.
        
        Args:
            condition: Condição a ser avaliada
            context: Dados contextuais
            
        Returns:
            bool: Resultado da avaliação
        """
        try:
            # Suporte para verificação de existência
            if 'exists' in condition:
                var_name = re.search(r'(\w+)\s+exists', condition)
                if var_name:
                    return var_name.group(1) in context
            
            # Verificação de igualdade
            if '==' in condition:
                parts = condition.split('==')
                left = parts[0].strip()
                right = parts[1].strip()
                
                left_val = context.get(left, left)
                right_val = context.get(right, right)
                
                # Remover aspas se forem strings literais
                if isinstance(right_val, str) and right_val.startswith('"') and right_val.endswith('"'):
                    right_val = right_val[1:-1]
                
                return left_val == right_val
            
            # Verificação de desigualdade
            if '!=' in condition:
                parts = condition.split('!=')
                left = parts[0].strip()
                right = parts[1].strip()
                
                left_val = context.get(left, left)
                right_val = context.get(right, right)
                
                # Remover aspas se forem strings literais
                if isinstance(right_val, str) and right_val.startswith('"') and right_val.endswith('"'):
                    right_val = right_val[1:-1]
                
                return left_val != right_val
            
            # Verificação de valor booleano
            var_name = condition.strip()
            var_value = context.get(var_name, False)
            return bool(var_value)
            
        except Exception as e:
            self.logger.error(f"Erro ao avaliar condição '{condition}': {str(e)}")
            return False
    
    def _clean_output(self, text: str) -> str:
        """
        Limpa o texto final, removendo linhas vazias extras.
        
        Args:
            text: Texto a ser limpo
            
        Returns:
            str: Texto limpo
        """
        # Remover linhas vazias consecutivas
        return re.sub(r'\n{3,}', '\n\n', text)
    
    # Implementação de filtros
    
    def _filter_json(self, value: Any) -> str:
        """Converte valor para JSON."""
        import json
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erro ao converter para JSON: {str(e)}")
            return str(value)
    
    def _filter_uppercase(self, value: Any) -> str:
        """Converte valor para maiúsculas."""
        try:
            return str(value).upper()
        except Exception as e:
            self.logger.error(f"Erro ao converter para maiúsculas: {str(e)}")
            return str(value)
    
    def _filter_lowercase(self, value: Any) -> str:
        """Converte valor para minúsculas."""
        try:
            return str(value).lower()
        except Exception as e:
            self.logger.error(f"Erro ao converter para minúsculas: {str(e)}")
            return str(value)
    
    def _filter_trim(self, value: Any) -> str:
        """Remove espaços extras no início e fim."""
        try:
            return str(value).strip()
        except Exception as e:
            self.logger.error(f"Erro ao remover espaços: {str(e)}")
            return str(value)
    
    def register_filter(self, name: str, filter_func: Callable) -> None:
        """
        Registra um filtro personalizado.
        
        Args:
            name: Nome do filtro
            filter_func: Função do filtro
        """
        self.filters[name] = filter_func 