import os
import sys
import asyncio
import traceback
import json
import logging
import base64
import uuid
import time
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from dotenv import load_dotenv
from src.storage.storage_manager import StorageManager
from src.api.rabbitmq.event_publisher import EventPublisher

# Importar biblioteca browser-use com caminhos corretos
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContextWindowSize
from browser_use.agent.service import Agent as BrowserAgent
from langchain_openai import ChatOpenAI

# Importar implementação do Z2BAgent customizado
from .custom.z2b_agent import Z2BAgent
from .base.task import Task
from .base.result import TaskResult

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Verificar se estamos executando em Docker
RUNNING_IN_DOCKER = os.path.exists('/.dockerenv')
if RUNNING_IN_DOCKER:
    logger.info("Executando em ambiente Docker")
else:
    logger.info(f"Executando em ambiente local ({sys.platform})")

# Obter configurações do navegador
BROWSER_HEADLESS = os.getenv('BROWSER_HEADLESS', 'false').lower() == 'true'
BROWSER_DISABLE_SECURITY = os.getenv('BROWSER_DISABLE_SECURITY', 'true').lower() == 'true'
BROWSER_WIDTH = int(os.getenv('BROWSER_WIDTH', '1280'))
BROWSER_HEIGHT = int(os.getenv('BROWSER_HEIGHT', '720'))

# Configurações de Chrome
CHROME_CDP = os.getenv('CHROME_CDP', '')
CHROME_PATH = os.getenv('CHROME_PATH', '')
CHROME_USER_DATA = os.getenv('CHROME_USER_DATA', '')
CHROME_PERSISTENT_SESSION = os.getenv('CHROME_PERSISTENT_SESSION', 'false').lower() == 'true'

# Configurações do agente
AGENT_MAX_STEPS = int(os.getenv('AGENT_MAX_STEPS', '15'))
AGENT_USE_VISION = os.getenv('AGENT_USE_VISION', 'true').lower() == 'true'
AGENT_IMPLEMENTATION = os.getenv('AGENT_IMPLEMENTATION', 'legacy').lower()  # 'legacy' ou 'z2b'

class Task:
    """
    Representa uma tarefa a ser executada pelo agente.
    """
    def __init__(self, id: str, type: str, data: Dict[str, Any]):
        self.id = id
        self.type = type
        self.data = data

class TaskResult:
    """
    Representa o resultado de uma tarefa.
    """
    def __init__(
        self, 
        task_id: str, 
        status: str, 
        data: Optional[Dict[str, Any]] = None, 
        error: Optional[str] = None,
        duration: Optional[float] = None
    ):
        self.task_id = task_id
        self.status = status
        self.data = data or {}
        self.error = error
        self.duration = duration
        self.timestamp = datetime.now().isoformat()
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "data": self.data,
            "error": self.error,
            "duration": self.duration,
            "timestamp": self.timestamp
        }

