#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
import base64
from datetime import datetime
from dotenv import load_dotenv

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_agent_screenshots")

# Carregar variáveis de ambiente
load_dotenv()

# Importar a classe Agent do arquivo certo
from src.agent.agent import Agent

# Diretório para salvar os screenshots
SCREENSHOTS_DIR = "agent_screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

async def callback_com_screenshots(event_data):
    """
    Callback simples que salva screenshots quando disponíveis nos eventos
    """
    event_type = event_data.get("event_type", "unknown")
    logger.info(f"Evento recebido: {event_type}")
    
    # Criar diretório para sessão atual se ainda não existe
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(SCREENSHOTS_DIR, f"session_{timestamp}")
    os.makedirs(session_dir, exist_ok=True)
    
    # Salvar screenshot se disponível
    if "screenshot" in event_data:
        screenshot_path = os.path.join(
            session_dir, 
            f"screenshot_{event_type}_{int(datetime.now().timestamp())}.png"
        )
        try:
            with open(screenshot_path, "wb") as f:
                f.write(base64.b64decode(event_data["screenshot"]))
            logger.info(f"Screenshot salvo em: {screenshot_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar screenshot: {str(e)}")
    
    # Salvar URL atual se disponível
    if "url" in event_data:
        url_path = os.path.join(
            session_dir, 
            f"url_{event_type}_{int(datetime.now().timestamp())}.txt"
        )
        try:
            with open(url_path, "w", encoding="utf-8") as f:
                f.write(event_data["url"])
            logger.info(f"URL salvo em: {url_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar URL: {str(e)}")
    
    # Logging de resultado se disponível
    if event_type == "task.result" and "result" in event_data:
        result_path = os.path.join(session_dir, "result.txt")
        try:
            with open(result_path, "w", encoding="utf-8") as f:
                f.write(str(event_data["result"]))
            logger.info(f"Resultado salvo em: {result_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar resultado: {str(e)}")
    
    return session_dir

async def main():
    # Prompt básico para buscar o preço do Bitcoin
    prompt = "Abra o google e digite 'Preço do bitcoin hoje', e retorne o preço atual do bitcoin."
    
    # Criar um agente
    agent = Agent(prompt=prompt)
    
    # Executar o prompt com callback para captura de screenshots
    print("Executando prompt com captura de screenshots...")
    result = await agent.execute_prompt_task(prompt, callback=callback_com_screenshots)
    
    # Mostrar resultado
    print("\nResultado da tarefa:")
    print(result)
    
    print(f"\nScreenshots e dados salvos em: {SCREENSHOTS_DIR}")
    
    return result

if __name__ == "__main__":
    # Executar o teste
    asyncio.run(main()) 