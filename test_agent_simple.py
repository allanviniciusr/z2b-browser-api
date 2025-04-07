#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
from dotenv import load_dotenv

# Configurar logging básico
logging.basicConfig(level=logging.INFO)

# Carregar variáveis de ambiente
load_dotenv()

# Importar a classe Agent do arquivo certo
from src.agent.agent import Agent
from agent_tracker import AgentTracker, track_agent_execution

async def main():
    # Prompt básico para buscar o preço do Bitcoin
    prompt = "Abra o google e digite 'Preço do bitcoin hoje', e retorne o preço atual do bitcoin."
    
    # Criar um agente
    agent = Agent(prompt=prompt)
    
    # Criar diretório para o teste
    log_dir = os.path.join("agent_logs", "browser_test")
    os.makedirs(log_dir, exist_ok=True)
    
    print("Executando prompt com AgentTracker...")
    
    # Método 1: Usando o utilitário track_agent_execution
    result, tracker = await track_agent_execution(
        agent, 
        prompt, 
        log_dir=log_dir,
        include_screenshots=True,
        auto_summarize=True,
        compression_level=5
    )
    
    # Método 2: Alternativa usando diretamente o AgentTracker (comentado)
    """
    # Criar um tracker
    tracker = AgentTracker(
        log_dir=log_dir,
        include_screenshots=True,
        auto_summarize=True,
        compression_level=5
    )
    
    # Definir o prompt no tracker
    tracker.set_prompt(prompt)
    
    # Executar com o tracker
    result = await tracker.track_execution(agent, prompt)
    """
    
    # Mostrar resultado
    print("\nResultado da tarefa:")
    print(result)
    
    # Mostrar informações do tracker
    print("\nResumo da execução:")
    resumo = tracker.get_resumo_execucao()
    print(f"Total de eventos: {resumo['total_eventos']}")
    print(f"Passos executados: {resumo['passos']}")
    print(f"Navegações: {resumo['navegacoes']}")
    print(f"Screenshots: {resumo['screenshots']}")
    print(f"Duração: {resumo['duracao_segundos']:.2f} segundos")
    print(f"Logs salvos em: {tracker.log_dir}")
    
    return result

if __name__ == "__main__":
    # Executar o teste
    asyncio.run(main()) 