"""
Implementação de gerenciamento de prompts base para agentes.

Este módulo define classes para gerenciar prompts e templates usados pelos agentes.
"""

import json
import os
from typing import Dict, Any, Optional, List, Union


class BasePrompt:
    """
    Classe base para representar prompts do sistema e templates de instruções.
    """
    
    def __init__(self, content: str, variables: Optional[Dict[str, Any]] = None):
        """
        Inicializa um prompt base.
        
        Args:
            content: Conteúdo do prompt ou template
            variables: Variáveis para renderização do template (opcional)
        """
        self.content = content
        self.variables = variables or {}
        
    def render(self, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Renderiza o prompt substituindo as variáveis no template.
        
        Args:
            variables: Variáveis adicionais para renderização (opcional)
            
        Returns:
            str: Prompt renderizado com as variáveis substituídas
        """
        all_variables = self.variables.copy()
        if variables:
            all_variables.update(variables)
            
        rendered_content = self.content
        
        # Substitui variáveis no formato {variable_name}
        for key, value in all_variables.items():
            placeholder = '{' + key + '}'
            rendered_content = rendered_content.replace(placeholder, str(value))
            
        return rendered_content
    
    @classmethod
    def from_file(cls, file_path: str, variables: Optional[Dict[str, Any]] = None) -> 'BasePrompt':
        """
        Cria um prompt a partir de um arquivo.
        
        Args:
            file_path: Caminho do arquivo contendo o prompt
            variables: Variáveis para renderização do template (opcional)
            
        Returns:
            BasePrompt: O prompt criado
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo de prompt não encontrado: {file_path}")
            
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        return cls(content, variables)
    
    @classmethod
    def from_string(cls, content: str, variables: Optional[Dict[str, Any]] = None) -> 'BasePrompt':
        """
        Cria um prompt a partir de uma string.
        
        Args:
            content: Conteúdo do prompt
            variables: Variáveis para renderização do template (opcional)
            
        Returns:
            BasePrompt: O prompt criado
        """
        return cls(content, variables)


class SystemPrompt(BasePrompt):
    """
    Prompt do sistema usado para definir o comportamento base do agente.
    """
    
    DEFAULT_BROWSER_AGENT_PROMPT = """
    Você é um agente de IA projetado para automatizar tarefas de navegador. Seu objetivo é realizar a tarefa final seguindo as regras.
    
    # Formato de Entrada
    Tarefa
    Passos anteriores
    URL atual
    Abas abertas
    Elementos interativos
    [índice]<tipo>texto</tipo>
    - índice: Identificador numérico para interação
    - tipo: Tipo de elemento HTML (botão, input, etc.)
    - texto: Descrição do elemento
    Exemplo:
    [33]<button>Enviar Formulário</button>
    
    - Apenas elementos com índices numéricos em [] são interativos
    - Elementos sem [] fornecem apenas contexto
    
    # Regras de Resposta
    1. FORMATO DE RESPOSTA: Você deve SEMPRE responder com JSON válido neste formato exato:
    {{
     "current_state": {{
       "evaluation_previous_goal": "Sucesso|Falha|Desconhecido - Analise os elementos atuais e a imagem para verificar se os objetivos/ações anteriores foram bem-sucedidos conforme pretendido pela tarefa. Mencione se algo inesperado aconteceu. Declare brevemente por que/por que não.",
       "important_contents": "Apresente conteúdos importantes relacionados à instrução do usuário na página atual. Se houver, apresente os conteúdos. Se não, apresente uma string vazia ''.",
       "thought": "Pense sobre os requisitos que foram concluídos em operações anteriores e os requisitos que precisam ser concluídos na próxima operação. Se a sua avaliação_objetivo_anterior for 'Falha', reflita e apresente sua reflexão aqui.",
       "next_goal": "Gere uma breve descrição em linguagem natural para o objetivo de suas próximas ações com base em seu pensamento."
     }},
     "action": [
       {{"nome_da_ação": {{// parâmetro específico da ação}}}}, // ... mais ações em sequência
     ]
    }}
    
    2. AÇÕES: Você pode especificar múltiplas ações na lista para serem executadas em sequência. Mas sempre especifique apenas um nome de ação por item. Use no máximo {{max_actions}} ações por sequência.
    Sequências de ações comuns:
    - Preenchimento de formulário: [{{"input_text": {{"index": 1, "text": "nome de usuário"}}}}, {{"input_text": {{"index": 2, "text": "senha"}}}}, {{"click_element": {{"index": 3}}}}]
    - Navegação e extração: [{{"go_to_url": {{"url": "https://exemplo.com"}}}}, {{"extract_content": {{"goal": "extrair os nomes"}}}}]
    - As ações são executadas na ordem dada
    - Se a página mudar após uma ação, a sequência é interrompida e você recebe o novo estado.
    - Forneça apenas a sequência de ações até uma ação que altere significativamente o estado da página.
    - Tente ser eficiente, por exemplo, preencha formulários de uma vez ou encadeie ações onde nada muda na página
    - use múltiplas ações apenas se fizer sentido.
    
    3. INTERAÇÃO COM ELEMENTOS:
    - Use apenas índices dos elementos interativos
    - Elementos marcados com "[]Texto não interativo" são não interativos
    
    4. NAVEGAÇÃO E TRATAMENTO DE ERROS:
    - Se não existirem elementos adequados, use outras funções para concluir a tarefa
    - Se estiver preso, tente abordagens alternativas - como voltar a uma página anterior, nova pesquisa, nova aba, etc.
    - Lide com popups/cookies aceitando-os ou fechando-os
    - Use scroll para encontrar elementos que você está procurando
    - Se quiser pesquisar algo, abra uma nova aba em vez de usar a aba atual
    - Se aparecer captcha, tente resolvê-lo - caso contrário, tente uma abordagem diferente
    - Se a página não estiver totalmente carregada, use a ação de espera
    
    5. CONCLUSÃO DA TAREFA:
    - Use a ação de conclusão como a última ação assim que a tarefa final estiver completa
    - Não use "done" antes de terminar tudo o que o usuário pediu, exceto se você atingir a última etapa de max_steps.
    - Se você atingir sua última etapa, use a ação de conclusão mesmo que a tarefa não esteja totalmente concluída. Forneça todas as informações que você coletou até agora.
    - Se tiver que fazer algo repetidamente, por exemplo, a tarefa diz "para cada", ou "para todos", ou "x vezes", conte sempre dentro da "memória" quantas vezes você fez isso e quantas restam.
    - Não invente ações
    - Certifique-se de incluir tudo o que você descobriu para a tarefa final no parâmetro de texto de conclusão.
    
    6. CONTEXTO VISUAL:
    - Quando uma imagem é fornecida, use-a para entender o layout da página
    - Caixas delimitadoras com rótulos no canto superior direito correspondem aos índices dos elementos
    
    7. Preenchimento de formulário:
    - Se você preencher um campo de entrada e sua sequência de ações for interrompida, geralmente algo mudou, por exemplo, sugestões apareceram sob o campo.
    
    8. Tarefas longas:
    - Mantenha o controle do status e subresultados na memória.
    
    9. Extração:
    - Se sua tarefa for encontrar informações - chame extract_content nas páginas específicas para obter e armazenar as informações.
    
    Suas respostas devem ser sempre JSON com o formato especificado.
    """
    
    def __init__(self, content: Optional[str] = None, variables: Optional[Dict[str, Any]] = None):
        """
        Inicializa um prompt do sistema.
        
        Args:
            content: Conteúdo do prompt (opcional, usa o padrão se não fornecido)
            variables: Variáveis para renderização do template (opcional)
        """
        if content is None:
            content = self.DEFAULT_BROWSER_AGENT_PROMPT
            
        super().__init__(content, variables)
    
    @classmethod
    def default_browser_agent(cls, max_actions: int = 5) -> 'SystemPrompt':
        """
        Cria um prompt de sistema padrão para agente de navegador.
        
        Args:
            max_actions: Número máximo de ações por sequência
            
        Returns:
            SystemPrompt: O prompt de sistema criado
        """
        return cls(cls.DEFAULT_BROWSER_AGENT_PROMPT, {"max_actions": max_actions})


class PromptManager:
    """
    Gerencia prompts e templates usados pelos agentes.
    """
    
    def __init__(self, system_prompt: Optional[SystemPrompt] = None):
        """
        Inicializa o gerenciador de prompts.
        
        Args:
            system_prompt: Prompt do sistema inicial (opcional)
        """
        self.system_prompt = system_prompt or SystemPrompt.default_browser_agent()
        self.custom_prompts: Dict[str, BasePrompt] = {}
        
    def set_system_prompt(self, prompt: Union[SystemPrompt, str]) -> None:
        """
        Define o prompt do sistema.
        
        Args:
            prompt: Novo prompt do sistema ou conteúdo do prompt
        """
        if isinstance(prompt, str):
            self.system_prompt = SystemPrompt(prompt)
        else:
            self.system_prompt = prompt
            
    def add_custom_prompt(self, name: str, prompt: Union[BasePrompt, str]) -> None:
        """
        Adiciona um prompt personalizado.
        
        Args:
            name: Nome do prompt
            prompt: Prompt personalizado ou conteúdo do prompt
        """
        if isinstance(prompt, str):
            self.custom_prompts[name] = BasePrompt(prompt)
        else:
            self.custom_prompts[name] = prompt
            
    def get_prompt(self, name: str) -> Optional[BasePrompt]:
        """
        Retorna um prompt personalizado pelo nome.
        
        Args:
            name: Nome do prompt
            
        Returns:
            Optional[BasePrompt]: O prompt encontrado ou None
        """
        return self.custom_prompts.get(name)
    
    def get_system_prompt(self, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Retorna o prompt do sistema renderizado.
        
        Args:
            variables: Variáveis adicionais para renderização (opcional)
            
        Returns:
            str: Prompt do sistema renderizado
        """
        return self.system_prompt.render(variables)
    
    def load_prompts_from_directory(self, directory_path: str) -> None:
        """
        Carrega prompts de um diretório.
        
        Args:
            directory_path: Caminho do diretório contendo os arquivos de prompt
        """
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            raise ValueError(f"Diretório de prompts não encontrado: {directory_path}")
            
        for filename in os.listdir(directory_path):
            if filename.endswith(('.txt', '.md')):
                file_path = os.path.join(directory_path, filename)
                prompt_name = os.path.splitext(filename)[0]
                
                prompt = BasePrompt.from_file(file_path)
                self.add_custom_prompt(prompt_name, prompt)
                
    def export_prompts(self, directory_path: str) -> None:
        """
        Exporta prompts para um diretório.
        
        Args:
            directory_path: Caminho do diretório para salvar os prompts
        """
        os.makedirs(directory_path, exist_ok=True)
        
        # Exporta o prompt do sistema
        system_path = os.path.join(directory_path, "system_prompt.md")
        with open(system_path, 'w', encoding='utf-8') as file:
            file.write(self.system_prompt.content)
            
        # Exporta prompts personalizados
        for name, prompt in self.custom_prompts.items():
            prompt_path = os.path.join(directory_path, f"{name}.md")
            with open(prompt_path, 'w', encoding='utf-8') as file:
                file.write(prompt.content) 