"""
Biblioteca de templates de prompts para diferentes situações.

Este módulo mantém uma coleção de templates de prompts 
que podem ser carregados de arquivos ou definidos programaticamente.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path


logger = logging.getLogger(__name__)


class PromptLibrary:
    """
    Mantém uma biblioteca de templates de prompts para diferentes situações.
    
    Esta classe é responsável por:
    1. Carregar templates de prompts de arquivos
    2. Armazenar templates em memória
    3. Fornecer acesso aos templates por nome ou categoria
    4. Manter versionamento de templates
    """
    
    def __init__(
        self, 
        library_path: Optional[str] = None,
        custom_library: Optional[Dict[str, Any]] = None
    ):
        """
        Inicializa a biblioteca de prompts.
        
        Args:
            library_path: Caminho para o diretório contendo templates de prompts
            custom_library: Biblioteca personalizada de prompts fornecida diretamente
        """
        self.library_path = library_path or os.path.join(os.path.dirname(__file__), "templates")
        self.templates = custom_library or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Carregar templates padrão
        self._load_default_templates()
        
        # Carregar templates do disco se o caminho existir
        if os.path.exists(self.library_path):
            self.load_from_directory(self.library_path)
    
    def _load_default_templates(self) -> None:
        """
        Carrega templates padrão embutidos.
        """
        # Template de sistema padrão
        self.templates["system_default"] = """
        Você é um agente de automação web especializado em executar tarefas em navegadores. 
        Você deve analisar páginas web, interagir com elementos e extrair informações conforme solicitado.
        
        Ao executar tarefas, siga estas orientações:
        1. Analise cuidadosamente a estrutura da página atual
        2. Identifique os elementos relevantes para a tarefa
        3. Execute as ações necessárias (clicar, digitar, navegar)
        4. Verifique se as ações foram bem-sucedidas
        5. Extraia e formate os dados conforme solicitado
        
        Utilize as ferramentas disponíveis para interagir com o navegador e execute a tarefa da forma mais eficiente possível.
        """
        
        # Template de navegação
        self.templates["task_navigation"] = """
        Navegue para a URL: {{url}}
        
        Depois de carregar a página:
        1. Verifique se a página carregou corretamente
        2. Analise o conteúdo principal
        3. Identifique os elementos de navegação principais
        
        {{additional_instructions}}
        """
        
        # Template de extração
        self.templates["task_extraction"] = """
        Extraia as seguintes informações da página atual:
        
        {% for field in fields %}
        - {{field.name}}: {{field.description}}
        {% endfor %}
        
        Retorne os dados extraídos em formato JSON.
        
        {{additional_instructions}}
        """
        
        # Template de preenchimento de formulário
        self.templates["task_form"] = """
        Preencha o formulário na página atual com os seguintes dados:
        
        {% for field in form_data %}
        - Campo "{{field.name}}": {{field.value}}
        {% endfor %}
        
        Após preencher todos os campos, {{submission_action}}.
        
        {{additional_instructions}}
        """
        
        # Template de melhoria geral
        self.templates["enhance_general"] = """
        {{base_prompt}}
        
        Instruções adicionais:
        * Documento cada passo da sua execução
        * Se encontrar erros, tente abordagens alternativas
        * Registre quaisquer problemas ou limitações encontrados
        """
        
        # Template de melhoria detalhada
        self.templates["enhance_detail"] = """
        {{base_prompt}}
        
        Execute esta tarefa com atenção especial aos detalhes:
        1. Documente o estado inicial da página
        2. Para cada ação, verifique se foi bem-sucedida antes de prosseguir
        3. Captura screenshots em pontos críticos da operação
        4. Valide os dados antes de submeter qualquer formulário
        5. Registre o estado final e o resultado da operação
        """
    
    def get_template(self, name: str) -> Optional[str]:
        """
        Obtém um template pelo nome.
        
        Args:
            name: Nome do template
            
        Returns:
            str: Conteúdo do template ou None se não encontrado
        """
        return self.templates.get(name)
    
    def get_templates_by_category(self, category: str) -> Dict[str, str]:
        """
        Obtém todos os templates de uma categoria específica.
        
        Args:
            category: Categoria dos templates (system, task, enhance)
            
        Returns:
            Dict[str, str]: Dicionário de templates da categoria
        """
        return {k: v for k, v in self.templates.items() if k.startswith(f"{category}_")}
    
    def register_template(self, name: str, template: str) -> bool:
        """
        Registra um novo template na biblioteca.
        
        Args:
            name: Nome do template
            template: Conteúdo do template
            
        Returns:
            bool: True se o registro foi bem-sucedido, False caso contrário
        """
        try:
            self.templates[name] = template
            return True
        except Exception as e:
            self.logger.error(f"Erro ao registrar template '{name}': {str(e)}")
            return False
    
    def save_template(self, name: str, template: str, version: str = "latest") -> bool:
        """
        Salva um template em disco.
        
        Args:
            name: Nome do template
            template: Conteúdo do template
            version: Versão do template
            
        Returns:
            bool: True se o salvamento foi bem-sucedido, False caso contrário
        """
        try:
            # Registrar na memória
            self.register_template(name, template)
            
            # Verificar se o diretório existe
            if not os.path.exists(self.library_path):
                os.makedirs(self.library_path, exist_ok=True)
            
            # Determinar caminho do arquivo
            template_dir = os.path.join(self.library_path, name.split('_')[0])
            if not os.path.exists(template_dir):
                os.makedirs(template_dir, exist_ok=True)
            
            # Salvar arquivo
            file_path = os.path.join(template_dir, f"{name}_{version}.txt")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(template)
            
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar template '{name}': {str(e)}")
            return False
    
    def load_from_directory(self, directory: str) -> int:
        """
        Carrega templates de um diretório.
        
        Args:
            directory: Caminho para o diretório contendo templates
            
        Returns:
            int: Número de templates carregados
        """
        count = 0
        try:
            # Percorrer diretório e carregar arquivos
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith('.txt') or file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        
                        # Extrair nome do template do nome do arquivo
                        name_parts = file.split('_')
                        if len(name_parts) >= 2:
                            # Remover extensão e versão
                            template_type = os.path.basename(root)
                            template_name = name_parts[0]
                            name = f"{template_type}_{template_name}"
                            
                            # Carregar conteúdo
                            with open(file_path, 'r', encoding='utf-8') as f:
                                template = f.read()
                            
                            # Registrar template
                            self.register_template(name, template)
                            count += 1
            
            return count
        except Exception as e:
            self.logger.error(f"Erro ao carregar templates do diretório '{directory}': {str(e)}")
            return count
    
    def reload(self) -> int:
        """
        Recarrega todos os templates do disco.
        
        Returns:
            int: Número de templates carregados
        """
        # Limpar templates existentes, mas manter os padrão
        default_templates = {k: v for k, v in self.templates.items() if k in [
            "system_default", "task_navigation", "task_extraction", 
            "task_form", "enhance_general", "enhance_detail"
        ]}
        
        self.templates = default_templates.copy()
        
        # Recarregar do disco
        return self.load_from_directory(self.library_path) 