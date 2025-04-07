#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import base64
import logging
import asyncio
import time
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Awaitable, Union
import traceback
import concurrent.futures

# Configuração de logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("agent_tracker")

class EventCategorizador:
    """
    Classe que categoriza eventos para facilitar análise e filtragem.
    """
    # Categorias de eventos
    CATEGORIA_NAVEGACAO = "navegacao"
    CATEGORIA_INTERACAO = "interacao"
    CATEGORIA_SCREENSHOT = "screenshot"
    CATEGORIA_PLANEJAMENTO = "planejamento"
    CATEGORIA_ERRO = "erro"
    CATEGORIA_SISTEMA = "sistema"
    CATEGORIA_DESCONHECIDO = "desconhecido"
    
    @staticmethod
    def categorizar_evento(event_type: str) -> str:
        """
        Categoriza o evento baseado no seu tipo.
        
        Args:
            event_type: Tipo do evento
            
        Returns:
            str: Categoria do evento
        """
        if not event_type:
            return EventCategorizador.CATEGORIA_DESCONHECIDO
            
        event_type = event_type.lower()
        
        # Eventos de navegação
        if "navigate" in event_type or "url" in event_type or "navigation" in event_type:
            return EventCategorizador.CATEGORIA_NAVEGACAO
            
        # Eventos de interação
        if any(action in event_type for action in ["click", "type", "input", "select", "scroll", "drag"]):
            return EventCategorizador.CATEGORIA_INTERACAO
            
        # Eventos de screenshot
        if "screenshot" in event_type:
            return EventCategorizador.CATEGORIA_SCREENSHOT
            
        # Eventos de planejamento
        if "plan" in event_type or "goal" in event_type or "strategy" in event_type:
            return EventCategorizador.CATEGORIA_PLANEJAMENTO
            
        # Eventos de erro
        if "error" in event_type or "fail" in event_type or "exception" in event_type:
            return EventCategorizador.CATEGORIA_ERRO
            
        # Eventos de sistema
        if "start" in event_type or "complete" in event_type or "init" in event_type:
            return EventCategorizador.CATEGORIA_SISTEMA
            
        # Desconhecido
        return EventCategorizador.CATEGORIA_DESCONHECIDO

class TimelineBuilder:
    """
    Classe para construir visualizações de timeline a partir dos eventos de execução.
    Permite criar um arquivo JSON com estrutura adequada para visualização em ferramentas externas.
    """
    def __init__(self, title="Agent Execution Timeline"):
        """
        Inicializa o construtor de timeline.
        
        Args:
            title (str): Título da timeline que será exibido na visualização
        """
        self.title = title
        self.events = []
        self.start_time = None
        self.end_time = None
        
    def start_timer(self):
        """Inicia o temporizador para a timeline"""
        self.start_time = datetime.now()
        
    def stop_timer(self):
        """Para o temporizador da timeline"""
        self.end_time = datetime.now()
        
    def add_event(self, title, description=None, icon=None, timestamp=None, metadata=None):
        """
        Adiciona um evento genérico à timeline.
        
        Args:
            title (str): Título do evento
            description (str, optional): Descrição detalhada do evento
            icon (str, optional): Ícone a ser exibido (emoji ou código HTML)
            timestamp (str, optional): Timestamp ISO do evento (usa o atual se não fornecido)
            metadata (dict, optional): Metadados adicionais do evento
        """
        if not timestamp:
            timestamp = datetime.now().isoformat()
            
        event = {
            "title": title,
            "timestamp": timestamp
        }
        
        if description:
            event["description"] = description
            
        if icon:
            event["icon"] = icon
            
        if metadata:
            event["metadata"] = metadata
            
        self.events.append(event)
        
    def add_step(self, step_number, content, status="completed", metadata=None):
        """
        Adiciona um passo de execução à timeline.
        
        Args:
            step_number (int): Número do passo
            content (str): Conteúdo ou descrição do passo
            status (str, optional): Status do passo (completed, error, etc)
            metadata (dict, optional): Metadados adicionais do passo
        """
        # Determinar ícone com base no status
        icon = "✅"  # Default para completed
        if status == "error":
            icon = "❌"
        elif status == "warning":
            icon = "⚠️"
        elif status == "initialized":
            icon = "🔄"
            
        # Criar título formatado com número do passo
        title = f"Passo {step_number}: {content[:50]}"
        if len(content) > 50:
            title += "..."
            
        # Adicionar o evento com metadados específicos de passo
        step_metadata = {"step_number": step_number, "status": status}
        if metadata:
            step_metadata.update(metadata)
            
        self.add_event(
            title=title,
            description=content,
            icon=icon,
            metadata=step_metadata
        )
        
    def add_thought(self, step_number, thought_type, content, timestamp=None):
        """
        Adiciona um pensamento à timeline.
        
        Args:
            step_number (int): Número do passo associado
            thought_type (str): Tipo de pensamento (thought, evaluation, memory, goal)
            content (str): Conteúdo do pensamento
            timestamp (str, optional): Timestamp ISO (usa o atual se não fornecido)
        """
        # Determinar ícone com base no tipo de pensamento
        icon = "💭"  # Default para thought
        if thought_type == "evaluation":
            icon = "🔍"
        elif thought_type == "memory":
            icon = "💾"
        elif thought_type == "goal" or thought_type == "next_goal":
            icon = "🎯"
            
        # Criar título formatado
        title = f"[Passo {step_number}] {thought_type.capitalize()}"
        
        # Truncar conteúdo para descrição
        description = content[:200]
        if len(content) > 200:
            description += "..."
            
        # Adicionar metadados específicos de pensamento
        metadata = {
            "step_number": step_number,
            "thought_type": thought_type,
            "full_content": content
        }
        
        self.add_event(
            title=title,
            description=description,
            icon=icon,
            timestamp=timestamp,
            metadata=metadata
        )
        
    def add_llm_event(self, step_number, event_type, data):
        """
        Adiciona um evento relacionado ao uso de LLM à timeline.
        
        Args:
            step_number (int): Número do passo associado
            event_type (str): Tipo de evento LLM (request, response, cost)
            data (dict): Dados específicos do evento
        """
        # Determinar ícone e título com base no tipo de evento LLM
        icon = "🤖"  # Default para eventos LLM
        
        if event_type == "llm_request":
            title = f"[Passo {step_number}] Requisição LLM"
            description = f"Modelo: {data.get('model', 'N/A')}, Tokens: {data.get('prompt_tokens', 'N/A')}"
        elif event_type == "llm_response":
            title = f"[Passo {step_number}] Resposta LLM"
            description = f"Tokens de resposta: {data.get('completion_tokens', 'N/A')}, Duração: {data.get('duration', 'N/A')}s"
        elif event_type == "llm_cost":
            icon = "💰"
            title = f"[Passo {step_number}] Custo LLM"
            description = f"Custo estimado: ${data.get('cost', 0):.6f}"
        else:
            title = f"[Passo {step_number}] Evento LLM"
            description = str(data)
            
        # Adicionar metadados específicos de LLM
        metadata = {
            "step_number": step_number,
            "event_type": event_type,
            "llm_data": data
        }
        
        self.add_event(
            title=title,
            description=description,
            icon=icon,
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=metadata
        )
        
    def save(self, output_file):
        """
        Salva a timeline em um arquivo JSON.
        
        Args:
            output_file (str): Caminho para o arquivo de saída
        """
        # Calcular duração se possível
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            
        # Criar estrutura completa da timeline
        timeline_data = {
            "title": self.title,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration,
            "events_count": len(self.events),
            "events": self.events
        }
        
        # Salvar no arquivo
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(timeline_data, f, indent=2, ensure_ascii=False)
        
        return output_file

