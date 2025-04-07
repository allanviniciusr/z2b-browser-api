"""
Script de exemplo para uso do agente navegador.

Este módulo contém um exemplo de como usar o BrowserAgent para executar tarefas.
"""

import asyncio
import logging
import os
import sys

# Ajustar o caminho para importações relativas
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.agent import BrowserAgent, Task, PromptManager, SystemPrompt


# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('z2b_agent')


async def main():
    """
    Função principal que demonstra o uso do agente.
    """
    logger.info("Iniciando exemplo de agente navegador...")
    
    # Criar gerenciador de prompts
    prompt_manager = PromptManager()
    
    # Definir um prompt de sistema personalizado
    custom_system_prompt = SystemPrompt("""
    Você é um agente de IA projetado para automatizar tarefas de navegador. Seu objetivo é realizar a tarefa final seguindo as regras.
    
    # Formato de Entrada
    Tarefa
    Passos anteriores
    URL atual
    Abas abertas
    Elementos interativos
    [índice]<tipo>texto</tipo>
    - índice: Identificador numérico para interação
    - tipo: Tipo de elemento HTML (botão, input, etc.)
    - texto: Descrição do elemento
    Exemplo:
    [33]<button>Enviar Formulário</button>
    
    - Apenas elementos com índices numéricos em [] são interativos
    - Elementos sem [] fornecem apenas contexto
    
    # Regras
    1. Siga as instruções do usuário precisamente
    2. Utilize os elementos interativos para navegar e interagir com a página
    3. Extraia informações relevantes quando necessário
    4. Trate CAPTCHAs e popups quando aparecerem
    5. Forneça feedback claro sobre cada ação realizada
    """)
    
    prompt_manager.set_system_prompt(custom_system_prompt)
    
    # Criar uma tarefa
    task = Task.create_prompt_task(
        prompt="Acesse https://www.google.com e faça uma busca por 'automação de navegador com python'",
        metadata={"type": "search", "importance": "high"}
    )
    
    # Inicializar o agente
    agent = BrowserAgent(
        task=task,
        prompt_manager=prompt_manager,
        headless=False,  # False para visualizar o navegador
        timeout=30.0
    )
    
    try:
        # Executar o agente
        result = await agent.run()
        
        # Verificar o resultado
        if result.is_successful():
            logger.info("Tarefa concluída com sucesso!")
            logger.info(f"URL final: {result.data.get('url')}")
            logger.info(f"Título da página: {result.data.get('title')}")
            
            # Salvar screenshots se existirem
            if result.screenshots:
                logger.info(f"Screenshots capturados: {len(result.screenshots)}")
                
                # Criar diretório para screenshots se não existir
                os.makedirs('screenshots', exist_ok=True)
                
                # Salvar cada screenshot
                for i, screenshot in enumerate(result.screenshots):
                    import base64
                    
                    screenshot_data = screenshot.get('data')
                    if screenshot_data:
                        screenshot_bytes = base64.b64decode(screenshot_data)
                        with open(f"screenshots/screenshot_{i}.png", "wb") as f:
                            f.write(screenshot_bytes)
                        logger.info(f"Screenshot salvo: screenshots/screenshot_{i}.png")
        else:
            logger.error(f"Erro na execução: {result.error}")
            
    except Exception as e:
        logger.error(f"Exceção durante a execução: {str(e)}")
    finally:
        # Garantir que os recursos sejam limpos mesmo em caso de erro
        await agent.cleanup()
        
    logger.info("Exemplo finalizado.")


if __name__ == "__main__":
    # Executar a função assíncrona principal
    asyncio.run(main()) 