#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('browser_tracker_test')

# Carregar variáveis de ambiente
load_dotenv()

# Importar as classes necessárias
from src.agent.agent import Agent
from agent_tracker import AgentTracker, track_agent_execution

async def test_browser_use_tracking():
    """Teste do rastreamento em tempo real do browser-use"""
    # Prompt de exemplo que explora várias funcionalidades
    prompt = "Navegue para o site do Google, pesquise por 'Preço do bitcoin hoje', " \
             "encontre o valor atual do bitcoin e me informe o resultado."
    
    print("\n" + "="*80)
    print(f"TESTE DE RASTREAMENTO DO BROWSER-USE EM TEMPO REAL\n")
    print(f"Prompt: '{prompt}'")
    print("="*80 + "\n")
    
    # Criar rastreador com logs na pasta agent_logs/browser_test
    tracker = AgentTracker(
        log_dir="agent_logs/browser_test_pensamentos",
        include_screenshots=True,
        auto_summarize=True
    )
    tracker.set_prompt(prompt)
    
    # Criar agente Z2B (que usa o browser-use internamente)
    # Definir a variável de ambiente para forçar o uso do Z2B
    os.environ["AGENT_IMPLEMENTATION"] = "z2b"
    agent = Agent(prompt=prompt)
    
    print("\nExecutando agente com rastreamento em tempo real...")
    start_time = datetime.now()
    
    # Executar o agente com o callback do tracker
    result = await agent.execute_prompt_task(prompt, callback=tracker.callback)
    
    end_time = datetime.now()
    
    # Mostrar resultados
    print(f"\nExecução concluída em {(end_time - start_time).total_seconds():.2f} segundos")
    print(f"Log JSON salvo em: {tracker.log_file}")
    print(f"Arquivo de pensamentos: {os.path.join(tracker.log_dir, 'thinking_logs.json')}")
    
    # Mostrar estatísticas do rastreamento
    with open(tracker.log_file, 'r', encoding='utf-8') as f:
        log_data = json.load(f)
        eventos = log_data.get('eventos', [])
        print(f"\nEventos registrados: {len(eventos)}")
        
        # Contagem por tipo de evento
        event_types = {}
        for evento in eventos:
            tipo = evento.get('tipo', 'unknown')
            event_types[tipo] = event_types.get(tipo, 0) + 1
        
        print("\nTipos de eventos registrados:")
        for tipo, count in event_types.items():
            print(f"  - {tipo}: {count}")
        
        # Verificar se capturamos steps do browser-use
        browser_use_steps = sum(1 for e in eventos if e.get('tipo') == 'browser_use.agent.step')
        if browser_use_steps > 0:
            print(f"\nCapturados {browser_use_steps} passos em tempo real do browser-use!")
            
            # Verificar se conseguimos extrair os pensamentos do LLM
            print("\nAnalisando logs de pensamento do agente LLM:")
            
            pensamentos_count = 0
            avaliacoes_count = 0
            memoria_count = 0
            objetivo_count = 0
            
            for e in eventos:
                if e.get('tipo') == 'browser_use.agent.step':
                    # Verificar campos de pensamento (no nível superior ou dentro de dados)
                    if 'thought' in e or ('dados' in e and 'thought' in e['dados']):
                        pensamentos_count += 1
                    
                    if 'evaluation' in e or ('dados' in e and 'evaluation' in e['dados']):
                        avaliacoes_count += 1
                    
                    if 'memory' in e or ('dados' in e and 'memory' in e['dados']):
                        memoria_count += 1
                    
                    if 'next_goal' in e or ('dados' in e and 'next_goal' in e['dados']):
                        objetivo_count += 1
            
            print(f"  ✓ Pensamentos capturados: {pensamentos_count} de {browser_use_steps}")
            print(f"  ✓ Avaliações capturadas: {avaliacoes_count} de {browser_use_steps}")
            print(f"  ✓ Memórias capturadas: {memoria_count} de {browser_use_steps}")
            print(f"  ✓ Objetivos capturados: {objetivo_count} de {browser_use_steps}")
            
            # Mostrar exemplo do primeiro pensamento capturado
            for e in eventos:
                if e.get('tipo') == 'browser_use.agent.step':
                    thought = e.get('thought') or e.get('dados', {}).get('thought')
                    evaluation = e.get('evaluation') or e.get('dados', {}).get('evaluation')
                    memory = e.get('memory') or e.get('dados', {}).get('memory')
                    next_goal = e.get('next_goal') or e.get('dados', {}).get('next_goal')
                    
                    if thought or evaluation or memory or next_goal:
                        print("\nExemplo de pensamento capturado (passo #{}):".format(
                            e.get('dados', {}).get('step', '?')))
                        if evaluation:
                            print(f"👍 Avaliação: {evaluation}")
                        if memory:
                            print(f"🧠 Memória: {memory}")
                        if next_goal:
                            print(f"🎯 Próximo objetivo: {next_goal}")
                        break
            
            # Mostrar algumas ações executadas
            print("\nAlgumas ações executadas pelo agente:")
            actions = []
            for e in eventos:
                if e.get('tipo') == 'browser_use.agent.step' and 'dados' in e and 'action' in e['dados']:
                    action = e['dados']['action']
                    if action and isinstance(action, dict):
                        action_type = list(action.keys())[0] if action.keys() else "unknown"
                        actions.append(action_type)
            
            # Mostrar até 5 ações
            for i, action in enumerate(actions[:5]):
                print(f"  {i+1}. {action}")
            
            if len(actions) > 5:
                print(f"  ... e mais {len(actions) - 5} ações")
        else:
            print("\nNenhum passo do browser-use foi capturado. Verifique se o callback está funcionando corretamente.")
    
    # Limpar o agente
    await agent.cleanup()
    
    # Verificar se foram gerados os arquivos adicionais
    thinking_logs_file = os.path.join(tracker.log_dir, "thinking_logs.json")
    if os.path.exists(thinking_logs_file):
        with open(thinking_logs_file, 'r', encoding='utf-8') as f:
            thinking_data = json.load(f)
            print(f"\nArquivo thinking_logs.json gerado com {len(thinking_data)} registros de pensamento!")
    
    # Executar script de verificação de logs para visualizar os pensamentos
    print("\nExecutando verificação detalhada dos logs de pensamento:")
    print("-" * 80)
    verificar_cmd = f"python verificar_logs.py {tracker.log_dir} --detalhado"
    print(f"Comando: {verificar_cmd}")
    print("-" * 80)
    print("\nPara verificar manualmente os logs de pensamento, execute:")
    print(f"python verificar_logs.py {tracker.log_dir} --detalhado")
    
    print("\n" + "="*80)
    print("TESTE CONCLUÍDO")
    print("="*80 + "\n")
    
    return "Teste de rastreamento concluído."

if __name__ == "__main__":
    # Executar teste
    asyncio.run(test_browser_use_tracking()) 