class TimelineBuilderExtended(TimelineBuilder):
    """
    Versão estendida do TimelineBuilder com suporte a tipos adicionais de eventos
    específicos para o rastreamento de agentes browser-use.
    """
    def __init__(self, title="Browser Use Timeline"):
        """
        Inicializa o construtor de timeline estendido.
        
        Args:
            title (str): Título da timeline que será exibido na visualização
        """
        super().__init__(title=title)
        self.steps = {}  # Armazena dados de passos pelo número
        self.thoughts_by_step = {}  # Armazena pensamentos agrupados por passo
        
    def add_step(self, step_number, content=None, is_complete=False, 
                 evaluation=None, memory=None, next_goal=None, thought=None,
                 status="in_progress", metadata=None):
        """
        Adiciona ou atualiza um passo na timeline com dados enriquecidos.
        
        Args:
            step_number (int): Número do passo
            content (str, optional): Conteúdo ou descrição do passo
            is_complete (bool): Se o passo está completo
            evaluation (str, optional): Avaliação associada ao passo
            memory (str, optional): Memória associada ao passo
            next_goal (str, optional): Próximo objetivo associado ao passo
            thought (str, optional): Pensamento associado ao passo
            status (str): Status do passo
            metadata (dict, optional): Metadados adicionais do passo
        """
        # Determinar status baseado no is_complete
        if is_complete:
            status = "completed"
            
        # Preparar metadados estendidos
        step_metadata = metadata or {}
        step_metadata["is_complete"] = is_complete
        
        # Adicionar pensamentos se fornecidos
        thoughts = {}
        if evaluation:
            thoughts["evaluation"] = evaluation
        if memory:
            thoughts["memory"] = memory
        if next_goal:
            thoughts["next_goal"] = next_goal
        if thought:
            thoughts["thought"] = thought
            
        if thoughts:
            step_metadata["thoughts"] = thoughts
            
        # Armazenar dados do passo para referência
        self.steps[step_number] = {
            "content": content or f"Passo {step_number}",
            "is_complete": is_complete,
            "status": status,
            "thoughts": thoughts,
            "metadata": step_metadata
        }
        
        # Inicializar estrutura de pensamentos por passo se necessário
        if step_number not in self.thoughts_by_step:
            self.thoughts_by_step[step_number] = {
                "evaluation": [],
                "memory": [],
                "next_goal": [],
                "thought": []
            }
            
        # Adicionar o evento à timeline usando o método da classe pai
        super().add_step(
            step_number=step_number,
            content=content or f"Passo {step_number}",
            status=status,
            metadata=step_metadata
        )
        
    def add_thought(self, step_number, thought_type, content, metadata=None, timestamp=None):
        """
        Adiciona um pensamento à timeline e o associa ao passo correspondente.
        
        Args:
            step_number (int): Número do passo associado
            thought_type (str): Tipo de pensamento (thought, evaluation, memory, goal)
            content (str): Conteúdo do pensamento
            metadata (dict, optional): Metadados adicionais do pensamento
            timestamp (str, optional): Timestamp ISO (usa o atual se não fornecido)
        """
        # Normalizar tipo de pensamento
        if thought_type.lower() in ["goal", "next_goal", "próximo_objetivo", "proximo_objetivo"]:
            normalized_type = "next_goal"
        elif thought_type.lower() in ["avaliação", "avaliacao", "evaluation"]:
            normalized_type = "evaluation"
        elif thought_type.lower() in ["memória", "memoria", "memory"]:
            normalized_type = "memory"
        else:
            normalized_type = "thought"
            
        # Inicializar estrutura de pensamentos por passo se necessário
        if step_number not in self.thoughts_by_step:
            self.thoughts_by_step[step_number] = {
                "evaluation": [],
                "memory": [],
                "next_goal": [],
                "thought": []
            }
            
        # Armazenar pensamento na categoria correspondente
        thought_data = {
            "content": content,
            "timestamp": timestamp or datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.thoughts_by_step[step_number][normalized_type].append(thought_data)
        
        # Adicionar o evento à timeline usando o método da classe pai
        super().add_thought(
            step_number=step_number,
            thought_type=normalized_type,
            content=content,
            timestamp=timestamp
        )
        
    def get_step_thoughts(self, step_number):
        """
        Obtém todos os pensamentos associados a um passo específico.
        
        Args:
            step_number (int): Número do passo
            
        Returns:
            dict: Pensamentos categorizados por tipo para o passo
        """
        return self.thoughts_by_step.get(step_number, {})
    
    def get_steps_summary(self):
        """
        Gera um resumo dos passos registrados na timeline.
        
        Returns:
            dict: Resumo dos passos com contagens por categoria
        """
        total_steps = len(self.steps)
        complete_steps = sum(1 for step in self.steps.values() if step["is_complete"])
        
        # Contar tipos de pensamentos por passo
        thought_counts = {}
        for step_num, thoughts in self.thoughts_by_step.items():
            thought_counts[step_num] = {
                thought_type: len(thought_list) 
                for thought_type, thought_list in thoughts.items()
            }
            thought_counts[step_num]["total"] = sum(thought_counts[step_num].values())
        
        return {
            "total_steps": total_steps,
            "complete_steps": complete_steps,
            "incomplete_steps": total_steps - complete_steps,
            "completion_rate": (complete_steps / total_steps) if total_steps > 0 else 0,
            "thoughts_by_step": thought_counts
        }
    
    def get_thoughts_summary(self):
        """
        Gera um resumo dos pensamentos registrados na timeline.
        
        Returns:
            dict: Resumo dos pensamentos com contagens por categoria
        """
        # Inicializar contadores
        totals = {
            "evaluation": 0,
            "memory": 0,
            "next_goal": 0,
            "thought": 0
        }
        
        # Contar por tipo e por passo
        for step_thoughts in self.thoughts_by_step.values():
            for thought_type, thoughts in step_thoughts.items():
                totals[thought_type] += len(thoughts)
        
        # Calcular total geral
        totals["total"] = sum(totals.values())
        
        return {
            "thought_counts": totals,
            "steps_with_thoughts": len(self.thoughts_by_step),
            "distribution": {
                thought_type: (count / totals["total"]) if totals["total"] > 0 else 0
                for thought_type, count in totals.items() if thought_type != "total"
            }
        }
        
    def save(self, output_file):
        """
        Salva a timeline em um arquivo JSON com dados estendidos.
        
        Args:
            output_file (str): Caminho para o arquivo de saída
        """
        # Calcular resumos
        steps_summary = self.get_steps_summary()
        thoughts_summary = self.get_thoughts_summary()
        
        # Calcular duração se possível
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            
        # Criar estrutura completa da timeline com dados estendidos
        timeline_data = {
            "title": self.title,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration,
            "events_count": len(self.events),
            "steps_count": len(self.steps),
            "thoughts_count": thoughts_summary["thought_counts"]["total"],
            "steps_summary": steps_summary,
            "thoughts_summary": thoughts_summary,
            "events": self.events
        }
        
        # Salvar no arquivo
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(timeline_data, f, indent=2, ensure_ascii=False)
            
        # Salvar também versões separadas dos resumos
        summary_dir = os.path.dirname(output_file)
        
        try:
            # Resumo de passos
            steps_file = os.path.join(summary_dir, "steps_summary.json")
            with open(steps_file, "w", encoding="utf-8") as f:
                json.dump(steps_summary, f, indent=2, ensure_ascii=False)
                
            # Resumo de pensamentos
            thoughts_file = os.path.join(summary_dir, "thoughts_summary.json")
            with open(thoughts_file, "w", encoding="utf-8") as f:
                json.dump(thoughts_summary, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar arquivos de resumo: {e}")
        
        return output_file

class BrowserUseTracker:
    """
    Classe para rastrear em tempo real as ações do browser-use.
    Compatível com o AgentTracker existente.
    """
    def __init__(self, agent_tracker=None):
        self.agent_tracker = agent_tracker
        self.actions = []
        self.steps = 0
        self.logger = logging.getLogger("browser_use_tracker")
        self.start_time = time.time()
        
    async def step_callback(self, model_output, state, result, **kwargs):
        """
        Callback chamado a cada passo do agente browser-use.
        
        Args:
            model_output: Saída do modelo LLM
            state: Estado atual do navegador
            result: Resultado da ação executada
            **kwargs: Argumentos adicionais
        """
        self.steps += 1
        step_time = time.time()
        elapsed_time = step_time - self.start_time
        
        # Extrair ação sendo executada
        action = None
        if model_output and hasattr(model_output, 'action'):
            if isinstance(model_output.action, list) and model_output.action:
                action = model_output.action[0]
                if hasattr(action, 'model_dump'):
                    action = action.model_dump(exclude_none=True)
        
        # Extrair pensamento do modelo
        thought = None
        if model_output and hasattr(model_output, 'current_state') and hasattr(model_output.current_state, 'thought'):
            thought = model_output.current_state.thought
        
        # Extrair avaliação do objetivo anterior
        evaluation = None
        if model_output and hasattr(model_output, 'current_state') and hasattr(model_output.current_state, 'evaluation_previous_goal'):
            evaluation = model_output.current_state.evaluation_previous_goal
            
        # Extrair memória/conteúdo importante
        memory = None
        if model_output and hasattr(model_output, 'current_state'):
            if hasattr(model_output.current_state, 'memory'):
                memory = model_output.current_state.memory
            elif hasattr(model_output.current_state, 'important_contents'):
                memory = model_output.current_state.important_contents
        
        # Extrair próximo objetivo
        next_goal = None
        if model_output and hasattr(model_output, 'current_state') and hasattr(model_output.current_state, 'next_goal'):
            next_goal = model_output.current_state.next_goal
        
        # Extrair URL atual
        current_url = state.url if state and hasattr(state, 'url') else None
        
        # Extrair screenshot
        screenshot_data = None
        if state and hasattr(state, 'screenshot') and state.screenshot:
            screenshot_data = base64.b64encode(state.screenshot).decode('utf-8')
        
        # Extrair estado do DOM se disponível
        dom_state = None
        if state and hasattr(state, 'dom_info'):
            dom_state = state.dom_info
        
        # Extrair informações de performance
        performance_info = {
            "elapsed_time": elapsed_time,
            "step": self.steps,
            "timestamp": datetime.now().isoformat()
        }
        
        # Criar evento para o AgentTracker
        event_data = {
            "event_type": "browser_use.agent.step",
            "step": self.steps,
            "action": action,
            "thought": thought,
            "evaluation": evaluation,
            "memory": memory,
            "goal": model_output.current_state.goal if model_output and hasattr(model_output, 'current_state') else None,
            "next_goal": next_goal,
            "current_url": current_url,
            "screenshot": screenshot_data,
            "dom_state": dom_state,
            "performance": performance_info,
            "timestamp": datetime.now().isoformat()
        }
        
        # Registrar no histórico local
        self.actions.append(event_data)
        
        # Repassar para o AgentTracker se disponível
        if self.agent_tracker and hasattr(self.agent_tracker, 'callback'):
            try:
                await self.agent_tracker.callback(event_data)
                self.logger.debug(f"Evento do passo {self.steps} repassado para o AgentTracker")
            except Exception as e:
                self.logger.error(f"Erro ao repassar evento para AgentTracker: {str(e)}")
                self.logger.error(traceback.format_exc())
        
        # No primeiro passo, criar um evento de plano se disponível
        if self.steps == 1 and model_output and hasattr(model_output, 'current_state'):
            try:
                plan_steps = []
                if hasattr(model_output.current_state, 'steps') and model_output.current_state.steps:
                    plan_steps = [step for step in model_output.current_state.steps]
                    
                plan_event = {
                    "event_type": "agent.plan",
                    "plan": plan_steps,
                    "timestamp": datetime.now().isoformat()
                }
                
                if self.agent_tracker and hasattr(self.agent_tracker, 'callback'):
                    await self.agent_tracker.callback(plan_event)
                    self.logger.info(f"Plano com {len(plan_steps)} passos registrado")
            except Exception as e:
                self.logger.error(f"Erro ao extrair plano: {str(e)}")
                self.logger.error(traceback.format_exc())

class BrowserUseLogInterceptor(logging.Handler):
    """
    Interceptador de logs para capturar pensamentos e detalhes de navegação 
    durante o uso do browser pelo LLM.
    
    Captura pensamentos do LLM sem necessidade de callbacks específicos.
    """
    
    # Padrões regex para detectar diferentes tipos de mensagens
    PATTERNS = {
        # Padrões para passos
        "step": r"📍 Step (\d+)",
        "step_alt": r"Step (\d+):",
        "step_numeric": r"Step (\d+) \-",
        "z2b_step": r"Z2B Step (\d+)",
        "step_start": r"Begin Step (\d+)",
        "step_complete": r"Step (\d+) completed",
        "z2b_step_complete": r"Z2B Step (\d+) completed",
        
        # Padrões para avaliações
        "eval": r"(👍|👎|🤷|⚠) Eval: (.*)",
        "eval_status": r"(Success|Failure|Uncertain) - (.*)",
        "eval_alt": r"Evaluation: (.*)",
        "eval_broader": r"(evaluate|assessed|evaluation|assessment): (.*)",
        
        # Padrões para memórias
        "memory": r"🧠 Memory: (.*)",
        "memory_alt": r"Memory: (.*)",
        "memory_content": r"I remember that (.*)",
        "memory_broader": r"(remembered|recalling|recalled): (.*)",
        
        # Padrões para objetivos
        "next_goal": r"🎯 Next goal: (.*)",
        "next_goal_alt": r"Next goal: (.*)",
        "goal_current": r"Current goal: (.*)",
        "goal_broader": r"(goal is to|aiming to|planning to): (.*)",
        
        # Padrões para pensamentos gerais
        "thought": r"(🛠️|💭) (.*)",
        "thought_alt": r"Thinking: (.*)",
        "thought_broader": r"(thought|thinking|considering|analyzed|analyzed): (.*)",
        
        # Padrões para ações
        "action": r"Action: (.*)",
        "action_result": r"Result: (.*)",
        
        # Padrões para informações de LLM
        "llm_request": r"LLM Request: model=(.*), prompt=(.*), tokens=(\d+)",
        "llm_request_alt": r"Sending request to (.*) with (\d+) tokens",
        "llm_response": r"LLM Response: model=(.*), response=(.*), tokens=(\d+)",
        "llm_response_alt": r"Received response from (.*) with (\d+) tokens",
        "llm_cost": r"Estimated cost: \$([\d\.]+)",
        "llm_cost_alt": r"Cost: \$([\d\.]+)"
    }
    
    def __init__(self, 
                 callback=None, 
                 callback_pensamento=None, 
                 log_dir=None, 
                 debug_mode=False, 
                 message_cache_size=1000):
        """
        Inicializa o interceptador de logs.
        
        Args:
            callback (function, optional): Callback para passos completos.
            callback_pensamento (function, optional): Callback para pensamentos detectados.
            log_dir (str, optional): Diretório para salvar logs e timeline.
            debug_mode (bool, optional): Ativar modo de depuração com logs adicionais.
            message_cache_size (int, optional): Tamanho do cache para detecção de duplicatas.
        """
        super().__init__()
        
        # Inicializar com tracking desativado até start_tracking ser chamado
        self.tracking_enabled = False
        
        # Callbacks para processar dados detectados
        self.callback = callback
        self.callback_pensamento = callback_pensamento
        
        # Diretório para salvar logs
        self.log_dir = log_dir
        
        # Loop de eventos para tarefas assíncronas
        self.loop = asyncio.get_event_loop()
        self._pending_tasks = set()
        
        # Modo de depuração
        self.debug_mode = debug_mode
        
        # Inicializar estruturas de dados para tracking
        self.timeline = []
        self.current_step = None
        self.last_step_number = 0
        self.start_time = datetime.now()
        
        # Cache para evitar duplicação de mensagens
        self.recent_messages = set()
        self.message_cache_size = message_cache_size
        
        # Pensamentos por passo
        self.thoughts_by_step = {}
        
        # Contadores
        self.total_thoughts_detected = 0
        self.total_thoughts_processed = 0
        
        # Estatísticas
        self.thought_stats = {
            "evaluation": 0,
            "memory": 0,
            "goal": 0,
            "thought": 0,
            "unknown": 0
        }
        
        # Estatísticas de LLM
        self.llm_stats = {
            "total_calls": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0,
            "models": {}
        }
        
        # Lista de mensagens não categorizadas
        self.unknown_messages = []
        
        # Se temos um diretório de log, garantir que existe
        if self.log_dir and not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # Inicializar timeline se temos log_dir
        if log_dir:
            # Garantir que o diretório existe
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                
            # Usar a versão estendida do TimelineBuilder
            self.timeline_builder = TimelineBuilderExtended(title="Browser Use Timeline")
            self.timeline_builder.start_timer()
            self.log_dir = log_dir
            
            # Inicializar arquivo de mensagens desconhecidas
            self.unknown_messages = []
            self.unknown_messages_file = os.path.join(log_dir, "unknown_messages.json")
            
            # Salvar periodicamente as mensagens desconhecidas
            self._save_unknown_messages_task = asyncio.create_task(self._save_unknown_messages_periodically())
            
        # Salvar callbacks
        self.callback = callback
        self.callback_pensamento = callback_pensamento
        
        # Registrar no logger raiz
        logging.getLogger().addHandler(self)
        logger.info(f"Interceptador de logs instalado {' com diretório de log' if log_dir else ''}")
        
        # Não deve retornar nada (remover o "return self")
        
    def instalar(self):
        """
        Ativa o tracking do interceptador de logs.
        Este método deve ser chamado após a criação da instância para iniciar
        o monitoramento efetivo das mensagens de log.
        """
        if self.tracking_enabled:
            logger.warning("Interceptador já está ativo. Reiniciando tracking.")
            
        # Ativar tracking
        self.tracking_enabled = True
        self.start_time = datetime.now()
        
        # Registrar evento de início na timeline se disponível
        if hasattr(self, 'timeline_builder'):
            self.timeline_builder.add_event(
                title="Interceptador Ativado",
                description="Início do tracking de logs do browser-use",
                icon="▶️",
                timestamp=self.start_time.isoformat()
            )
            
        # Inicializar ou redefinir contadores
        self.total_thoughts_detected = 0
        self.total_thoughts_processed = 0
        self.thought_stats = {
            "evaluation": 0,
            "memory": 0,
            "goal": 0,
            "thought": 0,
            "unknown": 0
        }
        
        # Inicializar estruturas para LLM tracking
        self.llm_tracking = {
            "current_model": None,
            "current_prompt_tokens": 0,
            "current_completion_tokens": 0,
            "current_cost": 0.0,
            "current_step": None,
            "pending_llm_data": {}
        }
        
        logger.info("Tracking de browser-use ativado")
        return True
        
    async def _save_unknown_messages_periodically(self):
        """
        Salva periodicamente as mensagens desconhecidas no arquivo JSON.
        """
        try:
            while True:
                await asyncio.sleep(30)  # Salvar a cada 30 segundos
                if hasattr(self, 'unknown_messages') and self.unknown_messages and hasattr(self, 'unknown_messages_file'):
                    try:
                        with open(self.unknown_messages_file, 'w', encoding='utf-8') as f:
                            json.dump(self.unknown_messages, f, indent=2, ensure_ascii=False)
                        logger.debug(f"Mensagens desconhecidas salvas em {self.unknown_messages_file}")
                    except Exception as e:
                        logger.error(f"Erro ao salvar mensagens desconhecidas: {e}")
        except asyncio.CancelledError:
            # Tarefa cancelada, salvar uma última vez
            if hasattr(self, 'unknown_messages') and self.unknown_messages and hasattr(self, 'unknown_messages_file'):
                try:
                    with open(self.unknown_messages_file, 'w', encoding='utf-8') as f:
                        json.dump(self.unknown_messages, f, indent=2, ensure_ascii=False)
                    logger.debug(f"Mensagens desconhecidas salvas em {self.unknown_messages_file} (final)")
                except Exception as e:
                    logger.error(f"Erro ao salvar mensagens desconhecidas (final): {e}")
        except Exception as e:
            logger.error(f"Erro em _save_unknown_messages_periodically: {e}")
    
    def get_resumo_execucao(self) -> Dict[str, Any]:
        """
        Gera um resumo da execução atual
        
        Returns:
            Dict[str, Any]: Resumo da execução
        """
        duracao = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "prompt": self.prompt[:100] + "..." if self.prompt and len(self.prompt) > 100 else self.prompt,
            "inicio": self.start_time.isoformat(),
            "duracao_segundos": duracao,
            "total_eventos": self.total_events,
            "passos": self.steps_count,
            "navegacoes": self.navigation_count,
            "interacoes": self.interaction_count,
            "screenshots": self.screenshot_count,
            "erros": self.error_count,
            "distribuicao_categorias": self.stats_por_categoria
        }
    
    def get_thinking_logs(self) -> List[Dict[str, Any]]:
        """
        Extrai os logs de pensamento do agente para visualização do raciocínio.
        
        Returns:
            List[Dict[str, Any]]: Lista de registros de pensamento do agente
        """
        thinking_logs = []
        
        for evento in self.eventos:
            # Verificar se é um passo do agente que contém pensamentos
            if evento["tipo"] == "browser_use.agent.step":
                step_data = {
                    "step": evento["dados"].get("step", 0),
                    "timestamp": evento["timestamp"],
                    "thought": None,
                    "evaluation": None,
                    "memory": None,
                    "next_goal": None,
                    "action": None
                }
                
                # Extrair campos relevantes
                for campo in ["thought", "evaluation", "memory", "next_goal"]:
                    # Verificar no nível superior do evento (adicionados pelo process_event)
                    if campo in evento and evento[campo]:
                        step_data[campo] = evento[campo]
                    # Verificar nos dados do evento
                    elif campo in evento["dados"] and evento["dados"][campo]:
                        step_data[campo] = evento["dados"][campo]
                
                # Extrair ação
                if "action" in evento["dados"] and evento["dados"]["action"]:
                    action = evento["dados"]["action"]
                    if isinstance(action, dict):
                        step_data["action"] = action
                
                # Adicionar à lista se tiver pelo menos um campo de pensamento
                if any(step_data[campo] for campo in ["thought", "evaluation", "memory", "next_goal"]):
                    thinking_logs.append(step_data)
        
        return thinking_logs
    
    def save_thinking_logs(self, filename=None):
        """
        Salva os logs de pensamento do agente em um arquivo separado para facilitar análise.
        
        Args:
            filename: Nome do arquivo para salvar os logs (padrão: thinking_logs.json)
        """
        logs = self.get_thinking_logs()
        
        if not logs:
            logger.warning("Nenhum log de pensamento encontrado para salvar")
            return
        
        if not filename:
            filename = os.path.join(self.log_dir, "thinking_logs.json")
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Logs de pensamento salvos em: {filename}")
        except Exception as e:
            logger.error(f"Erro ao salvar logs de pensamento: {str(e)}")

    async def track_execution(self, agent, prompt, **kwargs):
        """
        Inicia o rastreamento da execução do agente
        
        Args:
            agent: Instância do agente a ser rastreado
            prompt: Prompt para execução do agente
            **kwargs: Argumentos adicionais para o método execute_prompt_task
            
        Returns:
            Resultado da execução do agente
        """
        self.set_prompt(prompt)
        logger.info(f"Iniciando rastreamento do agente com prompt: '{prompt[:100]}...' (truncado)")
        
        try:
            # Registrar evento de início
            await self.process_event({
                "type": "agent.start",
                "prompt": prompt,
                "timestamp": datetime.now().isoformat()
            })
            
            # Instalar interceptador de logs do browser-use
            self.log_interceptor = BrowserUseLogInterceptor(self.callback)
            self.log_interceptor.instalar()
            
            # Tentar registrar callbacks no browser-use se disponível
            # Isso é feito sem afetar o fluxo atual
            try:
                if hasattr(agent, 'z2b_agent') and agent.z2b_agent and hasattr(agent.z2b_agent, 'browser_agent'):
                    browser_agent = agent.z2b_agent.browser_agent
                    self.register_browser_use_callbacks(browser_agent)
            except Exception as e:
                logger.warning(f"Não foi possível registrar callbacks para o browser-use: {str(e)}")
            
            # Executar o agente com nosso callback
            logger.info("Executando o agente com callback do tracker")
            start_execution = time.time()
            result = await agent.execute_prompt_task(prompt, callback=self.callback, **kwargs)
            execution_time = time.time() - start_execution
            
            # Remover interceptador de logs
            if hasattr(self, 'log_interceptor'):
                self.log_interceptor.desinstalar()
            
            # Registrar evento de conclusão
            await self.process_event({
                "type": "agent.complete",
                "result": result,
                "execution_time_seconds": execution_time,
                "summary": self.get_resumo_execucao(),
                "timestamp": datetime.now().isoformat()
            })
            
            # Salvar resumo em arquivo separado se auto_summarize estiver ativado
            if self.auto_summarize:
                resumo_file = os.path.join(self.log_dir, "execution_summary.json")
                with open(resumo_file, "w", encoding="utf-8") as f:
                    json.dump(self.get_resumo_execucao(), f, indent=2, ensure_ascii=False)
                
                # Salvar logs de pensamento também
                self.save_thinking_logs()
            
            return result
            
        except Exception as e:
            logger.error(f"Erro durante o rastreamento do agente: {e}")
            
            # Remover interceptador de logs em caso de erro
            if hasattr(self, 'log_interceptor'):
                self.log_interceptor.desinstalar()
            
            # Registrar o erro
            await self.process_event({
                "type": "agent.error",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now().isoformat()
            })
            
            # Relançar a exceção para tratamento externo
            raise

    def get_unknown_messages(self):
        """Retorna as mensagens desconhecidas capturadas para depuração"""
        return self.unknown_messages
         
    def get_thoughts_summary(self):
        """
        Gera um resumo dos pensamentos capturados.
        
        Returns:
            dict: Resumo de pensamentos por categoria e estatísticas.
        """
        # Contadores
        total_pensamentos = self.total_thoughts_processed
        
        # Pensamentos por categoria
        pensamentos_por_categoria = {}
        for step_num, thoughts in self.thoughts_by_step.items():
            for thought in thoughts:
                category = thought.get("category", "unknown")
                if category not in pensamentos_por_categoria:
                    pensamentos_por_categoria[category] = []
                pensamentos_por_categoria[category].append(thought)
        
        # Contagens por categoria
        contagens_por_categoria = {
            categoria: len(pensamentos)
            for categoria, pensamentos in pensamentos_por_categoria.items()
        }
        
        # Construir resumo
        resumo = {
            "total_pensamentos": total_pensamentos,
            "pensamentos_por_categoria": contagens_por_categoria,
            "categorias_detectadas": list(pensamentos_por_categoria.keys()),
            "distribuicao_por_passo": {
                step_num: len(thoughts)
                for step_num, thoughts in self.thoughts_by_step.items()
            }
        }
        
        return resumo
        
    def get_steps_summary(self):
        """
        Gera um resumo dos passos processados.
        
        Returns:
            dict: Resumo de passos e estatísticas.
        """
        if not self.timeline:
            return {
                "total_passos": 0,
                "mensagem": "Nenhum passo processado ainda."
            }
            
        # Contadores
        total_passos = len(self.timeline)
        passos_completos = sum(1 for step in self.timeline if step.get("is_complete", False))
        
        # Calcular tempos médios e totais
        duracoes = []
        for step in self.timeline:
            if "start_timestamp" in step and "end_timestamp" in step:
                start = datetime.fromisoformat(step["start_timestamp"])
                end = datetime.fromisoformat(step["end_timestamp"])
                duracao_segundos = (end - start).total_seconds()
                duracoes.append(duracao_segundos)
        
        duracao_media = sum(duracoes) / len(duracoes) if duracoes else 0
        duracao_total = sum(duracoes)
        
        # Taxas de sucesso baseado em avaliações
        passos_com_avaliacao = 0
        passos_sucesso = 0
        
        for step in self.timeline:
            thoughts_by_category = step.get("thoughts_by_category", {})
            avaliacoes = thoughts_by_category.get("evaluation", [])
            
            if avaliacoes:
                passos_com_avaliacao += 1
                for avaliacao in avaliacoes:
                    conteudo = avaliacao.get("content", "").lower()
                    if "success" in conteudo or "sucesso" in conteudo or "bem-sucedido" in conteudo:
                        passos_sucesso += 1
                        break
        
        taxa_sucesso = passos_sucesso / passos_com_avaliacao if passos_com_avaliacao > 0 else 0
        
        # Resumo por passo
        resumo_passos = []
        for step in self.timeline:
            step_num = step.get("step")
            pensamentos = step.get("thoughts", [])
            
            # Contar pensamentos por categoria
            pensamentos_por_cat = {}
            for thought in pensamentos:
                cat = thought.get("category", "unknown")
                if cat not in pensamentos_por_cat:
                    pensamentos_por_cat[cat] = 0
                pensamentos_por_cat[cat] += 1
            
            # Determinar status
            status = "concluído" if step.get("is_complete", False) else "em andamento"
            
            # Calcular duração
            duracao = None
            if "start_timestamp" in step and "end_timestamp" in step:
                start = datetime.fromisoformat(step["start_timestamp"])
                end = datetime.fromisoformat(step["end_timestamp"])
                duracao = (end - start).total_seconds()
            
            # Adicionar ao resumo
            resumo_passos.append({
                "passo": step_num,
                "status": status,
                "duracao_segundos": duracao,
                "total_pensamentos": len(pensamentos),
                "pensamentos_por_categoria": pensamentos_por_cat
            })
        
        # Construir resumo completo
        resumo = {
            "total_passos": total_passos,
            "passos_completos": passos_completos,
            "taxa_completude": passos_completos / total_passos if total_passos > 0 else 0,
            "duracao_media_segundos": duracao_media,
            "duracao_total_segundos": duracao_total,
            "passos_com_avaliacao": passos_com_avaliacao,
            "passos_sucesso": passos_sucesso,
            "taxa_sucesso": taxa_sucesso,
            "detalhes_passos": resumo_passos
        }
        
        return resumo
        
    def _process_llm_data(self, pattern_name, match, full_message):
        """
        Processa dados de LLM capturados de mensagens de log.
        
        Args:
            pattern_name (str): Nome do padrão correspondido
            match: Objeto de correspondência regex
            full_message (str): Mensagem completa
        """
        try:
            # Incrementar contador de chamadas de LLM
            self.llm_stats["total_calls"] += 1
            
            if pattern_name in ["llm_request", "llm_request_alt"]:
                # Processar requisição de LLM
                if pattern_name == "llm_request":
                    model, prompt, tokens = match.groups()
                    tokens = int(tokens)
                else:  # llm_request_alt
                    model, tokens = match.groups()
                    tokens = int(tokens)
                    prompt = "N/A"  # Não disponível no formato alternativo
                
                # Atualizar estatísticas
                self.llm_stats["total_tokens"] += tokens
                
                # Registrar modelo
                if model not in self.llm_stats["models"]:
                    self.llm_stats["models"][model] = {
                        "requests": 0,
                        "responses": 0,
                        "tokens": 0,
                        "cost": 0.0
                    }
                
                self.llm_stats["models"][model]["requests"] += 1
                self.llm_stats["models"][model]["tokens"] += tokens
                
                logger.debug(f"Requisição LLM registrada: modelo={model}, tokens={tokens}")
                
            elif pattern_name in ["llm_response", "llm_response_alt"]:
                # Processar resposta de LLM
                if pattern_name == "llm_response":
                    model, response, tokens = match.groups()
                    tokens = int(tokens)
                else:  # llm_response_alt
                    model, tokens = match.groups()
                    tokens = int(tokens)
                    response = "N/A"  # Não disponível no formato alternativo
                
                # Atualizar estatísticas
                self.llm_stats["total_tokens"] += tokens
                
                # Registrar modelo
                if model not in self.llm_stats["models"]:
                    self.llm_stats["models"][model] = {
                        "requests": 0,
                        "responses": 0,
                        "tokens": 0,
                        "cost": 0.0
                    }
                
                self.llm_stats["models"][model]["responses"] += 1
                self.llm_stats["models"][model]["tokens"] += tokens
                
                logger.debug(f"Resposta LLM registrada: modelo={model}, tokens={tokens}")
                
            elif pattern_name in ["llm_cost", "llm_cost_alt"]:
                # Processar custo de LLM
                cost = float(match.group(1))
                
                # Atualizar estatísticas
                self.llm_stats["estimated_cost"] += cost
                
                # Tentar determinar o modelo na mensagem
                model_match = re.search(r"model[=:]([a-zA-Z0-9\-]+)", full_message)
                if model_match:
                    model = model_match.group(1)
                    if model in self.llm_stats["models"]:
                        self.llm_stats["models"][model]["cost"] += cost
                
                logger.debug(f"Custo LLM registrado: ${cost:.4f}")
                
        except Exception as e:
            logger.error(f"Erro ao processar dados de LLM: {e}")
    
    def get_unknown_messages(self):
        """Retorna as mensagens desconhecidas capturadas para depuração"""
        return self.unknown_messages
        
    def save_timeline(self, filepath):
        """Salva a timeline em um arquivo JSON"""
        return self.timeline_builder.save_timeline(filepath)
     
    def get_timeline(self):
        """Retorna a timeline completa"""
        return self.timeline_builder.get_timeline()

    def get_thoughts_for_step(self, step_number):
        """
        Retorna pensamentos para um passo específico.
        
        Args:
            step_number: Número do passo
            
        Returns:
            Lista de pensamentos ou None se não houver
        """
        return self.thoughts_by_step.get(step_number, [])

    def _update_thought_stats(self, category):
        """
        Atualiza estatísticas de pensamentos.
        
        Args:
            category (str): Categoria do pensamento.
        """
        if category in self.thought_stats:
            self.thought_stats[category] += 1
        else:
            self.thought_stats["unknown"] += 1
            
        # Log para diagnóstico
        categories_count = ", ".join([f"{k}: {v}" for k, v in self.thought_stats.items() if v > 0])
        logger.debug(f"Estatísticas de pensamentos atualizadas: {categories_count}")

def similarity_score(text1, text2):
    """
    Calcula um score de similaridade básico entre dois textos.
    Usado para detectar pensamentos duplicados.
    
    Args:
        text1 (str): Primeiro texto
        text2 (str): Segundo texto
        
    Returns:
        float: Score de similaridade entre 0 e 1
    """
    if not text1 or not text2:
        return 0
    
    # Normalizar textos
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()
    
    # Se os textos são idênticos, retornar 1
    if text1 == text2:
        return 1.0
    
    # Se um texto está contido no outro, retornar um score alto
    if text1 in text2 or text2 in text1:
        return 0.9
    
    # Calcular similaridade baseada em palavras comuns
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    # Calcular interseção e união
    common_words = words1.intersection(words2)
    all_words = words1.union(words2)
    
    # Evitar divisão por zero
    if not all_words:
        return 0
    
    # Calcular coeficiente de Jaccard
    return len(common_words) / len(all_words)

class AgentTracker:
    """
    Classe principal para rastreamento de execução de agentes.
    Permite capturar eventos, passos, pensamentos e estatísticas da execução.
    """
    def __init__(self, log_dir="agent_logs", include_screenshots=True, auto_summarize=True, compression_level=9):
        """
        Inicializa o rastreador de agente.
        
        Args:
            log_dir (str): Diretório para salvar logs e arquivos relacionados
            include_screenshots (bool): Se deve incluir screenshots nos logs
            auto_summarize (bool): Se deve gerar resumo automaticamente ao finalizar
            compression_level (int): Nível de compressão para screenshots (0-9)
        """
        self.logger = logging.getLogger("agent_tracker")
        
        # Configurar diretório de logs com timestamp para evitar sobrescrita
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = os.path.join(log_dir, f"agent_run_{timestamp}")
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Arquivo de log principal
        self.log_file = os.path.join(self.log_dir, "agent_events.json")
        
        # Configurações
        self.include_screenshots = include_screenshots
        self.auto_summarize = auto_summarize
        self.compression_level = compression_level
        
        # Estado interno
        self.eventos = []
        self.start_time = datetime.now()
        self.prompt = None
        
        # Contadores
        self.total_events = 0
        self.steps_count = 0
        self.navigation_count = 0
        self.interaction_count = 0
        self.screenshot_count = 0
        self.error_count = 0
        
        # Estatísticas por categoria
        self.stats_por_categoria = {}
        
        # Inicializar
        self.logger.info(f"AgentTracker inicializado. Logs serão salvos em: {self.log_dir}")
    
    def set_prompt(self, prompt):
        """Define o prompt utilizado para a execução"""
        self.prompt = prompt
    
    async def callback(self, event_data):
        """
        Callback principal para processar eventos do agente.
        Este método é chamado pelo agente durante a execução.
        
        Args:
            event_data (dict): Dados do evento a ser processado
        """
        if not event_data:
            return
            
        # Incrementar contador de eventos
        self.total_events += 1
        
        # Processar o evento
        await self.process_event(event_data)
    
    async def process_event(self, event_data):
        """
        Processa um evento do agente, categorizando-o e salvando nos logs.
        
        Args:
            event_data (dict): Dados do evento a ser processado
        """
        # Adicionar timestamp se não existir
        if "timestamp" not in event_data:
            event_data["timestamp"] = datetime.now().isoformat()
            
        # Determinar tipo de evento
        event_type = event_data.get("event_type") or event_data.get("type", "unknown")
        
        # Categorizar evento
        categoria = EventCategorizador.categorizar_evento(event_type)
        
        # Atualizar contadores
        if categoria == EventCategorizador.CATEGORIA_NAVEGACAO:
            self.navigation_count += 1
        elif categoria == EventCategorizador.CATEGORIA_INTERACAO:
            self.interaction_count += 1
        elif categoria == EventCategorizador.CATEGORIA_SCREENSHOT:
            self.screenshot_count += 1
        elif categoria == EventCategorizador.CATEGORIA_ERRO:
            self.error_count += 1
            
        # Atualizar estatísticas por categoria
        if categoria not in self.stats_por_categoria:
            self.stats_por_categoria[categoria] = 0
        self.stats_por_categoria[categoria] += 1
        
        # Processar passos de agente
        if event_type in ["browser_use.agent.step", "agent.step"]:
            self.steps_count += 1
            
            # Extrair pensamentos se presentes
            for field in ["thought", "evaluation", "memory", "next_goal"]:
                if field in event_data and event_data[field]:
                    # Adicionar ao evento para facilitar visualização
                    event_data[f"{field}_present"] = True
        
        # Processar screenshots se configurado
        if self.include_screenshots and "screenshot" in event_data:
            try:
                screenshot_data = event_data["screenshot"]
                # Se for uma string base64, salvar como arquivo
                if isinstance(screenshot_data, str) and screenshot_data.startswith("data:image"):
                    # Extrair o conteúdo base64
                    content_type, base64_data = screenshot_data.split(",", 1)
                    
                    # Criar um nome de arquivo baseado no timestamp e contador
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    screenshot_filename = f"screenshot_{ts}_{self.screenshot_count}.png"
                    screenshot_path = os.path.join(self.log_dir, screenshot_filename)
                    
                    # Decodificar e salvar
                    with open(screenshot_path, "wb") as f:
                        f.write(base64.b64decode(base64_data))
                    
                    # Substituir o dado base64 pelo nome do arquivo para economizar espaço
                    event_data["screenshot"] = screenshot_filename
                    self.logger.debug(f"Screenshot salvo em: {screenshot_path}")
            except Exception as e:
                self.logger.error(f"Erro ao processar screenshot: {str(e)}")
                # Manter o evento mesmo se falhar o processamento do screenshot
        
        # Adicionar categoria ao evento
        event_data["categoria"] = categoria
        
        # Salvar o evento na lista
        self.eventos.append({
            "tipo": event_type,
            "categoria": categoria,
            "timestamp": event_data["timestamp"],
            "dados": event_data
        })
        
        # Salvar o log atualizado
        self._save_log()
    
    def _save_log(self):
        """Salva os eventos em um arquivo JSON"""
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(self.eventos, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erro ao salvar log: {str(e)}")
    
    def register_browser_use_callbacks(self, agent):
        """
        Registra callbacks para um agente browser-use.
        
        Args:
            agent: Instância do agente browser-use
            
        Returns:
            bool: True se os callbacks foram registrados com sucesso
        """
        try:
            # Registrar interceptador de logs se ainda não tiver sido registrado
            interceptor = BrowserUseLogInterceptor(self.callback)
            interceptor.instalar()
            self.log_interceptor = interceptor
            
            # Criar rastreador de browser-use se necessário
            tracker = self.get_browser_use_tracker()
            
            # Registrar callback no agente
            if hasattr(agent, 'register_callback'):
                agent.register_callback(tracker.step_callback)
                logger.info("Callback do AgentTracker registrado no agente browser-use")
                return True
            else:
                logger.warning("Agente não tem método register_callback. Callback não registrado.")
                # O interceptador de logs ainda capturará as informações
                return True
        except Exception as e:
            logger.error(f"Erro ao registrar callbacks: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def get_browser_use_tracker(self):
        """
        Obtém ou cria um rastreador de browser-use associado a este tracker.
        
        Returns:
            BrowserUseTracker: Instância do rastreador
        """
        if not hasattr(self, 'browser_use_tracker'):
            self.browser_use_tracker = BrowserUseTracker(self)
        return self.browser_use_tracker
    
    async def track_execution(self, agent, prompt, **kwargs):
        """
        Inicia o rastreamento da execução do agente
        
        Args:
            agent: Instância do agente a ser rastreado
            prompt: Prompt para execução do agente
            **kwargs: Argumentos adicionais para o método execute_prompt_task
            
        Returns:
            Resultado da execução do agente
        """
        self.set_prompt(prompt)
        logger.info(f"Iniciando rastreamento do agente com prompt: '{prompt[:100]}...' (truncado)")
        
        try:
            # Registrar evento de início
            await self.process_event({
                "type": "agent.start",
                "prompt": prompt,
                "timestamp": datetime.now().isoformat()
            })
            
            # Instalar interceptador de logs do browser-use
            self.log_interceptor = BrowserUseLogInterceptor(self.callback)
            self.log_interceptor.instalar()
            
            # Tentar registrar callbacks no browser-use se disponível
            # Isso é feito sem afetar o fluxo atual
            try:
                if hasattr(agent, 'z2b_agent') and agent.z2b_agent and hasattr(agent.z2b_agent, 'browser_agent'):
                    browser_agent = agent.z2b_agent.browser_agent
                    self.register_browser_use_callbacks(browser_agent)
            except Exception as e:
                logger.warning(f"Não foi possível registrar callbacks para o browser-use: {str(e)}")
            
            # Executar o agente com nosso callback
            logger.info("Executando o agente com callback do tracker")
            start_execution = time.time()
            result = await agent.execute_prompt_task(prompt, callback=self.callback, **kwargs)
            execution_time = time.time() - start_execution
            
            # Remover interceptador de logs
            if hasattr(self, 'log_interceptor'):
                self.log_interceptor.desinstalar()
            
            # Registrar evento de conclusão
            await self.process_event({
                "type": "agent.complete",
                "result": result,
                "execution_time_seconds": execution_time,
                "summary": self.get_resumo_execucao(),
                "timestamp": datetime.now().isoformat()
            })
            
            # Salvar resumo em arquivo separado se auto_summarize estiver ativado
            if self.auto_summarize:
                resumo_file = os.path.join(self.log_dir, "execution_summary.json")
                with open(resumo_file, "w", encoding="utf-8") as f:
                    json.dump(self.get_resumo_execucao(), f, indent=2, ensure_ascii=False)
                
                # Salvar logs de pensamento também
                self.save_thinking_logs()
            
            return result
            
        except Exception as e:
            logger.error(f"Erro durante o rastreamento do agente: {e}")
            
            # Remover interceptador de logs em caso de erro
            if hasattr(self, 'log_interceptor'):
                self.log_interceptor.desinstalar()
            
            # Registrar o erro
            await self.process_event({
                "type": "agent.error",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now().isoformat()
            })
            
            # Relançar a exceção para tratamento externo
            raise
    
    def get_resumo_execucao(self) -> Dict[str, Any]:
        """
        Gera um resumo da execução atual
        
        Returns:
            Dict[str, Any]: Resumo da execução
        """
        duracao = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "prompt": self.prompt[:100] + "..." if self.prompt and len(self.prompt) > 100 else self.prompt,
            "inicio": self.start_time.isoformat(),
            "duracao_segundos": duracao,
            "total_eventos": self.total_events,
            "passos": self.steps_count,
            "navegacoes": self.navigation_count,
            "interacoes": self.interaction_count,
            "screenshots": self.screenshot_count,
            "erros": self.error_count,
            "distribuicao_categorias": self.stats_por_categoria
        }
    
    def get_thinking_logs(self) -> List[Dict[str, Any]]:
        """
        Extrai os logs de pensamento do agente para visualização do raciocínio.
        
        Returns:
            List[Dict[str, Any]]: Lista de registros de pensamento do agente
        """
        thinking_logs = []
        
        for evento in self.eventos:
            # Verificar se é um passo do agente que contém pensamentos
            if evento["tipo"] == "browser_use.agent.step":
                step_data = {
                    "step": evento["dados"].get("step", 0),
                    "timestamp": evento["timestamp"],
                    "thought": None,
                    "evaluation": None,
                    "memory": None,
                    "next_goal": None,
                    "action": None
                }
                
                # Extrair campos relevantes
                for campo in ["thought", "evaluation", "memory", "next_goal"]:
                    # Verificar no nível superior do evento (adicionados pelo process_event)
                    if campo in evento and evento[campo]:
                        step_data[campo] = evento[campo]
                    # Verificar nos dados do evento
                    elif campo in evento["dados"] and evento["dados"][campo]:
                        step_data[campo] = evento["dados"][campo]
                
                # Extrair ação
                if "action" in evento["dados"] and evento["dados"]["action"]:
                    action = evento["dados"]["action"]
                    if isinstance(action, dict):
                        step_data["action"] = action
                
                # Adicionar à lista se tiver pelo menos um campo de pensamento
                if any(step_data[campo] for campo in ["thought", "evaluation", "memory", "next_goal"]):
                    thinking_logs.append(step_data)
        
        return thinking_logs
    
    def save_thinking_logs(self, filename=None):
        """
        Salva os logs de pensamento do agente em um arquivo separado para facilitar análise.
        
        Args:
            filename: Nome do arquivo para salvar os logs (padrão: thinking_logs.json)
        """
        logs = self.get_thinking_logs()
        
        if not logs:
            logger.warning("Nenhum log de pensamento encontrado para salvar")
            return
        
        if not filename:
            filename = os.path.join(self.log_dir, "thinking_logs.json")
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Logs de pensamento salvos em: {filename}")
        except Exception as e:
            logger.error(f"Erro ao salvar logs de pensamento: {str(e)}")

async def track_agent_execution(agent, prompt, **kwargs):
    """
    Função auxiliar para rastrear a execução de um agente.
    
    Args:
        agent: Instância do agente a ser rastreado
        prompt: Prompt a ser executado
        **kwargs: Argumentos adicionais para repassar ao AgentTracker
        
    Returns:
        tuple: (resultado, tracker) - Resultado da execução e instância do tracker
    """
    # Extrair parâmetros específicos do tracker
    tracker_kwargs = {}
    for param in ["log_dir", "include_screenshots", "auto_summarize", "compression_level"]:
        if param in kwargs:
            tracker_kwargs[param] = kwargs.pop(param)
    
    # Criar rastreador
    tracker = AgentTracker(**tracker_kwargs)
    
    # Iniciar rastreamento
    result = await tracker.track_execution(agent, prompt, **kwargs)
    
    return result, tracker