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
    
    def save_timeline(self, filepath):
        """
        Salva a timeline em um arquivo JSON com estrutura enriquecida.
        
        Args:
            filepath (str): Caminho do arquivo onde a timeline será salva
            
        Returns:
            str: Caminho do arquivo salvo
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
            "events": self.events,
            "total_steps": len(self.steps),
            "total_thoughts": thoughts_summary["thought_counts"]["total"]
        }
        
        # Salvar no arquivo
        try:
            # Garantir que o diretório existe
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(timeline_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Timeline salva em {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Erro ao salvar timeline: {e}")
            return None
    
    def get_timeline(self):
        """
        Retorna os dados da timeline formatados para uso externo.
        
        Returns:
            dict: Dados completos da timeline
        """
        # Calcular resumos
        steps_summary = self.get_steps_summary()
        thoughts_summary = self.get_thoughts_summary()
        
        # Calcular duração se possível
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        # Converter o dicionário de passos para uma lista
        timeline_steps = []
        for step_num, step_data in self.steps.items():
            # Adicionar o número do passo no objeto de passo para manter consistência
            step_copy = step_data.copy()
            step_copy["step_number"] = step_num
            timeline_steps.append(step_copy)
        
        # Ordenar os passos por número
        timeline_steps.sort(key=lambda x: x.get("step_number", 0))
        
        return {
            "title": self.title,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration,
            "timeline": timeline_steps,  # Agora é uma lista ordenada
            "events": self.events,
            "total_steps": len(self.steps),
            "total_thoughts": thoughts_summary["thought_counts"]["total"],
            "steps_summary": steps_summary,
            "thoughts_summary": thoughts_summary
        }

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
        "action_json": r"Action: (\{.*?\})",
        "action_json_extended": r"Action JSON: (\{.*?\})",
        "action_json_with_type": r"Action \(([a-zA-Z_]+)\): (\{.*?\})",
        "navigation_action": r"Navigation action: (\{.*?\})",
        "click_action": r"Click action: (\{.*?\})",
        "extraction_action": r"Extraction action: (\{.*?\})",
        "form_action": r"Form action: (\{.*?\})",
        
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
        
    def emit(self, record):
        """
        Processa um registro de log.
        
        Este método é obrigatório para todos os Handlers de logging e é 
        chamado automaticamente pelo sistema de logging do Python quando
        uma mensagem é registrada.
        
        Args:
            record: O registro de log a ser processado
        """
        if not self.tracking_enabled:
            return
            
        try:
            # Formatar a mensagem do log
            msg = self.format(record)
            
            # Processar apenas mensagens do módulo browser_use (mais eficiente)
            if not record.name.startswith("browser_use"):
                return
                
            # Verificar se a mensagem corresponde a algum dos padrões conhecidos
            self._process_message(msg)
        except Exception as e:
            # Capturar qualquer erro para não quebrar o fluxo de logging
            logger.error(f"Erro ao processar log no interceptador: {e}")
    
    def _process_message(self, message):
        """
        Processa uma mensagem de log para extrair informações.
        
        Args:
            message (str): A mensagem de log formatada
        """
        # Verificar se é uma mensagem duplicada (para evitar processamento repetido)
        if message in self.recent_messages:
            return
            
        # Adicionar à lista de mensagens recentes
        self.recent_messages.add(message)
        
        # Limitar o tamanho do cache de mensagens
        if len(self.recent_messages) > self.message_cache_size:
            self.recent_messages.pop()
            
        # Processar a mensagem com os padrões
        matched = False
        
        # Verificar cada padrão por correspondência
        for pattern_name, pattern in self.PATTERNS.items():
            try:
                match = re.search(pattern, message)
                if match:
                    matched = True
                    
                    # Processar de acordo com o tipo de padrão
                    if pattern_name.startswith("step"):
                        # Extrair número do passo
                        step_number = int(match.group(1))
                        self._process_step(step_number, pattern_name, message)
                    elif pattern_name.startswith("eval"):
                        # Processar avaliação
                        self._add_thought_to_step("evaluation", match.group(2) if len(match.groups()) > 1 else match.group(1), message)
                    elif pattern_name.startswith("memory"):
                        # Processar memória
                        self._add_thought_to_step("memory", match.group(1), message)
                    elif pattern_name.startswith("next_goal") or pattern_name.startswith("goal"):
                        # Processar próximo objetivo
                        self._add_thought_to_step("next_goal", match.group(1), message)
                    elif pattern_name.startswith("thought"):
                        # Processar pensamento
                        content = match.group(2) if len(match.groups()) > 1 else match.group(1)
                        self._add_thought_to_step("thought", content, message)
                    elif pattern_name.startswith("action") or pattern_name.endswith("action"):
                        # Processar ação
                        if pattern_name == "action_json_with_type":
                            # Este padrão captura dois grupos: o tipo da ação e o JSON
                            action_type = match.group(1)
                            content = match.group(2)
                            self._process_action(pattern_name, content, message, action_type)
                        else:
                            # Padrões normais capturam apenas o conteúdo
                            content = match.group(1)
                            self._process_action(pattern_name, content, message)
                    elif pattern_name.startswith("llm"):
                        # Processar dados de LLM
                        self._process_llm_data(pattern_name, match, message)
            except Exception as e:
                logger.error(f"Erro ao processar padrão {pattern_name}: {e}")
                
        # Se não corresponder a nenhum padrão conhecido, registrar como desconhecido
        if not matched:
            # Verificar se parece ser uma mensagem de pensamento ou passo
            if any(keyword in message.lower() for keyword in ["thought", "thinking", "step", "memory", "goal", "eval"]):
                if self.debug_mode:
                    logger.debug(f"Mensagem potencialmente relevante sem correspondência: {message}")
                
                # Registrar para análise posterior
                if hasattr(self, 'unknown_messages'):
                    self.unknown_messages.append({
                        "message": message,
                        "timestamp": datetime.now().isoformat()
                    })
    
    def _process_step(self, step_number, pattern_name, message):
        """
        Processa um passo identificado em uma mensagem de log.
        
        Args:
            step_number (int): Número do passo identificado
            pattern_name (str): Nome do padrão que identificou o passo
            message (str): Mensagem completa
        """
        # Garantir que começa em 1, não em 0
        if step_number <= 0:
            logger.warning(f"Passo com número inválido {step_number}, ignorando")
            return
            
        # Detectar se é o início ou fim do passo
        is_start = pattern_name in ["step", "step_alt", "step_numeric", "z2b_step", "step_start"]
        is_complete = pattern_name in ["step_complete", "z2b_step_complete"]
        
        # Inicializar passo 1 se este for o primeiro passo detectado e for maior que 1
        if not self.timeline and step_number > 1:
            # Criar um passo inicial implícito
            self._create_implicit_step(1)
            logger.debug(f"Passo 1 inicial criado implicitamente quando detectado passo {step_number}")
        
        # Verificar se o passo já existe na timeline
        existing_step = None
        for step in self.timeline:
            if step.get("step_number") == step_number:
                existing_step = step
                break
                
        # Se o passo não existe e é um início de passo, criar um novo
        if not existing_step and (is_start or not is_complete):
            # Criar passo
            self.timeline.append({
                "step_number": step_number,
                "start_timestamp": datetime.now().isoformat(),
                "is_complete": False,
                "message": message,
                "thoughts": [],
                "thoughts_by_category": {},
                "llm_events": []
            })
            logger.debug(f"Novo passo {step_number} iniciado")
            self.last_step_number = step_number
            self.current_step = step_number
            
            # Criar entrada no dicionário de pensamentos por passo
            if step_number not in self.thoughts_by_step:
                self.thoughts_by_step[step_number] = []
                
            # Registrar na timeline se disponível
            if hasattr(self, 'timeline_builder'):
                self.timeline_builder.add_step(
                    step_number=step_number,
                    content=f"Passo {step_number} iniciado",
                    status="in_progress"
                )
        
        # Se o passo existe e é um fim de passo, marcá-lo como completo
        elif existing_step and is_complete:
            existing_step["is_complete"] = True
            existing_step["end_timestamp"] = datetime.now().isoformat()
            existing_step["duration_seconds"] = (datetime.fromisoformat(existing_step["end_timestamp"]) - 
                                             datetime.fromisoformat(existing_step["start_timestamp"])).total_seconds()
            logger.debug(f"Passo {step_number} completado")
            
            # Atualizar na timeline se disponível
            if hasattr(self, 'timeline_builder'):
                # Obter dados do passo para atualização
                thoughts_by_category = existing_step.get("thoughts_by_category", {})
                evaluation = thoughts_by_category.get("evaluation", [])
                evaluation_text = evaluation[0] if evaluation else None
                memory = thoughts_by_category.get("memory", [])
                memory_text = memory[0] if memory else None
                next_goal = thoughts_by_category.get("next_goal", [])
                next_goal_text = next_goal[0] if next_goal else None
                
                # Determinar status com base na avaliação (se houver)
                status = "completed"
                if evaluation_text:
                    if any(term in evaluation_text.lower() for term in ["success", "successfully", "completed", "conseguiu"]):
                        status = "success"
                    elif any(term in evaluation_text.lower() for term in ["fail", "failed", "not able", "couldn't", "could not", "erro", "falhou"]):
                        status = "error"
                    elif any(term in evaluation_text.lower() for term in ["partial", "partially", "uncertain", "unclear", "parcial"]):
                        status = "warning"
                        
                # Atualizar o passo na timeline
                self.timeline_builder.add_step(
                    step_number=step_number,
                    content=f"Passo {step_number} completado",
                    is_complete=True,
                    evaluation=evaluation_text,
                    memory=memory_text,
                    next_goal=next_goal_text,
                    status=status
                )
            
            # Se completou um passo, e temos um callback registrado, chamar
            if self.callback:
                # Preparar dados do evento
                event_data = {
                    "event_type": "browser_use.agent.step",
                    "step": step_number,
                    "is_complete": True,
                    "timestamp": datetime.now().isoformat(),
                    "all_thoughts": existing_step.get("thoughts", []),
                    "thoughts_by_category": existing_step.get("thoughts_by_category", {})
                }
                
                # Adicionar pensamentos específicos
                for category in ["evaluation", "memory", "next_goal", "thought"]:
                    thoughts = existing_step.get("thoughts_by_category", {}).get(category, [])
                    if thoughts:
                        event_data[category] = thoughts[0]  # Usar o primeiro pensamento de cada categoria
                
                # Invocar o callback de forma assíncrona
                if asyncio.iscoroutinefunction(self.callback):
                    # Criar uma task para o callback e adicioná-la ao conjunto
                    task = asyncio.create_task(self.callback(event_data))
                    self._pending_tasks.add(task)
                    task.add_done_callback(self._pending_tasks.discard)
                else:
                    # Callback síncrono
                    try:
                        self.callback(event_data)
                    except Exception as e:
                        logger.error(f"Erro ao invocar callback: {e}")
    
    def _create_implicit_step(self, step_number):
        """
        Cria um passo implícito (não detectado explicitamente).
        
        Args:
            step_number (int): Número do passo a ser criado
        """
        # Criar passo na timeline
        self.timeline.append({
            "step_number": step_number,
            "start_timestamp": self.start_time.isoformat(),
            "is_complete": False,
            "message": f"[Passo {step_number} implícito]",
            "thoughts": [],
            "thoughts_by_category": {},
            "llm_events": [],
            "is_implicit": True
        })
        
        # Criar entrada no dicionário de pensamentos por passo
        if step_number not in self.thoughts_by_step:
            self.thoughts_by_step[step_number] = []
            
        # Registrar na timeline se disponível
        if hasattr(self, 'timeline_builder'):
            self.timeline_builder.add_step(
                step_number=step_number,
                content=f"Passo {step_number} (inicializado implicitamente)",
                status="in_progress",
                metadata={"is_implicit": True, "is_first_step": step_number == 1}
            )
            
        logger.debug(f"Passo {step_number} criado implicitamente")
        self.last_step_number = step_number
        self.current_step = step_number
    
    def _add_thought_to_step(self, thought_type, content, raw_message):
        """
        Adiciona um pensamento ao passo atual.
        
        Args:
            thought_type (str): Tipo de pensamento (evaluation, memory, next_goal, thought)
            content (str): Conteúdo do pensamento
            raw_message (str): Mensagem completa do log
        """
        # Incrementar contador total
        self.total_thoughts_detected += 1
        
        # Normalizar tipo de pensamento para categorias padrão
        normalized_type = self._normalize_thought_type(thought_type)
        
        # Atualizar estatísticas
        self._update_thought_stats(normalized_type)
        
        # Determinar a qual passo este pensamento pertence
        step_number = self.current_step
        
        # Se não temos um passo atual, usar o último passo conhecido
        if step_number is None:
            if self.last_step_number > 0:
                step_number = self.last_step_number
            else:
                # Inicializar passo 1 implicitamente
                self._create_implicit_step(1)
                step_number = 1
        
        # Criar pensamento
        timestamp = datetime.now().isoformat()
        thought = {
            "type": normalized_type,
            "original_type": thought_type,
            "content": content,
            "timestamp": timestamp,
            "raw_message": raw_message
        }
        
        # Verificar se o passo existe na timeline
        step_exists = False
        for step in self.timeline:
            if step.get("step_number") == step_number:
                step_exists = True
                
                # Verificar se é duplicado para evitar pensamentos repetidos
                for existing_thought in step.get("thoughts", []):
                    # Calcular similaridade - pensamentos quase idênticos são ignorados
                    if existing_thought.get("content") == content or existing_thought.get("raw_message") == raw_message:
                        logger.debug(f"Pensamento duplicado ignorado: {content[:30]}...")
                        return
                
                # Adicionar pensamento ao passo
                step["thoughts"].append(thought)
                
                # Adicionar ao dicionário por categoria
                if normalized_type not in step["thoughts_by_category"]:
                    step["thoughts_by_category"][normalized_type] = []
                step["thoughts_by_category"][normalized_type].append(content)
                
                # Incrementar contador de processados
                self.total_thoughts_processed += 1
                break
        
        # Se o passo não existe na timeline (situação excepcional), criar
        if not step_exists:
            # Criar passo implícito
            self._create_implicit_step(step_number)
            
            # Adicionar pensamento ao novo passo
            for step in self.timeline:
                if step.get("step_number") == step_number:
                    # Adicionar pensamento
                    step["thoughts"].append(thought)
                    
                    # Adicionar ao dicionário por categoria
                    if normalized_type not in step["thoughts_by_category"]:
                        step["thoughts_by_category"][normalized_type] = []
                    step["thoughts_by_category"][normalized_type].append(content)
                    
                    # Incrementar contador
                    self.total_thoughts_processed += 1
                    break
        
        # Adicionar ao dicionário de pensamentos por passo
        if step_number not in self.thoughts_by_step:
            self.thoughts_by_step[step_number] = []
        self.thoughts_by_step[step_number].append({
            "step": step_number,
            "category": normalized_type,
            "texto": content,
            "timestamp": timestamp
        })
        
        # Registrar na timeline se disponível
        if hasattr(self, 'timeline_builder'):
            try:
                self.timeline_builder.add_thought(
                    step_number=step_number,
                    thought_type=normalized_type,
                    content=content,
                    timestamp=timestamp
                )
            except Exception as e:
                logger.error(f"Erro ao adicionar pensamento na timeline: {e}")
        
        # Se temos um callback de pensamento registrado, chamar
        if self.callback_pensamento:
            # Criar objeto de pensamento
            pensamento_obj = {
                "passo": step_number,
                "tipo": normalized_type,
                "tipo_original": thought_type,
                "texto": content,
                "timestamp": timestamp,
                "mensagem_completa": raw_message,
                "pensamentos_por_categoria": {}
            }
            
            # Adicionar todos os pensamentos do passo atual
            for step in self.timeline:
                if step.get("step_number") == step_number:
                    pensamento_obj["pensamentos_por_categoria"] = step.get("thoughts_by_category", {})
                    pensamento_obj["todos_pensamentos"] = step.get("thoughts", [])
                    break
            
            # Chamar callback
            try:
                self.callback_pensamento(pensamento_obj)
            except Exception as e:
                logger.error(f"Erro ao invocar callback_pensamento: {e}")
    
    def _normalize_thought_type(self, thought_type):
        """
        Normaliza o tipo de pensamento para categorias padrão.
        
        Args:
            thought_type (str): Tipo original do pensamento
            
        Returns:
            str: Tipo normalizado (evaluation, memory, next_goal, thought)
        """
        # Mapping para tipos normalizados
        normalized_types = {
            "evaluation": ["eval", "evaluation", "avaliação", "avaliacao", "assessment"],
            "memory": ["memory", "memória", "memoria", "remembered"],
            "next_goal": ["next_goal", "goal", "next", "objetivo", "próximo", "proximo"],
            "thought": ["thought", "thinking", "pensamento", "reasoning", "raciocínio", "raciocinio"]
        }
        
        # Verificar qual categoria normalizada corresponde ao tipo
        thought_type_lower = thought_type.lower()
        for normalized, variants in normalized_types.items():
            if any(variant in thought_type_lower for variant in variants):
                return normalized
                
        # Se não corresponder a nenhuma categoria conhecida, retornar "thought"
        return "thought"
    
    def _update_thought_stats(self, category):
        """
        Atualiza estatísticas de pensamentos.
        
        Args:
            category (str): Categoria de pensamento
        """
        # Garantir que categoria existe nas estatísticas
        if category not in self.thought_stats:
            self.thought_stats[category] = 0
            
        # Incrementar contador
        self.thought_stats[category] += 1
            
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

    def save_timeline(self, filepath):
        """
        Salva a timeline em um arquivo JSON.
        
        Args:
            filepath (str): Caminho do arquivo onde a timeline será salva
            
        Returns:
            str: Caminho do arquivo salvo
        """
        if hasattr(self, 'timeline_builder') and self.timeline_builder:
            return self.timeline_builder.save_timeline(filepath)
        else:
            logger.error("Não foi possível salvar a timeline: timeline_builder não disponível")
            return None
     
    def get_timeline(self):
        """
        Retorna a timeline completa.
        
        Returns:
            dict: Dados completos da timeline
        """
        if hasattr(self, 'timeline_builder') and self.timeline_builder:
            return self.timeline_builder.get_timeline()
        else:
            logger.warning("Não foi possível obter a timeline: timeline_builder não disponível")
            return {"events": [], "total_steps": 0, "total_thoughts": 0}

    def get_unknown_messages(self):
        """
        Retorna a lista de mensagens não categorizadas capturadas durante o rastreamento.
        
        Returns:
            List[Dict]: Lista de mensagens desconhecidas com seus timestamps
        """
        if hasattr(self, 'unknown_messages'):
            return self.unknown_messages
        else:
            return []

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
            category (str): Categoria de pensamento
        """
        # Garantir que categoria existe nas estatísticas
        if category not in self.thought_stats:
            self.thought_stats[category] = 0
            
        # Incrementar contador
        self.thought_stats[category] += 1
            
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

    def _process_llm_data(self, pattern_name, match, message):
        """
        Processa dados relacionados ao LLM capturados nos logs.
        
        Args:
            pattern_name (str): Nome do padrão que identificou os dados de LLM
            match (re.Match): Objeto match com os grupos capturados
            message (str): Mensagem completa do log
        """
        try:
            # Determinar o tipo de evento LLM
            event_type = pattern_name
            
            # Extrair dados com base no tipo de padrão
            if pattern_name == "llm_request" or pattern_name == "llm_request_alt":
                # Capturar dados de requisição
                if pattern_name == "llm_request":
                    # Formato: "LLM Request: model=XXX, prompt=YYY, tokens=ZZZ"
                    model = match.group(1).strip()
                    prompt_summary = match.group(2).strip()
                    prompt_tokens = int(match.group(3))
                else:
                    # Formato alternativo: "Sending request to XXX with YYY tokens"
                    model = match.group(1).strip()
                    prompt_tokens = int(match.group(2))
                    prompt_summary = "N/A"
                
                # Registrar no tracking atual
                self.llm_tracking["current_model"] = model
                self.llm_tracking["current_prompt_tokens"] = prompt_tokens
                self.llm_tracking["current_step"] = self.current_step
                
                # Criar evento
                event_data = {
                    "model": model,
                    "prompt": prompt_summary[:100] + "..." if len(prompt_summary) > 100 else prompt_summary,
                    "prompt_tokens": prompt_tokens,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Registrar na timeline se disponível
                if hasattr(self, 'timeline_builder') and self.current_step:
                    self.timeline_builder.add_llm_event(
                        step_number=self.current_step or 0,
                        event_type="llm_request",
                        data=event_data
                    )
                    
                # Atualizar estatísticas
                self.llm_stats["total_calls"] += 1
                self.llm_stats["total_tokens"] += prompt_tokens
                
                # Registrar no modelo específico
                if model not in self.llm_stats["models"]:
                    self.llm_stats["models"][model] = {
                        "calls": 0,
                        "total_prompt_tokens": 0,
                        "total_completion_tokens": 0,
                        "total_cost": 0.0
                    }
                    
                self.llm_stats["models"][model]["calls"] += 1
                self.llm_stats["models"][model]["total_prompt_tokens"] += prompt_tokens
                
            elif pattern_name == "llm_response" or pattern_name == "llm_response_alt":
                # Capturar dados de resposta
                if pattern_name == "llm_response":
                    # Formato: "LLM Response: model=XXX, response=YYY, tokens=ZZZ"
                    model = match.group(1).strip()
                    response_summary = match.group(2).strip()
                    completion_tokens = int(match.group(3))
                else:
                    # Formato alternativo: "Received response from XXX with YYY tokens"
                    model = match.group(1).strip()
                    completion_tokens = int(match.group(2))
                    response_summary = "N/A"
                
                # Registrar no tracking atual
                self.llm_tracking["current_completion_tokens"] = completion_tokens
                
                # Criar evento
                event_data = {
                    "model": model,
                    "response": response_summary[:100] + "..." if len(response_summary) > 100 else response_summary,
                    "completion_tokens": completion_tokens,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Registrar na timeline se disponível
                if hasattr(self, 'timeline_builder'):
                    self.timeline_builder.add_llm_event(
                        step_number=self.current_step or self.llm_tracking.get("current_step", 0),
                        event_type="llm_response",
                        data=event_data
                    )
                    
                # Atualizar estatísticas
                self.llm_stats["total_tokens"] += completion_tokens
                
                # Registrar no modelo específico
                if model not in self.llm_stats["models"]:
                    self.llm_stats["models"][model] = {
                        "calls": 0,
                        "total_prompt_tokens": 0,
                        "total_completion_tokens": 0,
                        "total_cost": 0.0
                    }
                    
                self.llm_stats["models"][model]["total_completion_tokens"] += completion_tokens
                
            elif pattern_name == "llm_cost" or pattern_name == "llm_cost_alt":
                # Capturar dados de custo
                cost = float(match.group(1))
                
                # Registrar no tracking atual
                self.llm_tracking["current_cost"] = cost
                
                # Criar evento
                event_data = {
                    "cost": cost,
                    "model": self.llm_tracking.get("current_model", "unknown"),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Registrar na timeline se disponível
                if hasattr(self, 'timeline_builder'):
                    self.timeline_builder.add_llm_event(
                        step_number=self.current_step or self.llm_tracking.get("current_step", 0),
                        event_type="llm_cost",
                        data=event_data
                    )
                    
                # Atualizar estatísticas
                self.llm_stats["estimated_cost"] += cost
                
                # Registrar no modelo específico se disponível
                model = self.llm_tracking.get("current_model")
                if model and model in self.llm_stats["models"]:
                    self.llm_stats["models"][model]["total_cost"] += cost
                
            # Adicionar ao passo atual se existir
            if self.current_step:
                # Encontrar o passo na timeline
                for step in self.timeline:
                    if step.get("step_number") == self.current_step:
                        # Garantir que a lista de eventos LLM existe
                        if "llm_events" not in step:
                            step["llm_events"] = []
                            
                        # Adicionar evento
                        step["llm_events"].append({
                            "type": event_type,
                            "timestamp": datetime.now().isoformat(),
                            "data": match.groups()
                        })
                        break
            
            logger.debug(f"Dados de LLM processados: {pattern_name}")
            
        except Exception as e:
            logger.error(f"Erro ao processar dados de LLM ({pattern_name}): {e}")
            
    async def finish_tracking(self):
        """
        Finaliza o processo de rastreamento, salvando dados pendentes e limpando recursos.
        
        Este método deve ser chamado antes de desinstalar o interceptador para garantir que
        todos os dados sejam salvos adequadamente.
        
        Returns:
            Dict[str, Any]: Resumo dos dados capturados durante o tracking
        """
        if not self.tracking_enabled:
            logger.warning("O tracking já estava desativado.")
            return {}
            
        logger.info("Finalizando tracking de logs do browser-use...")
        
        try:
            # Salvar mensagens desconhecidas uma última vez
            if hasattr(self, 'unknown_messages') and self.unknown_messages and hasattr(self, 'unknown_messages_file'):
                try:
                    with open(self.unknown_messages_file, 'w', encoding='utf-8') as f:
                        json.dump(self.unknown_messages, f, indent=2, ensure_ascii=False)
                    logger.debug(f"Mensagens desconhecidas salvas em {self.unknown_messages_file} (final)")
                except Exception as e:
                    logger.error(f"Erro ao salvar mensagens desconhecidas (final): {e}")
            
            # Cancelar tarefa de salvamento periódico
            if hasattr(self, '_save_unknown_messages_task'):
                self._save_unknown_messages_task.cancel()
                try:
                    # Aguardar a tarefa ser cancelada
                    await asyncio.wait_for(asyncio.shield(self._save_unknown_messages_task), timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass  # Esperado quando a tarefa é cancelada
            
            # Finalizar timeline
            if hasattr(self, 'timeline_builder'):
                self.timeline_builder.stop_timer()
                
                # Registrar evento de encerramento na timeline
                self.timeline_builder.add_event(
                    title="Interceptador Desativado",
                    description="Fim do tracking de logs do browser-use",
                    icon="⏹️",
                    timestamp=datetime.now().isoformat()
                )
                
                # Salvar timeline se temos diretório de log
                if self.log_dir:
                    timeline_file = os.path.join(self.log_dir, "timeline.json")
                    try:
                        with open(timeline_file, 'w', encoding='utf-8') as f:
                            json.dump({
                                "title": self.timeline_builder.title,
                                "start_time": self.start_time.isoformat(),
                                "end_time": datetime.now().isoformat(),
                                "events": self.timeline_builder.events,
                                "total_steps": len([e for e in self.timeline_builder.events if "step_number" in e.get("metadata", {})]),
                                "total_thoughts": self.total_thoughts_processed
                            }, f, indent=2, ensure_ascii=False)
                        logger.info(f"Timeline salva em {timeline_file}")
                    except Exception as e:
                        logger.error(f"Erro ao salvar timeline: {e}")
            
            # Calcular duração do tracking
            duration = (datetime.now() - self.start_time).total_seconds()
            
            # Marcar tracking como desativado
            self.tracking_enabled = False
            
            # Gerar resumo dos dados capturados
            summary = {
                "duration_seconds": duration,
                "total_thoughts": self.total_thoughts_processed,
                "thought_stats": self.thought_stats,
                "total_steps": len(self.timeline),
                "llm_stats": self.llm_stats,
                "unknown_messages_count": len(self.unknown_messages) if hasattr(self, 'unknown_messages') else 0
            }
            
            # Salvar resumo se temos diretório de log
            if self.log_dir:
                summary_file = os.path.join(self.log_dir, "tracking_summary.json")
                try:
                    with open(summary_file, 'w', encoding='utf-8') as f:
                        json.dump(summary, f, indent=2, ensure_ascii=False)
                    logger.info(f"Resumo do tracking salvo em {summary_file}")
                except Exception as e:
                    logger.error(f"Erro ao salvar resumo: {e}")
            
            # Salvar também os pensamentos capturados
            if self.log_dir:
                thoughts_file = os.path.join(self.log_dir, "thinking_logs.json")
                try:
                    # Extrair pensamentos de todos os passos
                    all_thoughts = []
                    for step in self.timeline:
                        step_thoughts = []
                        for thought in step.get("thoughts", []):
                            step_thoughts.append({
                                "step": step.get("step_number"),
                                "type": thought.get("type"),
                                "content": thought.get("content"),
                                "timestamp": thought.get("timestamp")
                            })
                        all_thoughts.extend(step_thoughts)
                    
                    with open(thoughts_file, 'w', encoding='utf-8') as f:
                        json.dump(all_thoughts, f, indent=2, ensure_ascii=False)
                    logger.info(f"Pensamentos salvos em {thoughts_file}")
                except Exception as e:
                    logger.error(f"Erro ao salvar pensamentos: {e}")
            
            logger.info(f"Tracking finalizado após {duration:.1f} segundos")
            logger.info(f"Total de pensamentos: {self.total_thoughts_processed}")
            logger.info(f"Total de passos: {len(self.timeline)}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Erro ao finalizar tracking: {e}")
            logger.error(traceback.format_exc())
            self.tracking_enabled = False
            return {
                "error": str(e),
                "total_thoughts": self.total_thoughts_processed,
                "total_steps": len(self.timeline)
            }

    def desinstalar(self):
        """
        Remove o interceptador do sistema de logging e limpa recursos.
        
        Este método deve ser chamado para encerrar o interceptador após o uso.
        Recomenda-se chamar finish_tracking() antes deste método para garantir
        que todos os dados sejam salvos corretamente.
        
        Returns:
            bool: True se o interceptador foi desinstalado com sucesso
        """
        try:
            # Desativar tracking
            self.tracking_enabled = False
            
            # Registrar evento de encerramento na timeline se disponível
            if hasattr(self, 'timeline_builder'):
                try:
                    self.timeline_builder.add_event(
                        title="Interceptador Desinstalado",
                        description="Interceptador de logs removido do sistema",
                        icon="🛑",
                        timestamp=datetime.now().isoformat()
                    )
                except Exception as e:
                    logger.error(f"Erro ao registrar evento de desinstalação: {e}")
            
            # Remover o handler do logger raiz
            root_logger = logging.getLogger()
            if self in root_logger.handlers:
                root_logger.removeHandler(self)
                
            # Cancelar tarefas pendentes
            for task in self._pending_tasks:
                if not task.done():
                    task.cancel()
            
            # Cancelar a tarefa de salvamento periódico se estiver ativa
            if hasattr(self, '_save_unknown_messages_task') and self._save_unknown_messages_task and not self._save_unknown_messages_task.done():
                try:
                    self._save_unknown_messages_task.cancel()
                except Exception as e:
                    logger.error(f"Erro ao cancelar tarefa de salvamento: {e}")
            
            logger.info("Interceptador de logs desinstalado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao desinstalar interceptador: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def get_thoughts_summary(self):
        """
        Gera um resumo estatístico dos pensamentos capturados.
        
        Returns:
            Dict[str, Any]: Resumo estatístico dos pensamentos
        """
        # Copiar estatísticas atuais
        stats = {
            "total_thoughts": sum(self.thought_stats.values()),
            "categories": {k: v for k, v in self.thought_stats.items() if k != "unknown"},
            "unknown": self.thought_stats.get("unknown", 0)
        }
        
        # Se temos timeline, adicionar pensamentos por passo
        if self.timeline:
            thoughts_by_step = {}
            for step in self.timeline:
                step_number = step.get("step_number")
                step_thoughts = step.get("thoughts", [])
                thoughts_by_step[step_number] = len(step_thoughts)
            
            stats["step_count"] = len(self.timeline)
            stats["thoughts_by_step"] = thoughts_by_step
            
            # Adicionar estatísticas de ações se disponíveis
            action_stats = self._get_action_stats()
            if action_stats:
                stats["actions"] = action_stats
        
        # Adicionar estatísticas sobre o processamento
        if hasattr(self, 'total_thoughts_detected') and hasattr(self, 'total_thoughts_processed'):
            stats["processing_stats"] = {
                "detected": self.total_thoughts_detected,
                "processed": self.total_thoughts_processed,
                "processing_rate": round((self.total_thoughts_processed / self.total_thoughts_detected) * 100, 2) if self.total_thoughts_detected > 0 else 0
            }
        
        return stats
    
    def _get_action_stats(self):
        """
        Gera estatísticas sobre as ações detectadas.
        
        Returns:
            Dict[str, Any]: Estatísticas de ações por tipo
        """
        # Inicializar contadores
        action_counts = {}
        total_actions = 0
        
        # Contar ações por tipo em cada passo
        for step in self.timeline:
            actions = step.get("actions", [])
            for action in actions:
                action_type = action.get("type", "unknown")
                if action_type not in action_counts:
                    action_counts[action_type] = 0
                action_counts[action_type] += 1
                total_actions += 1
        
        # Se não há ações, retornar None
        if not total_actions:
            return None
            
        # Calcular distribuição percentual
        distribution = {}
        for action_type, count in action_counts.items():
            distribution[action_type] = round((count / total_actions) * 100, 2)
        
        # Agrupar ações por passo
        actions_by_step = {}
        for step in self.timeline:
            step_number = step.get("step_number")
            actions = step.get("actions", [])
            if actions:
                actions_by_step[step_number] = len(actions)
        
        return {
            "total_actions": total_actions,
            "action_counts": action_counts,
            "distribution": distribution,
            "actions_by_step": actions_by_step,
            "actions_per_step": round(total_actions / len(self.timeline), 2) if self.timeline else 0
        }
    
    def _update_thought_stats(self, thought_type):
        """
        Atualiza as estatísticas de pensamentos por categoria.
        
        Args:
            thought_type (str): O tipo normalizado de pensamento
        """
        # Garantir que categoria existe nas estatísticas
        if thought_type not in self.thought_stats:
            self.thought_stats[thought_type] = 0
            
        # Incrementar contador
        self.thought_stats[thought_type] += 1
    
    def _process_action(self, pattern_name, content, message, explicit_type=None):
        """
        Processa ações detectadas nas mensagens de log.
        
        Args:
            pattern_name (str): Nome do padrão que identificou a ação
            content (str): Conteúdo da ação (possivelmente em formato JSON)
            message (str): Mensagem completa do log
            explicit_type (str, optional): Tipo explícito da ação, se capturado no pattern
        """
        try:
            # Determinar o tipo de ação com base no pattern_name ou explicit_type
            if explicit_type:
                # Usar o tipo explícito fornecido pelo padrão action_json_with_type
                action_type = explicit_type
                # Tentar parsear como JSON
                try:
                    action_data = json.loads(content)
                except json.JSONDecodeError:
                    action_data = {"text": content}
                    if self.debug_mode:
                        logger.warning(f"Falha ao parsear ação como JSON apesar do tipo explícito '{explicit_type}': {content}")
            elif pattern_name == "action" or pattern_name == "action_result":
                # Ação em formato texto simples
                action_type = "generic"
                action_data = {"text": content}
            else:
                # Tentar parsear como JSON
                try:
                    action_data = json.loads(content)
                    
                    # Determinar o tipo de ação baseado no pattern ou no conteúdo
                    if pattern_name == "navigation_action":
                        action_type = "navigation"
                    elif pattern_name == "click_action":
                        action_type = "click"
                    elif pattern_name == "extraction_action":
                        action_type = "extraction"
                    elif pattern_name == "form_action":
                        action_type = "form"
                    elif "type" in action_data:
                        # Usar o tipo definido no próprio JSON
                        action_type = action_data["type"]
                    else:
                        # Inferir o tipo baseado nas chaves presentes
                        if "url" in action_data:
                            action_type = "navigation"
                        elif "selector" in action_data or "element" in action_data:
                            action_type = "click"
                        elif "extract" in action_data or "data" in action_data:
                            action_type = "extraction"
                        elif "form" in action_data or "inputs" in action_data:
                            action_type = "form"
                        else:
                            action_type = "unknown"
                except json.JSONDecodeError:
                    # Não é JSON válido, tratar como texto
                    action_type = "text"
                    action_data = {"text": content}
                    if self.debug_mode:
                        logger.warning(f"Falha ao parsear ação como JSON: {content}")
                        
            # Registrar a ação no passo atual
            if self.current_step:
                # Encontrar o passo atual na timeline
                for step in self.timeline:
                    if step.get("step_number") == self.current_step:
                        # Garantir que a lista de ações existe
                        if "actions" not in step:
                            step["actions"] = []
                        
                        # Adicionar ação
                        step["actions"].append({
                            "type": action_type,
                            "data": action_data,
                            "timestamp": datetime.now().isoformat(),
                            "raw_message": message
                        })
                        
                        # Registrar na timeline, se disponível
                        if hasattr(self, 'timeline_builder'):
                            # Determinar ícone com base no tipo de ação
                            icon = "🔍"  # Ícone padrão para ação genérica
                            if action_type == "navigation":
                                icon = "🌐"
                            elif action_type == "click":
                                icon = "👆"
                            elif action_type == "extraction":
                                icon = "📊"
                            elif action_type == "form":
                                icon = "📝"
                            
                            # Preparar descrição compacta da ação
                            description = self._create_action_description(action_type, action_data)
                            
                            # Adicionar à timeline
                            self.timeline_builder.add_event(
                                title=f"Ação: {action_type.capitalize()}",
                                description=description,
                                icon=icon,
                                metadata={
                                    "step_number": self.current_step,
                                    "action_type": action_type,
                                    "action_data": action_data
                                }
                            )
                        
                        logger.debug(f"Ação do tipo {action_type} adicionada ao passo {self.current_step}")
                        break
            
            # Se não houver passo atual, registrar como desconhecido para análise posterior
            else:
                if hasattr(self, 'unknown_messages'):
                    self.unknown_messages.append({
                        "message": message,
                        "action_content": content,
                        "action_type": action_type,
                        "timestamp": datetime.now().isoformat(),
                        "reason": "Nenhum passo atual definido para associar a ação"
                    })
                logger.warning(f"Ação detectada mas nenhum passo atual: {action_type}")
                
        except Exception as e:
            logger.error(f"Erro ao processar ação ({pattern_name}): {e}")
            if hasattr(self, 'unknown_messages'):
                self.unknown_messages.append({
                    "message": message,
                    "action_content": content,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "reason": "Erro ao processar ação"
                })
    
    def _create_action_description(self, action_type, action_data):
        """
        Cria uma descrição legível para uma ação com base em seu tipo e dados.
        
        Args:
            action_type (str): Tipo da ação
            action_data (dict): Dados da ação
            
        Returns:
            str: Descrição formatada da ação
        """
        if action_type == "navigation":
            if "url" in action_data:
                return f"Navegação para: {action_data['url']}"
            else:
                return "Navegação (URL não especificada)"
                
        elif action_type == "click":
            if "selector" in action_data:
                return f"Clique em: {action_data['selector']}"
            elif "element" in action_data:
                return f"Clique em: {action_data['element']}"
            else:
                return "Clique (elemento não especificado)"
                
        elif action_type == "extraction":
            if "selector" in action_data:
                return f"Extração de dados do elemento: {action_data['selector']}"
            elif "data" in action_data:
                data_keys = list(action_data["data"].keys()) if isinstance(action_data["data"], dict) else []
                if data_keys:
                    return f"Extração de dados: {', '.join(data_keys[:3])}" + ("..." if len(data_keys) > 3 else "")
                else:
                    return "Extração de dados"
            else:
                return "Extração de dados"
                
        elif action_type == "form":
            if "form" in action_data and "selector" in action_data["form"]:
                return f"Preenchimento de formulário: {action_data['form']['selector']}"
            elif "inputs" in action_data:
                input_count = len(action_data["inputs"]) if isinstance(action_data["inputs"], list) else 0
                return f"Preenchimento de formulário com {input_count} campo(s)"
            else:
                return "Preenchimento de formulário"
                
        elif action_type == "text" or action_type == "generic":
            if "text" in action_data:
                text = action_data["text"]
                # Limitar o tamanho do texto para a descrição
                if len(text) > 50:
                    return text[:47] + "..."
                else:
                    return text
            else:
                return "Ação genérica"
                
        else:
            # Para outros tipos de ações, mostrar as primeiras chaves disponíveis
            if isinstance(action_data, dict):
                keys = list(action_data.keys())
                if keys:
                    key_values = []
                    for key in keys[:3]:  # Mostrar no máximo 3 chaves
                        value = action_data[key]
                        if isinstance(value, (str, int, float, bool)):
                            # Limitar o tamanho do valor
                            str_value = str(value)
                            if len(str_value) > 20:
                                str_value = str_value[:17] + "..."
                            key_values.append(f"{key}: {str_value}")
                    
                    return f"Ação {action_type}: {', '.join(key_values)}" + ("..." if len(keys) > 3 else "")
            
            return f"Ação {action_type}"

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