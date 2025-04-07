"""
Implementação de um agente de navegador.

Este módulo contém a implementação concreta de um agente que utiliza
um navegador web para executar tarefas e interagir com páginas web.
"""

import json
import logging
import os
import time
from typing import Dict, Any, Optional, List, Tuple, Union

from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig, BrowserContextWindowSize

from ..base import BaseAgent, Task, TaskResult, PromptManager, browser_utils


class BrowserAgent(BaseAgent):
    """
    Agente que utiliza um navegador web para executar tarefas.
    
    Este agente é capaz de navegar em páginas web, interagir com elementos,
    extrair informações e executar tarefas automatizadas em navegadores.
    """
    
    def __init__(
        self,
        task: Optional[Union[str, Task]] = None,
        browser_context: Optional[BrowserContext] = None,
        browser: Optional[Browser] = None,
        prompt_manager: Optional[PromptManager] = None,
        headless: bool = True,
        user_agent: Optional[str] = None,
        viewport: Optional[Dict[str, int]] = None,
        timeout: float = 60.0
    ):
        """
        Inicializa o agente de navegador.
        
        Args:
            task: Tarefa a ser executada, pode ser um prompt ou objeto Task
            browser_context: Contexto do navegador já inicializado (opcional)
            browser: Instância do navegador já inicializada (opcional)
            prompt_manager: Gerenciador de prompts (opcional)
            headless: Se True, executa o navegador em modo sem interface gráfica
            user_agent: User agent para o navegador (opcional)
            viewport: Dimensões da janela do navegador (opcional)
            timeout: Tempo máximo de espera para operações do navegador em segundos
        """
        super().__init__(task, browser_context, browser)
        
        self.prompt_manager = prompt_manager or PromptManager()
        self.headless = headless
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self.viewport = viewport or {"width": 1280, "height": 800}
        self.timeout = timeout
        self.action_history: List[Dict[str, Any]] = []
    
    async def setup(self) -> bool:
        """
        Configura o ambiente do agente, inicializando o navegador e o contexto.
        
        Returns:
            bool: True se a configuração foi bem-sucedida, False caso contrário
        """
        try:
            if not self.browser or not self.browser_context:
                self.browser, self.browser_context = await self.create_browser_and_context()
                
            self.logger.info("Navegador e contexto inicializados com sucesso.")
            return True
        except Exception as e:
            self.logger.error(f"Erro na configuração do agente: {str(e)}")
            return False
    
    async def execute(self, task: Task) -> TaskResult:
        """
        Executa uma tarefa utilizando o navegador.
        
        Args:
            task: A tarefa a ser executada
            
        Returns:
            TaskResult: O resultado da execução da tarefa
        """
        start_time = time.time()
        task_id = task.id
        
        try:
            self.logger.info(f"Executando tarefa: {task_id}")
            
            # Se a tarefa for do tipo prompt, executa como navegação
            if task.type == "prompt":
                prompt = task.data.get("prompt", "")
                result = await self._execute_prompt_task(prompt)
                
            # Se a tarefa for do tipo navigation, navega para a URL
            elif task.type == "navigation":
                url = task.data.get("url", "")
                result = await self._execute_navigation_task(url)
                
            # Se a tarefa for do tipo action, executa a ação específica
            elif task.type == "action":
                actions = task.data.get("actions", [])
                result = await self._execute_action_task(actions)
                
            # Para outros tipos de tarefas, retorna erro
            else:
                error_msg = f"Tipo de tarefa não suportado: {task.type}"
                self.logger.error(error_msg)
                return TaskResult.create_error_result(
                    task_id=task_id,
                    error=error_msg,
                    duration=time.time() - start_time
                )
                
            # Registra a execução bem-sucedida
            result.duration = time.time() - start_time
            self.logger.info(f"Tarefa {task_id} concluída em {result.duration:.2f} segundos")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro durante execução da tarefa {task_id}: {str(e)}")
            return TaskResult.create_error_result(
                task_id=task_id,
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def cleanup(self) -> None:
        """
        Limpa recursos utilizados pelo agente, fechando o navegador.
        """
        try:
            # Fecha o contexto do navegador
            if self.browser_context:
                await self.browser_context.close()
                self.browser_context = None
                self.logger.info("Contexto do navegador fechado com sucesso.")
                
            # Fecha o navegador
            if self.browser:
                await self.browser.close()
                self.browser = None
                self.logger.info("Navegador fechado com sucesso.")
                
        except Exception as e:
            self.logger.error(f"Erro ao limpar recursos: {str(e)}")
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Retorna o status atual do agente.
        
        Returns:
            Dict[str, Any]: Informações sobre o status atual do agente
        """
        status_info = {
            "status": self.status,
            "browser_ready": self.browser is not None and self.browser_context is not None,
        }
        
        if self.start_time:
            status_info["start_time"] = self.start_time
            
        if self.end_time:
            status_info["end_time"] = self.end_time
            status_info["duration"] = self.end_time - self.start_time
            
        if self.browser_context:
            try:
                url = await self.browser_context.get_current_url()
                status_info["current_url"] = url
            except:
                status_info["current_url"] = "unknown"
                
        if self.action_history:
            status_info["actions_performed"] = len(self.action_history)
            status_info["last_action"] = self.action_history[-1] if self.action_history else None
            
        return status_info
    
    async def create_browser_and_context(self) -> Tuple[Browser, BrowserContext]:
        """
        Cria uma instância do navegador e um contexto.
        
        Returns:
            Tuple[Browser, BrowserContext]: Browser e BrowserContext inicializados
        """
        # Configurações do navegador
        browser_config = BrowserConfig(
            headless=self.headless
        )
        
        # Criação do navegador
        browser = Browser(config=browser_config)
        
        # Configurações do contexto do navegador
        context_config = BrowserContextConfig(
            browser_window_size=BrowserContextWindowSize(
                width=self.viewport.get("width", 1280),
                height=self.viewport.get("height", 720)
            ),
            user_agent=self.user_agent
        )
        
        # Criação do contexto
        context = await browser.new_context(config=context_config)
        
        return browser, context
    
    async def _execute_prompt_task(self, prompt: str) -> TaskResult:
        """
        Executa uma tarefa baseada em prompt.
        
        Args:
            prompt: O prompt a ser processado
            
        Returns:
            TaskResult: O resultado da execução
        """
        # Obter a página atual
        page = await self.browser_context.get_current_page()
        
        # Extrair URL da tarefa se existir, senão usar um mecanismo de busca
        if prompt.startswith('http://') or prompt.startswith('https://'):
            url = prompt.split()[0]  # Assume que a URL é o primeiro token
            await page.goto(url)
        else:
            # Se não for uma URL, poderíamos buscar no Google, mas vamos apenas logar
            self.logger.info(f"Prompt sem URL detectada: {prompt}")
            # Exemplo: poderíamos navegar para uma busca
            search_term = prompt.replace(' ', '+')
            await page.goto(f"https://www.google.com/search?q={search_term}")
            
        # Capturar screenshot como evidência
        screenshot = await browser_utils.take_screenshot(self.browser_context)
        
        # Obter informações da página
        page_info = await browser_utils.get_page_info(self.browser_context)
        
        # Obter elementos interativos
        elements = await browser_utils.get_interactive_elements(self.browser_context)
        
        # Criar resultado
        result = TaskResult(
            task_id=f"prompt_{int(time.time())}",
            status=TaskResult.STATUS_COMPLETED,
            data={
                "url": page_info.get("url"),
                "title": page_info.get("title"),
                "elements_count": len(elements)
            }
        )
        
        # Adicionar screenshot
        result.add_screenshot(
            screenshot=screenshot,
            url=page_info.get("url"),
            title=page_info.get("title")
        )
        
        return result
    
    async def _execute_navigation_task(self, url: str) -> TaskResult:
        """
        Executa uma tarefa de navegação para uma URL.
        
        Args:
            url: A URL para navegar
            
        Returns:
            TaskResult: O resultado da navegação
        """
        try:
            # Obter a página atual
            page = await self.browser_context.get_current_page()
            
            # Navega para a URL
            await page.goto(url)
            
            # Aguarda a página carregar
            await browser_utils.wait_for_navigation(self.browser_context)
            
            # Captura screenshot
            screenshot = await browser_utils.take_screenshot(self.browser_context)
            
            # Obtém informações da página
            page_info = await browser_utils.get_page_info(self.browser_context)
            
            # Registra a ação no histórico
            self.action_history.append({
                "type": "navigation",
                "url": url,
                "timestamp": time.time()
            })
            
            # Cria o resultado
            result = TaskResult(
                task_id=f"nav_{int(time.time())}",
                status=TaskResult.STATUS_COMPLETED,
                data={
                    "url": page_info.get("url"),
                    "title": page_info.get("title")
                }
            )
            
            # Adiciona screenshot
            result.add_screenshot(
                screenshot=screenshot,
                url=page_info.get("url"),
                title=page_info.get("title")
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Erro na navegação para {url}: {str(e)}"
            self.logger.error(error_msg)
            
            return TaskResult(
                task_id=f"nav_{int(time.time())}",
                status=TaskResult.STATUS_ERROR,
                error=error_msg
            )
    
    async def _execute_action_task(self, actions: List[Dict[str, Any]]) -> TaskResult:
        """
        Executa uma sequência de ações no navegador.
        
        Args:
            actions: Lista de ações a serem executadas
            
        Returns:
            TaskResult: O resultado da execução
        """
        task_id = f"action_{int(time.time())}"
        results = []
        
        for i, action in enumerate(actions):
            action_type = list(action.keys())[0]
            action_params = action[action_type]
            
            try:
                # Executa a ação baseada no tipo
                if action_type == "click_element":
                    element_index = action_params.get("index")
                    await self._click_element(element_index)
                    results.append({"step": i, "action": "click", "status": "success"})
                    
                elif action_type == "input_text":
                    element_index = action_params.get("index")
                    text = action_params.get("text", "")
                    await self._input_text(element_index, text)
                    results.append({"step": i, "action": "input", "status": "success"})
                    
                elif action_type == "scroll":
                    amount = action_params.get("amount", 300)
                    await browser_utils.scroll_page(self.browser_context, amount)
                    results.append({"step": i, "action": "scroll", "status": "success"})
                    
                elif action_type == "wait":
                    seconds = action_params.get("seconds", 1)
                    await self.browser_context.sleep(seconds)
                    results.append({"step": i, "action": "wait", "status": "success"})
                    
                elif action_type == "navigate":
                    url = action_params.get("url")
                    page = await self.browser_context.get_current_page()
                    await page.goto(url)
                    results.append({"step": i, "action": "navigate", "status": "success"})
                    
                elif action_type == "extract_content":
                    goal = action_params.get("goal", "extract text")
                    content = await self._extract_page_content()
                    results.append({
                        "step": i,
                        "action": "extract",
                        "status": "success",
                        "content": content
                    })
                    
                else:
                    results.append({
                        "step": i,
                        "action": action_type,
                        "status": "error",
                        "error": f"Ação não suportada: {action_type}"
                    })
                    
                # Registra a ação no histórico
                self.action_history.append({
                    "type": action_type,
                    "params": action_params,
                    "timestamp": time.time()
                })
                
            except Exception as e:
                error_msg = f"Erro ao executar ação {action_type}: {str(e)}"
                self.logger.error(error_msg)
                
                results.append({
                    "step": i,
                    "action": action_type,
                    "status": "error",
                    "error": error_msg
                })
                
                # Se uma ação falhar, podemos continuar ou interromper
                # Neste caso, vamos continuar para tentar outras ações
                
        # Captura screenshot final
        try:
            screenshot = await browser_utils.take_screenshot(self.browser_context)
            page_info = await browser_utils.get_page_info(self.browser_context)
        except Exception as e:
            self.logger.error(f"Erro ao capturar screenshot final: {str(e)}")
            screenshot = None
            page_info = {"url": "unknown", "title": "unknown"}
        
        # Cria o resultado final
        result = TaskResult(
            task_id=task_id,
            status=TaskResult.STATUS_COMPLETED,
            data={
                "results": results,
                "url": page_info.get("url"),
                "title": page_info.get("title")
            }
        )
        
        # Adiciona screenshot se disponível
        if screenshot:
            result.add_screenshot(
                screenshot=screenshot,
                url=page_info.get("url"),
                title=page_info.get("title"),
                step=len(actions)
            )
            
        return result
    
    async def _click_element(self, element_index: int) -> None:
        """
        Clica em um elemento pelo índice.
        
        Args:
            element_index: Índice do elemento a ser clicado
        """
        # Obtém todos os elementos interativos
        elements = await browser_utils.get_interactive_elements(self.browser_context)
        
        # Encontra o elemento pelo índice
        target_element = None
        for element in elements:
            if element["index"] == element_index:
                target_element = element
                break
                
        if not target_element:
            raise ValueError(f"Elemento com índice {element_index} não encontrado")
            
        # Clica no elemento usando JavaScript
        selector_script = f"""
            const elements = document.querySelectorAll('button, a, input, select, textarea');
            const element = Array.from(elements).find((el, idx) => idx + 1 === {element_index});
            
            if (element) {{
                element.click();
                return true;
            }}
            
            return false;
        """
        
        clicked = await self.browser_context.execute_script(selector_script)
        
        if not clicked:
            raise ValueError(f"Não foi possível clicar no elemento com índice {element_index}")
    
    async def _input_text(self, element_index: int, text: str) -> None:
        """
        Insere texto em um elemento pelo índice.
        
        Args:
            element_index: Índice do elemento
            text: Texto a ser inserido
        """
        # Obtém todos os elementos interativos
        elements = await browser_utils.get_interactive_elements(self.browser_context)
        
        # Encontra o elemento pelo índice
        target_element = None
        for element in elements:
            if element["index"] == element_index:
                target_element = element
                break
                
        if not target_element:
            raise ValueError(f"Elemento com índice {element_index} não encontrado")
            
        # Insere texto no elemento usando JavaScript
        input_script = f"""
            const elements = document.querySelectorAll('input, textarea, select');
            const element = Array.from(elements).find((el, idx) => {{
                // Índice ajustado para corresponder ao que retornamos
                const allElements = document.querySelectorAll('button, a, input, select, textarea');
                const actualIndex = Array.from(allElements).indexOf(el) + 1;
                return actualIndex === {element_index};
            }});
            
            if (element) {{
                if (element.tagName.toLowerCase() === 'select') {{
                    // Para elementos select, tenta encontrar a opção pelo texto
                    const option = Array.from(element.options).find(opt => 
                        opt.text.toLowerCase().includes('{text.lower()}')
                    );
                    
                    if (option) {{
                        element.value = option.value;
                        const event = new Event('change', {{ bubbles: true }});
                        element.dispatchEvent(event);
                        return true;
                    }}
                }} else {{
                    // Para inputs de texto e textarea
                    element.value = '{text}';
                    const event = new Event('input', {{ bubbles: true }});
                    element.dispatchEvent(event);
                    return true;
                }}
            }}
            
            return false;
        """
        
        input_successful = await self.browser_context.execute_script(input_script)
        
        if not input_successful:
            raise ValueError(f"Não foi possível inserir texto no elemento com índice {element_index}")
    
    async def _extract_page_content(self) -> Dict[str, Any]:
        """
        Extrai conteúdo da página atual.
        
        Returns:
            Dict[str, Any]: Conteúdo extraído da página
        """
        # Extrai texto da página
        page_text = await self.browser_context.execute_script("""
            return document.body.innerText;
        """)
        
        # Extrai metadados da página
        metadata = await self.browser_context.execute_script("""
            const meta = {};
            const metaTags = document.querySelectorAll('meta');
            
            metaTags.forEach(tag => {
                if (tag.name) {
                    meta[tag.name] = tag.content;
                } else if (tag.property) {
                    meta[tag.property] = tag.content;
                }
            });
            
            return {
                title: document.title,
                meta: meta
            };
        """)
        
        # Extrai links da página
        links = await self.browser_context.execute_script("""
            const links = [];
            document.querySelectorAll('a').forEach(a => {
                if (a.href && a.href.startsWith('http')) {
                    links.push({
                        text: a.innerText.trim(),
                        href: a.href
                    });
                }
            });
            return links;
        """)
        
        return {
            "text": page_text,
            "metadata": metadata,
            "links": links
        } 