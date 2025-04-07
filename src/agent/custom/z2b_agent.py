"""
Implementação do agente customizado Zap2B.

Este módulo contém a implementação concreta do agente base Zap2B com
funcionalidades específicas para integração com o sistema Zap2B.
"""

import json
import logging
import time
import traceback
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union

from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig

from .browser_agent import BrowserAgent
from ..base import Task, TaskResult


class Z2BAgent(BrowserAgent):
    """
    Agente base customizado do Zap2B com melhorias específicas.
    
    Este agente estende o BrowserAgent com funcionalidades específicas
    para o ambiente Zap2B, incluindo tratamento avançado de erros,
    reparo de JSON e integração com o sistema de prompts.
    """
    
    def __init__(
        self,
        task: Optional[Union[str, Task]] = None,
        browser_context: Optional[BrowserContext] = None,
        browser: Optional[Browser] = None,
        prompt_manager: Optional[Any] = None,
        headless: bool = True,
        user_agent: Optional[str] = None,
        viewport: Optional[Dict[str, int]] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """
        Inicializa o agente Zap2B.
        
        Args:
            task: Tarefa a ser executada, pode ser um prompt ou objeto Task
            browser_context: Contexto do navegador já inicializado (opcional)
            browser: Instância do navegador já inicializada (opcional)
            prompt_manager: Gerenciador de prompts (opcional)
            headless: Se True, executa o navegador em modo sem interface gráfica
            user_agent: User agent para o navegador (opcional)
            viewport: Dimensões da janela do navegador (opcional)
            timeout: Tempo máximo de espera para operações do navegador em segundos
            max_retries: Número máximo de tentativas para operações que falham
            retry_delay: Tempo de espera entre tentativas em segundos
        """
        super().__init__(
            task=task,
            browser_context=browser_context,
            browser=browser,
            prompt_manager=prompt_manager,
            headless=headless,
            user_agent=user_agent,
            viewport=viewport,
            timeout=timeout
        )
        
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger("Z2BAgent")
        
        # Atributos adicionais
        self.browser_agent = None
        self._callback = None
        
    async def execute(self, task: Task) -> TaskResult:
        """
        Executa uma tarefa com tratamento avançado de erros e recuperação.
        
        Args:
            task: A tarefa a ser executada
            
        Returns:
            TaskResult: O resultado da execução da tarefa
        """
        start_time = time.time()
        task_id = task.id
        retries = 0
        
        while retries <= self.max_retries:
            try:
                # Tenta executar a tarefa normalmente
                result = await super().execute(task)
                
                # Se foi bem-sucedido, retorna o resultado
                if result.status != "error":
                    return result
                
                # Se houve erro, mas já tentamos o número máximo de vezes, retorna o erro
                if retries >= self.max_retries:
                    self.logger.warning(f"Falha após {retries} tentativas para a tarefa {task_id}")
                    return result
                
                # Caso contrário, aumenta o contador e tenta novamente
                retries += 1
                self.logger.info(f"Tentativa {retries}/{self.max_retries} para a tarefa {task_id}")
                time.sleep(self.retry_delay)
                
            except Exception as e:
                # Captura qualquer exceção não tratada
                self.logger.error(f"Erro não tratado: {str(e)}")
                traceback.print_exc()
                
                if retries >= self.max_retries:
                    return TaskResult.create_error_result(
                        task_id=task_id,
                        error=f"Erro após {retries} tentativas: {str(e)}",
                        duration=time.time() - start_time
                    )
                
                retries += 1
                time.sleep(self.retry_delay)
    
    async def cleanup(self) -> None:
        """
        Limpa recursos utilizados pelo agente, fechando o navegador 
        com tratamento de exceções.
        
        Esta implementação aprimorada garante que os recursos sejam liberados corretamente,
        evitando warnings de recursos não fechados.
        """
        try:
            # Primeiro, verifica se o contexto do navegador ainda existe
            if self.browser_context:
                try:
                    # Usa um timeout para garantir que o fechamento não trave
                    await asyncio.wait_for(self.browser_context.close(), timeout=5.0)
                    self.logger.info("Contexto do navegador fechado com sucesso.")
                except asyncio.TimeoutError:
                    self.logger.warning("Timeout ao fechar o contexto do navegador.")
                except Exception as e:
                    self.logger.error(f"Erro ao fechar o contexto do navegador: {str(e)}")
                finally:
                    # Garante que a referência seja removida mesmo em caso de erro
                    self.browser_context = None
                    
            # Em seguida, fecha o navegador principal
            if self.browser:
                try:
                    # Usa um timeout para garantir que o fechamento não trave
                    await asyncio.wait_for(self.browser.close(), timeout=5.0)
                    self.logger.info("Navegador fechado com sucesso.")
                except asyncio.TimeoutError:
                    self.logger.warning("Timeout ao fechar o navegador.")
                except Exception as e:
                    self.logger.error(f"Erro ao fechar o navegador: {str(e)}")
                finally:
                    # Garante que a referência seja removida mesmo em caso de erro
                    self.browser = None
                    
            # Pausa para permitir que o garbage collector do Python limpe os recursos
            await asyncio.sleep(0.5)
                
        except Exception as e:
            self.logger.error(f"Erro ao limpar recursos: {str(e)}")
    
    def repair_json(self, broken_json: str) -> Dict[Any, Any]:
        """
        Tenta reparar JSON malformado.
        
        Args:
            broken_json: String de JSON potencialmente malformado
            
        Returns:
            Dict[Any, Any]: Dicionário Python obtido do JSON reparado
        """
        try:
            # Primeiro tenta analisar normalmente
            return json.loads(broken_json)
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON malformado detectado, tentando reparar: {str(e)}")
            
            # Implementação básica de reparo de JSON
            # Identifica e corrige problemas comuns
            fixed_json = broken_json
            
            # Corrige aspas simples para aspas duplas
            fixed_json = fixed_json.replace("'", "\"")
            
            # Corrige vírgulas extras no final de objetos/arrays
            fixed_json = fixed_json.replace(",}", "}")
            fixed_json = fixed_json.replace(",]", "]")
            
            # Adiciona aspas em chaves não quotadas
            # Este é um reparo mais complexo que poderia ser implementado
            
            try:
                return json.loads(fixed_json)
            except json.JSONDecodeError:
                self.logger.error("Falha ao reparar JSON malformado")
                return {}
    
    async def execute_prompt_task(self, prompt: str) -> TaskResult:
        """
        Executa uma tarefa baseada em prompt com funcionalidades específicas do Zap2B.
        
        Args:
            prompt: O prompt descrevendo a tarefa a ser executada
            
        Returns:
            TaskResult: O resultado da execução
        """
        task_id = f"task_{int(time.time())}"
        task = Task(id=task_id, type="prompt", data={"prompt": prompt})
        
        self.logger.info(f"Executando tarefa de prompt: {prompt[:50]}...")
        return await self.run(task)

    def register_browser_callbacks(self, tracker):
        """
        Registra callbacks para rastrear a execução do browser-use
        
        Args:
            tracker: Instância do AgentTracker
        """
        if self.browser_agent and hasattr(self.browser_agent, 'register_callback'):
            if hasattr(tracker, 'get_browser_use_tracker'):
                browser_use_tracker = tracker.get_browser_use_tracker()
                if browser_use_tracker and hasattr(browser_use_tracker, 'step_callback'):
                    self.browser_agent.register_callback(browser_use_tracker.step_callback)
                    self.logger.info("Callbacks do BrowserUseTracker registrados no agente browser-use")
                    return True
        
        self.logger.warning("Não foi possível registrar callbacks para o browser-use")
        return False

    async def run_with_callback(self, callback: callable) -> TaskResult:
        """
        Executa a tarefa atual usando um callback para rastreamento.
        
        Args:
            callback: Função de callback para receber eventos durante a execução
            
        Returns:
            TaskResult: O resultado da execução
        """
        if not self.task:
            self.logger.error("Nenhuma tarefa definida para execução")
            return TaskResult.create_error_result(
                task_id="no_task", 
                error="Nenhuma tarefa definida para execução"
            )
        
        # Guardar o callback
        self._callback = callback
        
        start_time = time.time()
        self.logger.info(f"Iniciando execução da tarefa {self.task.id}")
        
        try:
            # Iniciar o navegador se necessário
            if not self.browser_context:
                await self.setup()
            
            # Executar a tarefa com base no tipo
            if self.task.type == "prompt":
                prompt = self.task.data.get("prompt", "")
                self.logger.info(f"Executando prompt: {prompt[:100]}...")
                
                # Se a ação for um prompt, executar o agente de navegador
                if not hasattr(self, 'browser_agent') or not self.browser_agent:
                    self.logger.info("Inicializando agente de navegador")
                    await self.init_browser_agent(prompt)
                
                # Enviar evento de início
                if self._callback:
                    try:
                        await self._callback({
                            "event_type": "task.started",
                            "data": {"prompt": prompt}
                        })
                    except Exception as e:
                        self.logger.error(f"Erro ao enviar evento de início: {str(e)}")
                
                # Executar o agente
                result = await self.browser_agent.run()
                
                # Criar resultado a partir do histórico do agente
                task_result = self._create_result_from_history(
                    task_id=self.task.id,
                    history=result if result else None,
                    duration=time.time() - start_time
                )
                
                # Enviar evento de conclusão
                if self._callback:
                    try:
                        await self._callback({
                            "event_type": "task.completed", 
                            "data": task_result.data
                        })
                    except Exception as e:
                        self.logger.error(f"Erro ao enviar evento de conclusão: {str(e)}")
                
                return task_result
                
            else:
                self.logger.error(f"Tipo de tarefa não suportado: {self.task.type}")
                error_result = TaskResult.create_error_result(
                    task_id=self.task.id,
                    error=f"Tipo de tarefa não suportado: {self.task.type}",
                    duration=time.time() - start_time
                )
                
                # Enviar evento de erro
                if self._callback:
                    try:
                        await self._callback({
                            "event_type": "task.error",
                            "data": {"error": f"Tipo de tarefa não suportado: {self.task.type}"}
                        })
                    except Exception as e:
                        self.logger.error(f"Erro ao enviar evento de erro: {str(e)}")
                
                return error_result
                
        except Exception as e:
            self.logger.error(f"Erro durante execução da tarefa: {str(e)}")
            traceback.print_exc()
            
            error_result = TaskResult.create_error_result(
                task_id=self.task.id,
                error=str(e),
                duration=time.time() - start_time
            )
            
            # Enviar evento de erro
            if self._callback:
                try:
                    await self._callback({
                        "event_type": "task.error",
                        "data": {"error": str(e)}
                    })
                except Exception as callback_error:
                    self.logger.error(f"Erro ao enviar callback de erro: {str(callback_error)}")
            
            return error_result
        finally:
            # Limpeza
            try:
                await self.cleanup()
            except Exception as e:
                self.logger.error(f"Erro durante limpeza: {str(e)}")
            
    def _create_result_from_history(self, task_id: str, history: Any, duration: float) -> TaskResult:
        """
        Cria um objeto TaskResult a partir do histórico do agente.
        
        Args:
            task_id: ID da tarefa
            history: Objeto de histórico retornado pelo agente
            duration: Duração da execução em segundos
            
        Returns:
            TaskResult: Resultado formatado da tarefa
        """
        try:
            # Extrair conteúdo
            extracted_content = []
            if history and hasattr(history, 'extracted_content'):
                extracted_content = history.extracted_content()
            
            # Extrair erros
            errors = []
            if history and hasattr(history, 'errors'):
                errors = [err for err in history.errors() if err]
            
            # Extrair URLs visitadas
            urls = []
            if history and hasattr(history, 'urls'):
                urls = history.urls()
            
            # Resultados das ações
            action_results = []
            if history and hasattr(history, 'action_results'):
                action_results = [
                    {
                        "success": result.success if hasattr(result, 'success') else None,
                        "content": result.extracted_content if hasattr(result, 'extracted_content') else None,
                        "error": result.error if hasattr(result, 'error') else None
                    }
                    for result in history.action_results()
                ]
            
            # Verificar sucesso/conclusão
            is_successful = None
            is_done = False
            if history:
                if hasattr(history, 'is_successful'):
                    is_successful = history.is_successful()
                if hasattr(history, 'is_done'):
                    is_done = history.is_done()
            
            # Criar resultado
            status = "completed" if is_done else "in_progress"
            if is_done and errors and not is_successful:
                status = "error"
            
            result_data = {
                "content": "\n".join(extracted_content) if extracted_content else "",
                "urls": urls,
                "errors": errors,
                "action_results": action_results,
                "is_done": is_done,
                "is_successful": is_successful
            }
            
            return TaskResult(
                task_id=task_id,
                status=status,
                data=result_data,
                error=errors[0] if errors else None,
                duration=duration
            )
        except Exception as e:
            self.logger.error(f"Erro ao criar resultado a partir do histórico: {str(e)}")
            return TaskResult.create_error_result(
                task_id=task_id,
                error=f"Erro ao processar resultado: {str(e)}",
                duration=duration
            ) 