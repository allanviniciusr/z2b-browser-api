#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import json
import base64
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Configurar logging básico
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('agent_tracker_test')

# Carregar variáveis de ambiente
load_dotenv()

try:
    # Importar a classe Agent do arquivo certo
    from src.agent.agent import Agent
    from agent_tracker import AgentTracker, track_agent_execution
except ImportError as e:
    logger.error(f"Erro ao importar dependências: {e}")
    logger.info("Certifique-se que você está executando este script do diretório raiz do projeto.")
    exit(1)

# Diretório para salvar os registros
LOGS_DIR = "agent_logs"
os.makedirs(LOGS_DIR, exist_ok=True)

async def main():
    """Função principal que demonstra o uso do AgentTracker"""
    # Prompt de exemplo
    prompt = "Abra o google e digite 'Preço do bitcoin hoje', e retorne o preço atual do bitcoin."
    
    print("\n" + "="*80)
    print(f"TESTE DO AGENTTRACKER SIMPLIFICADO\n")
    print(f"Prompt: '{prompt}'")
    print("="*80 + "\n")
    
    # Uso direto do AgentTracker
    print("\n--- Teste único: Uso do AgentTracker Simplificado ---")
    try:
        # Criar rastreador
        tracker = AgentTracker()
        tracker.set_prompt(prompt)
        
        # Criar agente
        agent = Agent(prompt=prompt)
        
        # Executar o prompt com o callback do tracker
        print("Executando agente com rastreamento...")
        
        # Registrar tempo de início
        start_time = datetime.now()
        
        # Executar o agente com o callback do tracker
        result = await agent.execute_prompt_task(prompt, callback=tracker.callback)
        
        # Registrar tempo de fim
        end_time = datetime.now()
        
        # Mostrar resultados
        print(f"\nExecução concluída em {(end_time - start_time).total_seconds():.2f} segundos")
        print(f"Log JSON salvo em: {tracker.log_file}")
        
        # Mostrar resultado
        print("\nResultado da tarefa:")
        if isinstance(result, dict):
            result_str = json.dumps(result, indent=2, ensure_ascii=False)
            print(result_str[:200] + "..." if len(result_str) > 200 else result_str)
        else:
            print(str(result)[:200] + "..." if len(str(result)) > 200 else str(result))
        
        # Mostrar contagem de eventos
        with open(tracker.log_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
            print(f"\nEventos registrados: {len(log_data.get('eventos', []))}")
            
            # Mostrar tipos de eventos registrados
            event_types = {}
            for evento in log_data.get('eventos', []):
                tipo = evento.get('tipo', 'unknown')
                event_types[tipo] = event_types.get(tipo, 0) + 1
            
            print("\nTipos de eventos registrados:")
            for tipo, count in event_types.items():
                print(f"  - {tipo}: {count}")
        
    except Exception as e:
        print(f"\nErro durante execução: {str(e)}")
    
    print("\n" + "="*80)
    print("TESTE CONCLUÍDO")
    print("="*80 + "\n")
    
    return "Teste de rastreamento concluído."

if __name__ == "__main__":
    # Executar o teste
    asyncio.run(main()) 