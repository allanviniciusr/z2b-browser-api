#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import json
import base64
import os
import sys
import time
import traceback
from datetime import datetime
from dotenv import load_dotenv

# Configuração de logging mais detalhada
logging.basicConfig(
    level=logging.DEBUG,  # Aumentamos para DEBUG para capturar mais informações
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("debug_agent_tracker.log")
    ]
)
logger = logging.getLogger('debug_agent_tracker')

# Carregar variáveis de ambiente
load_dotenv()

# Verificar ambiente Python
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Environment variables loaded: {os.environ.get('OPENAI_API_KEY') is not None}")

try:
    # Importar dependências necessárias
    from src.agent.agent import Agent
    from agent_tracker import AgentTracker
    
    logger.info("Importações realizadas com sucesso")
except ImportError as e:
    logger.error(f"Erro ao importar dependências: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

class DebugCallback:
    """Callback adicional para debug que intercepta todos os eventos"""
    
    def __init__(self):
        self.events = []
        self.error = None
    
    async def __call__(self, event_data):
        """Processa eventos e registra para análise"""
        event_type = event_data.get("event_type", "unknown")
        
        # Registrar evento
        logger.debug(f"EVENTO INTERCEPTADO: {event_type}")
        logger.debug(f"CONTEÚDO: {json.dumps(event_data, default=str)[:500]}...")
        
        # Armazenar evento para análise
        self.events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": event_data
        })
        
        # Se for erro, registrar separadamente
        if event_type == "task.error" or "error" in event_data:
            self.error = event_data.get("error", "Erro não especificado")
            logger.error(f"ERRO DETECTADO: {self.error}")
        
        # Retornar evento sem modificações
        return event_data

async def debug_browser_state(agent):
    """Tenta acessar e imprimir informações sobre o estado do navegador"""
    try:
        if hasattr(agent, "browser_context") and agent.browser_context:
            logger.info("Tentando acessar estado do navegador...")
            
            # Verifica se há método get_state
            if hasattr(agent.browser_context, "get_state"):
                state = await agent.browser_context.get_state()
                if state:
                    logger.info(f"Estado do navegador: URL={state.url}, Title={state.title}")
                    logger.info(f"Screenshot presente: {state.screenshot is not None}")
                else:
                    logger.info("Estado do navegador é None")
            else:
                logger.info("Método get_state não encontrado no browser_context")
                
            # Verifica páginas abertas
            pages = await agent.browser_context.pages()
            logger.info(f"Número de páginas abertas: {len(pages)}")
            for i, page in enumerate(pages):
                logger.info(f"Página {i}: URL={await page.url()}, Title={await page.title()}")
        else:
            logger.info("Agente não tem browser_context ou é None")
    except Exception as e:
        logger.error(f"Erro ao acessar estado do navegador: {e}")
        logger.error(traceback.format_exc())

async def diagnose_agent_execution(prompt):
    """
    Executa o agente com diagnóstico detalhado, capturando todo o fluxo
    """
    logger.info("Iniciando diagnóstico de execução do agente...")
    timeout_seconds = 180  # Aumentando para 3 minutos para dar mais tempo ao agente
    agent = None
    tracker = None
    
    try:
        logger.info(f"Criando tracker para execução com prompt: '{prompt}'")
        tracker = AgentTracker()
        tracker.set_prompt(prompt)
        
        logger.info("Inicializando agente com logging básico")
        agent = Agent(prompt=prompt)
        
        logger.info(f"Executando agente com timeout de {timeout_seconds} segundos")
        result = await asyncio.wait_for(
            tracker.track_execution(agent, prompt), 
            timeout=timeout_seconds
        )
        
        logger.info(f"Execução concluída com sucesso: {result}")
        return {
            "status": "sucesso",
            "resultado": result,
            "log_dir": tracker.log_dir,
            "relatorio_html": os.path.join(tracker.log_dir, "relatorio.html")
        }
    except Exception as e:
        logger.error(f"Erro durante diagnóstico: {e}")
        logger.error(traceback.format_exc())
        print(f"\nERRO DURANTE DIAGNÓSTICO: {e}")
        print(f"Detalhes completos no arquivo de log: debug_agent_tracker.log")
    
    finally:
        # Forçar marcação da conclusão no tracker se não estiver feito
        try:
            if 'tracker' in locals() and tracker:
                logger.info("Garantindo que o tracker seja marcado como concluído...")
                tracker.force_complete(result="Execução interrompida" if 'result' not in locals() else result)
        except Exception as te:
            logger.error(f"Erro ao finalizar tracker: {te}")
            
        # Tentar limpar recursos
        try:
            if 'agent' in locals():
                logger.info("Tentando fazer cleanup do agente...")
                try:
                    await asyncio.wait_for(agent.cleanup(), timeout=10)
                    logger.info("Cleanup do agente concluído com sucesso")
                except Exception as ce:
                    logger.error(f"Erro durante cleanup: {ce}")
        except Exception as e:
            logger.error(f"Erro na finalização: {e}")
    
    print("\nDiagnóstico concluído. Verifique o arquivo de log para detalhes.")
    return "Diagnóstico concluído"

async def main():
    """Função principal que inicia o diagnóstico"""
    try:
        # Prompt simples para teste
        prompt = "Abra o google e mostre a página inicial"
        
        print("\n" + "="*80)
        print("DIAGNÓSTICO DO AGENTTRACKER")
        print("="*80 + "\n")
        
        logger.info(f"Iniciando diagnóstico com prompt: '{prompt}'")
        
        # Executar diagnóstico
        resultado = await diagnose_agent_execution(prompt)
        
        if isinstance(resultado, dict):
            # Exibir resultados em formato de dicionário
            print("\n" + "-"*50)
            print("RESULTADO DO DIAGNÓSTICO:")
            print("-"*50)
            print(f"Status: {resultado.get('status', 'N/A')}")
            print(f"Resultado: {resultado.get('resultado', 'N/A')}")
            print(f"Logs salvos em: {resultado.get('log_dir', 'N/A')}")
            print(f"Relatório HTML: {resultado.get('relatorio_html', 'N/A')}")
            
            # Verificar estrutura de arquivos gerada
            print("\nArquivos gerados:")
            log_dir = resultado.get('log_dir')
            if log_dir and os.path.exists(log_dir):
                for root, dirs, files in os.walk(log_dir):
                    level = root.replace(log_dir, '').count(os.sep)
                    indent = ' ' * 4 * level
                    print(f"{indent}{os.path.basename(root)}/")
                    sub_indent = ' ' * 4 * (level + 1)
                    for f in files:
                        file_path = os.path.join(root, f)
                        size = os.path.getsize(file_path)
                        print(f"{sub_indent}{f} ({size} bytes)")
            else:
                print("Diretório de logs não encontrado ou não acessível")
        else:
            # Exibir resultado como string simples
            print("\n" + "-"*50)
            print("RESULTADO DO DIAGNÓSTICO (texto):")
            print("-"*50)
            print(resultado)
        
    except Exception as e:
        logger.error(f"Erro no diagnóstico: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    # Executar o diagnóstico
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Erro fatal: {e}")
        logger.critical(traceback.format_exc())
        print(f"ERRO FATAL: {e}")
        sys.exit(1) 