class Agent:
    def __init__(self, prompt=None, browser_context=None):
        """
        Inicializa o agente para um prompt específico.
        
        Args:
            prompt (str): O prompt a ser executado
            browser_context: O contexto do navegador a ser usado
        """
        self.prompt = prompt
        self.browser_context = browser_context
        self.logger = logging.getLogger('agent')
        
        # Adicionar atributos ausentes para compatibilidade
        self.status = "idle"
        self.current_task = None
        self.result = None
        self.storage = None
        self.llm_config = {
            "model_name": os.getenv("LLM_MODEL_NAME", "unknown"),
            "provider": os.getenv("LLM_PROVIDER", "unknown")
        }
        
        # Instância do agente Z2B (somente se estiver configurado para isso)
        self.z2b_agent = None
        if AGENT_IMPLEMENTATION == 'z2b':
            self.logger.info("Inicializando agente com implementação Z2B")
            self._init_z2b_agent(prompt, browser_context)
        else:
            self.logger.info("Inicializando agente com implementação legada")
    
    def _init_z2b_agent(self, prompt, browser_context):
        """
        Inicializa o agente Z2B.
        
        Args:
            prompt (str): O prompt a ser executado
            browser_context: O contexto do navegador a ser usado
        """
        try:
            # Criar tarefa se houver prompt
            task = None
            if prompt:
                task = Task(
                    id=f"prompt_{uuid.uuid4().hex}",
                    type="prompt",
                    data={"prompt": prompt}
                )
            
            # Inicializar Z2BAgent
            self.z2b_agent = Z2BAgent(
                task=task,
                browser_context=browser_context,
                browser=None,  # Será criado dentro do agente se necessário
                headless=BROWSER_HEADLESS,
                viewport={"width": BROWSER_WIDTH, "height": BROWSER_HEIGHT},
                max_steps=AGENT_MAX_STEPS,
                use_vision=AGENT_USE_VISION
            )
            
            self.logger.info("Agente Z2B inicializado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao inicializar agente Z2B: {str(e)}")
            traceback.print_exc()
    
    async def create_browser_and_context(self, user_agent=None, proxy=None, viewport=None) -> Tuple[Any, Any]:
        """
        Cria uma instância do navegador e um contexto.
        
        Args:
            user_agent (str, optional): O user agent a ser usado
            proxy (Dict, optional): Configuração de proxy
            viewport (Dict, optional): Configuração de viewport
            
        Returns:
            Tuple[Any, Any]: Browser e BrowserContext
        """
        try:
            # Se estivermos usando Z2BAgent, delegamos a criação para ele
            if AGENT_IMPLEMENTATION == 'z2b' and self.z2b_agent:
                return await self.z2b_agent.create_browser_and_context()
            
            # Implementação legada
            # Configurações do navegador
            width = viewport["width"] if viewport and "width" in viewport else 1280
            height = viewport["height"] if viewport and "height" in viewport else 720
            
            # Configuração de argumentos extras para Chrome
            extra_chromium_args = [
                f"--window-size={width},{height}",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--no-sandbox",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
            
            browser_config = BrowserConfig(
                headless=True,
                disable_security=True,
                extra_chromium_args=extra_chromium_args
            )
            
            # Cria o browser
            self.logger.info("Criando instância do browser")
            browser = await self.create_browser(browser_config)
            
            # User-agent padrão se não for fornecido
            default_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            
            # Configurações do contexto
            context_config = BrowserContextConfig(
                browser_window_size=BrowserContextWindowSize(
                    width=width,
                    height=height
                ),
                user_agent=user_agent or default_user_agent
            )
            
            # Cria o contexto
            self.logger.info("Criando contexto do browser")
            browser_context = await browser.new_context(context_config)
            
            return browser, browser_context
        except Exception as e:
            self.logger.error(f"Erro ao criar browser e contexto: {str(e)}")
            traceback.print_exc()
            raise
    
    async def create_browser(self, config: BrowserConfig):
        """
        Cria uma instância do navegador.
        
        Args:
            config (BrowserConfig): Configuração do navegador
            
        Returns:
            Browser: A instância do navegador
        """
        browser = Browser(config=config)
        return browser
    
    async def execute_prompt_task(self, prompt, client_id=None, task_id=None, callback=None):
        """
        Executa um prompt no navegador.
        
        Args:
            prompt (str): O prompt a ser executado
            client_id (str, optional): ID do cliente
            task_id (str, optional): ID da tarefa
            callback (callable, optional): Função de callback para atualizações
            
        Returns:
            Dict: Resultados da execução
        """
        self.logger.info(f"Executando prompt: {prompt}")
        
        # Verificar se devemos usar a implementação Z2B
        if AGENT_IMPLEMENTATION == 'z2b' and self.z2b_agent:
            return await self._execute_prompt_with_z2b(prompt, client_id, task_id, callback)
        
        # Continuar com a implementação legada
        if not self.browser_context:
            self.logger.info("Browser context não fornecido, criando um novo")
            browser, browser_context = await self.create_browser_and_context()
            self.browser = browser
            self.browser_context = browser_context
        
        try:
            # Executa o prompt em passos
            await self._execute_prompt_task(prompt, client_id, task_id, callback)
            
            # Captura screenshot final e URL
            self.logger.info("Capturando screenshot final")
            active_page = await self.browser_context.get_current_page()
            
            if active_page:
                final_screenshot = await active_page.screenshot()
                final_url = active_page.url
                encoded_screenshot = base64.b64encode(final_screenshot).decode('utf-8')
                
                result = {
                    "status": "completed",
                    "screenshot": encoded_screenshot,
                    "current_url": final_url
                }
                
                # Envia atualização final
                if callback:
                    await callback({
                        "event_type": "task.completed",
                        "task_id": task_id,
                        "client_id": client_id,
                        "data": result,
                        "screenshot": encoded_screenshot,
                        "current_url": final_url
                    })
                
                return result
            else:
                self.logger.warning("Não foi possível obter a página ativa para capturar o screenshot final")
                return {"status": "completed", "warning": "Não foi possível capturar screenshot final"}
                
        except Exception as e:
            self.logger.error(f"Erro ao executar tarefa: {str(e)}")
            traceback.print_exc()
            
            error_result = {
                "status": "error",
                "error": str(e)
            }
            
            # Envia erro para o callback
            if callback:
                await callback({
                    "event_type": "task.error",
                    "task_id": task_id,
                    "client_id": client_id,
                    "data": {"error": str(e)}
                })
            
            return error_result
    
    async def _execute_prompt_task(self, prompt, client_id=None, task_id=None, callback=None):
        """
        Executa um prompt no navegador usando o engine browser-use.
        """
        try:
            # Obtém a chave da API do provedor LLM configurado no ambiente
            llm_provider = os.getenv("LLM_PROVIDER", "openrouter")
            api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("LLM_API_KEY ou OPENAI_API_KEY não está definida. Configure no arquivo .env")
            
            # Configura o modelo de linguagem
            model_name = os.getenv("LLM_MODEL_NAME") or os.getenv("OPENAI_MODEL", "gpt-4o")
            base_url = os.getenv("LLM_ENDPOINT") or os.getenv("OPENAI_ENDPOINT", "https://api.openai.com/v1")
            temperature = float(os.getenv("LLM_TEMPERATURE") or os.getenv("OPENAI_TEMPERATURE", "0.6"))
            
            self.logger.info(f"Usando provedor LLM: {llm_provider} com endpoint: {base_url}")
            self.logger.info(f"Modelo selecionado: {model_name}")
            
            # Configurar headers específicos para OpenRouter
            default_headers = {}
            if "openrouter.ai" in base_url:
                default_headers = {
                    "HTTP-Referer": os.getenv("HTTP_REFERER", "https://z2b-browser-api"),
                    "X-Title": os.getenv("X_TITLE", "Z2B Browser API"),
                    "HTTP-OR-APP-ID": os.getenv("HTTP_HEADER_OR_APP_ID", "z2b-browser-api-v1")
                }
            
            # Teste de conexão com a API
            try:
                import openai
                from openai import OpenAI
                client = OpenAI(
                    api_key=api_key, 
                    base_url=base_url,
                    default_headers=default_headers
                )
                self.logger.info("Testando conexão com API...")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": "Responda apenas com 'OK' para testar a API."}],
                    temperature=0.1,
                    max_tokens=10
                )
                self.logger.info(f"Teste de API bem-sucedido! Resposta: {response.choices[0].message.content}")
            except Exception as api_error:
                self.logger.error(f"Erro ao testar API: {str(api_error)}")
                # Continuar mesmo com erro
            
            # Criar prompt melhorado
            enhanced_prompt = f"""
            Você é um agente de automação web. Sua tarefa é:
            
            {prompt}
            
            Siga estes passos:
            1. Navegue para o Google
            2. Pesquise pela informação solicitada
            3. Analise os resultados
            4. Retorne a informação solicitada
            
            Use os comandos de navegação e interação disponíveis.
            """
            
            # Configurar o LLM usando formato compatível com OpenAI
            from langchain_openai import ChatOpenAI
            
            # Configurar para compatibilidade com o modelo Gemini
            llm = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=api_key,
                base_url=base_url,
                default_headers=default_headers,
                model_kwargs={
                    "max_tokens": 4000,  # Limitar tokens de saída
                    "stop": None,  # Evitar paradas prematuras
                }
            )
            
            # Cria o agente browser-use com parâmetros compatíveis
            self.logger.info(f"Criando agente browser-use com modelo {model_name}")
            
            # Determinar o método de tool calling baseado no modelo
            tool_calling_method = "json_mode"
            if "gpt" in model_name.lower():
                tool_calling_method = "function_calling"
                
            max_failures = int(os.getenv("AGENT_MAX_FAILURES", "5"))
            
            agent = BrowserAgent(
                task=enhanced_prompt,
                llm=llm,
                browser_context=self.browser_context,
                tool_calling_method=tool_calling_method,
                max_failures=max_failures,
                use_vision=AGENT_USE_VISION
            )
            
            # Executa o agente
            self.logger.info("Executando agente browser-use")
            try:
                await agent.run()
                self.logger.info("Agente executado com sucesso")
            except Exception as agent_error:
                self.logger.error(f"Erro durante execução do agente: {str(agent_error)}")
                raise
            
            # Captura screenshot após execução
            self.logger.info("Execução completa, capturando dados da página atual")
            try:
                if self.browser_context:  # Verificar se existe antes de chamar
                    active_page = await self.browser_context.get_current_page()
                    if active_page:
                        screenshot = await active_page.screenshot()
                        current_url = active_page.url
                        encoded_screenshot = base64.b64encode(screenshot).decode('utf-8')
                        
                        # Envia screenshot via callback
                        if callback:
                            await callback({
                                "event_type": "task.screenshot",
                                "task_id": task_id,
                                "client_id": client_id,
                                "screenshot": encoded_screenshot,
                                "current_url": current_url
                            })
                    else:
                        self.logger.warning("Não foi possível obter a página ativa para capturar o screenshot")
                else:
                    self.logger.warning("Browser context não disponível para capturar screenshot")
            except Exception as e:
                self.logger.error(f"Erro ao capturar screenshot: {e}")
                
        except Exception as e:
            self.logger.error(f"Erro ao executar o agente browser-use: {str(e)}")
            traceback.print_exc()
            raise

    async def cleanup(self):
        """
        Limpa recursos utilizados pelo agente
        """
        self.logger.info("Iniciando processo de limpeza")
        
        try:
            if self.browser_context:
                self.logger.info("Fechando contexto do navegador")
                await self.browser_context.close()
            
            # Se iniciamos um processo do Chrome, vamos terminá-lo
            if hasattr(self, 'chrome_process') and self.chrome_process:
                self.logger.info("Encerrando processo do Chrome")
                try:
                    self.chrome_process.terminate()
                    self.chrome_process = None
                except Exception as e:
                    self.logger.error(f"Erro ao encerrar Chrome: {str(e)}")
            
            self.logger.info("Limpeza concluída com sucesso")
        except Exception as e:
            self.logger.error(f"Erro durante limpeza: {str(e)}")
            traceback.print_exc()

    async def execute(self, task: Task) -> TaskResult:
        """
        Executa uma tarefa utilizando o contexto do navegador.
        
        Args:
            task: A tarefa a ser executada.
            
        Returns:
            TaskResult: O resultado da execução da tarefa.
        """
        start_time = time.time()
        self.logger.info(f"Executando tarefa: {task.id}")
        
        result = None
        try:
            # Inicializar o navegador usando o método setup existente
            if not await self.setup():
                raise RuntimeError("Falha ao inicializar o navegador")
            
            # Seleciona o executor apropriado com base no tipo de tarefa
            if task.type == "prompt":
                result = await self._execute_prompt_task(task.data.get("prompt", ""), task.id, task.id)
            elif task.type == "plan":
                result = await self._execute_plan_task(task)
            else:
                raise ValueError(f"Tipo de tarefa desconhecido: {task.type}")
            
        except Exception as e:
            self.logger.error(f"Erro durante a execução da tarefa: {str(e)}", exc_info=True)
            result = TaskResult(
                task_id=task.id,
                status="error",
                error=str(e),
                duration=time.time() - start_time
            )
        finally:
            # Limpeza e fechamento do navegador usando o método cleanup existente
            await self.cleanup()
        
        self.logger.info(f"Tarefa {task.id} concluída em {time.time() - start_time:.2f}s")
        return result

    async def _execute_plan_task(self, task: Task) -> TaskResult:
        """
        Executa uma tarefa de plano utilizando o navegador.
        
        Args:
            task: A tarefa a ser executada.
            
        Returns:
            TaskResult: O resultado da execução da tarefa.
        """
        start_time = time.time()
        self.logger.info(f"Executando tarefa de plano: {task.id}")
        
        try:
            # Obter o plano dos dados da tarefa
            plan = task.data.get("plan", [])
            if not plan:
                raise ValueError("Plano não especificado na tarefa")
            
            # Registrar o plano
            self.logger.info(f"Executando plano com {len(plan)} etapas")
            
            # Navegar para a URL inicial (se especificada)
            url = task.data.get("url")
            if url and self.browser_context:
                # Obter a página atual ou criar uma nova
                page = await self.browser_context.get_current_page()
                
                # Navegar para a URL usando o método goto da página
                if page:
                    await page.goto(url)
                    self.logger.info(f"Navegou para: {url}")
                else:
                    self.logger.warning("Não foi possível obter a página atual")
            
            # Executar etapas do plano (implementação futura)
            # Por enquanto, apenas registrar as etapas do plano
            for i, step in enumerate(plan):
                self.logger.info(f"Etapa {i+1}: {step}")
            
            # Capturar screenshot
            screenshot_base64 = None
            current_url = url
            
            try:
                # Pegar página ativa para capturar screenshot
                if self.browser_context:
                    active_page = await self.browser_context.get_current_page()
                    if active_page:
                        # Usar screenshot() em vez de screenshot_base64()
                        screenshot = await active_page.screenshot()
                        screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
                        
                        # Obter URL atual da propriedade url
                        current_url = active_page.url
                        self.logger.info(f"Screenshot capturado da URL: {current_url}")
                    else:
                        self.logger.warning("Não foi possível obter a página ativa para captura de screenshot")
                else:
                    self.logger.warning("Browser context não disponível para capturar screenshot")
            except Exception as e:
                self.logger.error(f"Erro ao capturar screenshot: {str(e)}")
            
            # Preparar resultado
            result_data = {
                "url": current_url or url,
                "screenshot": screenshot_base64,
                "plan": plan,
                "result": "Simulação de plano executada com sucesso",
            }
            
            return TaskResult(
                task_id=task.id,
                status="completed",
                data=result_data,
                duration=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Erro durante a execução da tarefa de plano: {str(e)}", exc_info=True)
            return TaskResult(
                task_id=task.id,
                status="error",
                error=str(e),
                duration=time.time() - start_time
            )

    def _extract_model_info(self) -> dict:
        """
        Extrai informações do modelo em uso
        """
        model_info = {
            "model_name": "unknown",
            "provider": "unknown"
        }
        
        if self.llm_config:
            model_info["model_name"] = self.llm_config.get("model_name", "unknown")
            model_info["provider"] = self.llm_config.get("provider", "unknown")
            
        return model_info

    async def get_status(self) -> dict:
        """
        Retorna o status atual do agente
        """
        logger.debug(f"[STATUS] Status atual: {self.status}")
        status_info = {
            "status": self.status,
            "current_task": self.current_task,
            "result": self.result,
            "task_id": self.storage.task_id
        }
        return status_info

    async def setup(self) -> bool:
        """
        Configura o ambiente do agente, inicializando o Browser e BrowserContext
        
        Returns:
            bool: True se a configuração foi bem-sucedida, False caso contrário
        """
        self.logger.info("[SETUP] Iniciando configuração do navegador")
        
        try:
            # Configuração de argumentos extras para Chrome
            extra_chromium_args = [
                f"--window-size={BROWSER_WIDTH},{BROWSER_HEIGHT}",
                "--disable-blink-features=AutomationControlled",  # Esconde que é automação
                "--disable-web-security",  # Desativa segurança web
                "--no-sandbox",  # Desativa sandbox
                "--disable-features=IsolateOrigins,site-per-process"  # Ajuda com iframes
            ]
            
            # Configuração do Browser
            browser_config = BrowserConfig(
                headless=BROWSER_HEADLESS,
                disable_security=BROWSER_DISABLE_SECURITY,
                extra_chromium_args=extra_chromium_args
            )
            
            self.logger.info("[SETUP] Criando instância do Browser")
            self.browser = Browser(config=browser_config)
            
            # Configuração do BrowserContext com User-Agent personalizado
            context_config = BrowserContextConfig(
                browser_window_size=BrowserContextWindowSize(
                    width=BROWSER_WIDTH,
                    height=BROWSER_HEIGHT
                ),
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            
            self.logger.info("[SETUP] Criando contexto do navegador")
            self.browser_context = await self.browser.new_context(config=context_config)
            
            # Testar navegação para verificar se o navegador funciona
            try:
                self.logger.info("[SETUP] Testando navegação para example.com")
                page = await self.browser_context.get_current_page()
                if page:
                    await page.goto("https://example.com")
                    self.logger.info("[SETUP] Navegação bem-sucedida para example.com")
                    
                    # Tentar verificar o título
                    try:
                        title = await page.evaluate("document.title")
                        self.logger.info(f"[SETUP] Título da página: {title}")
                    except Exception as eval_error:
                        self.logger.warning(f"[SETUP] Não foi possível obter o título: {str(eval_error)}")
                else:
                    self.logger.warning("[SETUP] Não foi possível obter a página atual")
            except Exception as nav_error:
                self.logger.error(f"[SETUP] Erro ao testar navegação: {str(nav_error)}")
                # Continuar mesmo com erro no teste
            
            self.logger.info("[SETUP] Navegador inicializado com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"[SETUP] Erro ao configurar navegador: {str(e)}", exc_info=True)
            
            # Limpar recursos
            if hasattr(self, 'browser') and self.browser:
                try:
                    await self.browser.close()
                except Exception as close_error:
                    self.logger.error(f"[SETUP] Erro ao fechar navegador: {str(close_error)}")
                
                self.browser = None
                self.browser_context = None
                
            return False

    async def _execute_prompt_with_z2b(self, prompt, client_id=None, task_id=None, callback=None):
        """
        Executa um prompt usando a implementação Z2B.
        
        Args:
            prompt (str): O prompt a ser executado
            client_id (str, optional): ID do cliente
            task_id (str, optional): ID da tarefa
            callback (callable, optional): Função de callback para atualizações
            
        Returns:
            Dict: Resultados da execução
        """
        try:
            self.logger.info(f"Executando prompt com Z2BAgent: {prompt[:100]}...")
            
            # Integrar o callback com o Z2BAgent
            if self.z2b_agent:
                # Se temos um callback, tentar registrar para o browser-use por dentro do Z2BAgent
                if callback and hasattr(callback, 'get_browser_use_tracker') and hasattr(self.z2b_agent, 'register_browser_callbacks'):
                    self.logger.info("Registrando callbacks do browser-use")
                    self.z2b_agent.register_browser_callbacks(callback)
                
                # Criar tarefa se não existir
                if not self.z2b_agent.task:
                    task = Task(
                        id=task_id or f"prompt_{uuid.uuid4().hex}",
                        type="prompt",
                        data={"prompt": prompt}
                    )
                    self.z2b_agent.task = task
            
                # Configurar callback para o Z2BAgent
                # O callback do Z2BAgent será chamado após cada etapa
                if callback:
                    async def z2b_callback(event_data):
                        # Adicionar IDs
                        if task_id and "task_id" not in event_data:
                            event_data["task_id"] = task_id
                        if client_id and "client_id" not in event_data:
                            event_data["client_id"] = client_id
                        
                        # Chamar callback original
                        return await callback(event_data)
                    
                    # Executar com nosso wrapper de callback
                    result = await self.z2b_agent.run_with_callback(z2b_callback)
                else:
                    # Executar normalmente sem callback
                    result = await self.z2b_agent.run()
                
                # Obtém screenshot final e URL se disponível
                screenshot_base64 = None
                current_url = None
                
                try:
                    if self.z2b_agent.browser_context:
                        page = await self.z2b_agent.browser_context.get_current_page()
                        if page:
                            screenshot = await page.screenshot()
                            screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
                            current_url = page.url
                except Exception as e:
                    self.logger.error(f"Erro ao capturar screenshot final: {str(e)}")
                
                # Montar resultado final
                final_result = {
                    "status": "completed",
                    "result": result.data if hasattr(result, 'data') and result.data else result,
                    "screenshot": screenshot_base64,
                    "current_url": current_url
                }
                
                # Enviar evento final
                if callback:
                    try:
                        await callback({
                            "event_type": "task.completed",
                            "task_id": task_id,
                            "client_id": client_id,
                            "data": final_result,
                            "screenshot": screenshot_base64,
                            "current_url": current_url
                        })
                    except Exception as e:
                        self.logger.error(f"Erro ao enviar evento de conclusão: {str(e)}")
                
                return final_result
            else:
                self.logger.error("Z2BAgent não inicializado")
                return {"status": "error", "error": "Z2BAgent não inicializado"}
        
        except Exception as e:
            self.logger.error(f"Erro ao executar com Z2BAgent: {str(e)}")
            traceback.print_exc()
            
            # Enviar erro via callback
            if callback:
                try:
                    await callback({
                        "event_type": "task.error",
                        "task_id": task_id,
                        "client_id": client_id,
                        "data": {"error": str(e)}
                    })
                except Exception as callback_error:
                    self.logger.error(f"Erro ao enviar callback de erro: {str(callback_error)}")
            
            return {"status": "error", "error": str(e)}