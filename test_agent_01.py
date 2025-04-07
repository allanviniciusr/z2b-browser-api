#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Teste do agente para buscar preço do Bitcoin.

Este script testa a capacidade do agente de navegar na web, pesquisar no Google
e extrair o preço atual do Bitcoin.
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

# Configurar algumas variáveis de ambiente para o teste
os.environ["AGENT_IMPLEMENTATION"] = "legacy"  # Usar implementação legada por enquanto
os.environ["BROWSER_HEADLESS"] = "false"  # Mostrar o navegador durante o teste
os.environ["AGENT_USE_VISION"] = "true"  # Habilitar capacidades de visão

# Importar do módulo principal - corrigindo o import
from src.agent.base.agent import BaseAgent
from src.agent.base.task import Task
from src.agent.base.result import TaskResult

# Definir o prompt simples para buscar o preço do Bitcoin
PROMPT = """
Abra o google e digite 'Preço do bitcoin hoje', e retorne o preço atual do bitcoin.
"""

async def main():
    """Função principal para executar o teste."""
    try:
        start_time = datetime.now()
        logger.info(f"Iniciando teste em {start_time}")
        
        # Criar uma tarefa
        task = Task(
            id="bitcoin_price_test",
            type="prompt",
            data={"prompt": PROMPT}
        )
        
        # Inicializar o agente com o prompt simples
        agent = BaseAgent(task=task)
        
        # Executar a tarefa
        logger.info("Executando tarefa...")
        result = await agent.run()
        
        # Verificar o resultado
        if result:
            logger.info("Tarefa concluída com sucesso!")
            logger.info(f"Resultado: {result}")
            
            # Exibir tempo de execução
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Tempo total de execução: {duration:.2f} segundos")
            
            return result
        else:
            logger.error("Falha ao executar a tarefa")
            return None
            
    except Exception as e:
        logger.error(f"Erro durante a execução: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Garantir que o browser seja fechado
        if 'agent' in locals() and agent:
            try:
                await agent.cleanup()
                logger.info("Recursos liberados com sucesso")
            except Exception as cleanup_error:
                logger.error(f"Erro ao liberar recursos: {str(cleanup_error)}")

if __name__ == "__main__":
    # Executar o teste
    asyncio.run(main()) 