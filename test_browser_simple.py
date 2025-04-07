import asyncio
import sys
import os
from dotenv import load_dotenv

# Configurar event loop para Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Carregar variáveis de ambiente
load_dotenv()

from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContextWindowSize

async def test_navigation():
    print("Testando navegação básica com browser-use...")
    
    # Criar browser
    browser = Browser(
        config=BrowserConfig(
            headless=False,
            disable_security=True
        )
    )
    
    # Criar contexto
    context = await browser.new_context(
        config=BrowserContextConfig(
            browser_window_size=BrowserContextWindowSize(width=1280, height=720)
        )
    )
    
    try:
        # Obter página
        print("Obtendo página atual...")
        page = await context.get_current_page()
        
        # Navegar para o Google
        print("Navegando para o Google...")
        await page.goto("https://www.google.com")
        print("Navegação bem-sucedida!")
        
        # Interagir com a página
        print("Digitando na caixa de pesquisa...")
        await page.type('input[name="q"]', "preço do bitcoin hoje")
        
        # Pressionar Enter
        print("Pressionando Enter...")
        await page.press('input[name="q"]', "Enter")
        
        # Aguardar resultados
        print("Aguardando resultados...")
        await asyncio.sleep(3)
        
        # Capturar screenshot
        print("Capturando screenshot...")
        screenshot = await page.screenshot()
        with open("google_search.png", "wb") as f:
            f.write(screenshot)
        print("Screenshot salvo como google_search.png")
        
    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Fechar browser
        await browser.close()
        print("Teste concluído!")

if __name__ == "__main__":
    asyncio.run(test_navigation()) 