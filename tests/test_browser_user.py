# tests/test_browser_use_example.py
import asyncio
import sys
import os

# Configurar o event loop para Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContextWindowSize

async def run_browser_example():
    print("Iniciando exemplo do browser-use...")
    
    # Configurações baseadas no exemplo oficial: https://github.com/browser-use/browser-use/blob/main/examples/browser/stealth.py
    browser = Browser(
        config=BrowserConfig(
            headless=False,  # Para ver o navegador
            disable_security=True,
        )
    )
    
    browser_context = await browser.new_context(
        config=BrowserContextConfig(
            browser_window_size=BrowserContextWindowSize(width=1280, height=720)
        )
    )
    
    try:
        # Primeiro, vamos imprimir os métodos disponíveis no browser_context
        print("Métodos disponíveis no browser_context:")
        context_methods = [method for method in dir(browser_context) if not method.startswith('_')]
        print("\n".join(context_methods))
        
        # Acessar o Google
        print("\nTentando acessar o Google...")
        page = await browser_context.get_current_page()
        if not page:
            page = await browser_context.new_page()
        await page.goto("https://www.google.com")
        print("Google acessado com sucesso")
        
        # Capturar screenshot
        print("\nTentando capturar screenshot...")
        page = await browser_context.get_current_page()
        
        # Esperar para ver o resultado
        await asyncio.sleep(5)
    except Exception as e:
        print(f"Erro ao acessar o Google: {e}")
    finally:
        await browser.close()
        print("Browser fechado.")

if __name__ == "__main__":
    print(f"Plataforma: {sys.platform}")
    print(f"Python: {sys.version}")
    asyncio.run(run_browser_example())