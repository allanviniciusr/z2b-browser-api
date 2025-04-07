"""
Utilitários para interações com o navegador.

Este módulo contém funções auxiliares para interações com o navegador,
como captura de screenshots, navegação, e tratamento de CAPTCHAs.
"""

import base64
import logging
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union

from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext

# Definição simples de TargetInfo para compatibilidade
class TargetInfo:
    """Classe que representa informações sobre um elemento alvo."""
    def __init__(self, selector=None, text=None, index=None):
        self.selector = selector
        self.text = text
        self.index = index


logger = logging.getLogger(__name__)


async def take_screenshot(browser_context: BrowserContext, full_page: bool = True) -> bytes:
    """
    Captura um screenshot da página atual.
    
    Args:
        browser_context: O contexto do navegador
        full_page: Se True, captura a página inteira; caso contrário, apenas a área visível
        
    Returns:
        bytes: Dados do screenshot em formato de bytes
    """
    try:
        # Obter a página atual
        page = await browser_context.get_current_page()
        if not page:
            raise ValueError("Não foi possível obter a página atual")
            
        # Capturar screenshot da página
        return await page.screenshot(full_page=full_page)
    except Exception as e:
        logger.error(f"Erro ao capturar screenshot: {str(e)}")
        raise


async def scroll_page(browser_context: BrowserContext, amount: int = 300) -> None:
    """
    Rola a página para baixo.
    
    Args:
        browser_context: O contexto do navegador
        amount: A quantidade de pixels para rolar
    """
    try:
        # Obter a página atual
        page = await browser_context.get_current_page()
        if not page:
            raise ValueError("Não foi possível obter a página atual")
            
        # Rolar a página
        await page.evaluate(f"window.scrollBy(0, {amount});")
    except Exception as e:
        logger.error(f"Erro ao rolar a página: {str(e)}")
        raise


async def wait_for_navigation(browser_context: BrowserContext, timeout: float = 30.0) -> None:
    """
    Aguarda a navegação da página ser concluída.
    
    Args:
        browser_context: O contexto do navegador
        timeout: Tempo máximo de espera em segundos
    """
    try:
        # Obter a página atual
        page = await browser_context.get_current_page()
        if not page:
            raise ValueError("Não foi possível obter a página atual")
            
        # Aguardar navegação com timeout
        await page.wait_for_navigation(timeout=timeout * 1000)  # Convertendo para ms
    except Exception as e:
        logger.error(f"Erro ao aguardar navegação: {str(e)}")
        raise


async def get_page_info(browser_context: BrowserContext) -> Dict[str, Any]:
    """
    Obtém informações sobre a página atual.
    
    Args:
        browser_context: O contexto do navegador
        
    Returns:
        Dict[str, Any]: Informações sobre a página (URL, título, etc.)
    """
    try:
        # Obter a página atual
        page = await browser_context.get_current_page()
        if not page:
            raise ValueError("Não foi possível obter a página atual")
            
        # Obter URL da página
        url = page.url
        
        # Obter título da página
        title = await page.evaluate("document.title")
        
        return {
            "url": url,
            "title": title
        }
    except Exception as e:
        logger.error(f"Erro ao obter informações da página: {str(e)}")
        raise


async def get_interactive_elements(browser_context: BrowserContext) -> List[Dict[str, Any]]:
    """
    Obtém elementos interativos da página atual.
    
    Args:
        browser_context: O contexto do navegador
        
    Returns:
        List[Dict[str, Any]]: Lista de elementos interativos com seus índices
    """
    try:
        # Obter a página atual
        page = await browser_context.get_current_page()
        if not page:
            raise ValueError("Não foi possível obter a página atual")
            
        # Executar script para obter elementos interativos
        elements = await page.evaluate("""
            () => {
                const interactiveElements = [];
                const elements = document.querySelectorAll('button, a, input, select, textarea');
                
                elements.forEach((el, index) => {
                    let elementType = el.tagName.toLowerCase();
                    let text = '';
                    
                    if (elementType === 'input') {
                        elementType = `input[type=${el.type || 'text'}]`;
                        text = el.value || el.placeholder || '';
                    } else if (elementType === 'button' || elementType === 'a') {
                        text = el.innerText || el.textContent || '';
                    } else if (elementType === 'select') {
                        text = el.options[el.selectedIndex]?.text || '';
                    }
                    
                    interactiveElements.push({
                        index: index + 1,
                        type: elementType,
                        text: text.trim(),
                        isVisible: el.offsetParent !== null,
                        rect: el.getBoundingClientRect()
                    });
                });
                
                return interactiveElements;
            }
        """)
        
        return elements
    except Exception as e:
        logger.error(f"Erro ao obter elementos interativos: {str(e)}")
        raise


async def wait_for_element(
    browser_context: BrowserContext,
    selector: str,
    timeout: float = 30.0,
    visible: bool = True
) -> bool:
    """
    Aguarda um elemento estar presente ou visível na página.
    
    Args:
        browser_context: O contexto do navegador
        selector: O seletor CSS do elemento
        timeout: Tempo máximo de espera em segundos
        visible: Se True, aguarda o elemento estar visível; caso contrário, apenas presente
        
    Returns:
        bool: True se o elemento foi encontrado no tempo determinado, False caso contrário
    """
    try:
        # Obter a página atual
        page = await browser_context.get_current_page()
        if not page:
            raise ValueError("Não foi possível obter a página atual")
            
        start_time = time.time()
        while time.time() - start_time < timeout:
            if visible:
                is_present = await page.evaluate(f"""
                    () => {{
                        const el = document.querySelector('{selector}');
                        return el && el.offsetParent !== null;
                    }}
                """)
            else:
                is_present = await page.evaluate(f"""
                    () => {{
                        return !!document.querySelector('{selector}');
                    }}
                """)
                
            if is_present:
                return True
                
            await asyncio.sleep(0.1)
            
        return False
    except Exception as e:
        logger.error(f"Erro ao aguardar elemento '{selector}': {str(e)}")
        return False


async def is_captcha_present(browser_context: BrowserContext) -> bool:
    """
    Verifica se há um CAPTCHA na página atual.
    
    Args:
        browser_context: O contexto do navegador
        
    Returns:
        bool: True se um CAPTCHA foi detectado, False caso contrário
    """
    try:
        # Obter a página atual
        page = await browser_context.get_current_page()
        if not page:
            raise ValueError("Não foi possível obter a página atual")
            
        captcha_selectors = [
            "iframe[src*='recaptcha']",
            ".g-recaptcha",
            "iframe[src*='captcha']",
            "#captcha",
            ".captcha",
            "img[src*='captcha']",
            "iframe[title*='areCAPTCHA']"
        ]
        
        captcha_keywords = [
            "captcha",
            "recaptcha",
            "verificação humana",
            "human verification",
            "prove you're human",
            "prove you are human",
            "are you a robot",
            "não sou um robô",
            "i'm not a robot"
        ]
        
        # Verifica seletores
        for selector in captcha_selectors:
            is_present = await page.evaluate(f"""
                () => {{
                    return !!document.querySelector('{selector}');
                }}
            """)
            
            if is_present:
                return True
                
        # Verifica palavras-chave no texto da página
        page_text = await page.evaluate("""
            () => {
                return document.body.innerText.toLowerCase();
            }
        """)
        
        for keyword in captcha_keywords:
            if keyword.lower() in page_text:
                return True
                
        return False
    except Exception as e:
        logger.error(f"Erro ao verificar presença de CAPTCHA: {str(e)}")
        return False


async def solve_simple_captcha(browser_context: BrowserContext) -> bool:
    """
    Tenta resolver CAPTCHAs simples, como cliques em checkboxes.
    
    Args:
        browser_context: O contexto do navegador
        
    Returns:
        bool: True se o CAPTCHA foi resolvido, False caso contrário
    """
    try:
        # Obter a página atual
        page = await browser_context.get_current_page()
        if not page:
            raise ValueError("Não foi possível obter a página atual")
            
        # Tenta clicar em checkboxes de reCAPTCHA
        recaptcha_selectors = [
            ".recaptcha-checkbox",
            ".rc-anchor-checkbox"
        ]
        
        # Verificar se há frames de captcha
        frames = await page.evaluate("""
            () => {
                return Array.from(document.querySelectorAll("iframe[src*='recaptcha']"))
                    .map(f => f.name || '');
            }
        """)
        
        if frames and len(frames) > 0:
            for frame_name in frames:
                if frame_name:
                    # Este código assume que deve haver métodos para alternar entre frames
                    # A implementação exata pode variar dependendo da versão da biblioteca
                    try:
                        # Tentativa de alternar para o frame - observe que isso pode precisar de ajuste
                        frame = await page.frame(frame_name)
                        if frame:
                            # Verificar se o checkbox está visível dentro do frame
                            checkbox_visible = await frame.evaluate("""
                                () => {
                                    const el = document.querySelector('.recaptcha-checkbox');
                                    return el && el.offsetParent !== null;
                                }
                            """)
                            
                            if checkbox_visible:
                                # Clicar no checkbox dentro do frame
                                await frame.click(".recaptcha-checkbox")
                                
                                # Aguarda para verificar se o CAPTCHA foi resolvido
                                await asyncio.sleep(2)
                                return not await is_captcha_present(browser_context)
                    except Exception as frame_error:
                        logger.warning(f"Erro ao interagir com frame: {str(frame_error)}")
        
        # Tentar clicar diretamente nos seletores na página principal
        for selector in recaptcha_selectors:
            try:
                # Verificar se o elemento existe e está visível
                is_visible = await page.evaluate(f"""
                    () => {{
                        const el = document.querySelector('{selector}');
                        return el && el.offsetParent !== null;
                    }}
                """)
                
                if is_visible:
                    await page.click(selector)
                    
                    # Aguarda para verificar se o CAPTCHA foi resolvido
                    await asyncio.sleep(2)
                    return not await is_captcha_present(browser_context)
            except Exception as click_error:
                logger.warning(f"Erro ao clicar em {selector}: {str(click_error)}")
                
        # CAPTCHA não resolvido
        return False
    except Exception as e:
        logger.error(f"Erro ao tentar resolver CAPTCHA: {str(e)}")
        return False


async def get_open_tabs(browser: Browser) -> List[Dict[str, Any]]:
    """
    Obtém informações sobre todas as abas abertas.
    
    Args:
        browser: A instância do navegador
        
    Returns:
        List[Dict[str, Any]]: Lista de informações sobre as abas abertas
    """
    try:
        targets = await browser.get_targets()
        page_targets = [target for target in targets if target.type == "page"]
        
        tabs = []
        for target in page_targets:
            tabs.append({
                "target_id": target.target_id,
                "url": target.url,
                "title": target.title
            })
            
        return tabs
    except Exception as e:
        logger.error(f"Erro ao obter abas abertas: {str(e)}")
        raise


async def switch_to_tab(browser: Browser, target_id: str) -> Optional[BrowserContext]:
    """
    Muda para uma aba específica.
    
    Args:
        browser: A instância do navegador
        target_id: O ID da aba para mudar
        
    Returns:
        Optional[BrowserContext]: O contexto da aba, ou None se não encontrado
    """
    try:
        context = await browser.create_browser_context_from_target(target_id)
        return context
    except Exception as e:
        logger.error(f"Erro ao mudar para aba '{target_id}': {str(e)}")
        return None


async def close_tab(browser: Browser, target_id: str) -> bool:
    """
    Fecha uma aba específica.
    
    Args:
        browser: A instância do navegador
        target_id: O ID da aba para fechar
        
    Returns:
        bool: True se a aba foi fechada com sucesso, False caso contrário
    """
    try:
        # Obter o contexto da aba e fechá-la
        context = await browser.create_browser_context_from_target(target_id)
        if context:
            await context.close()
            return True
        return False
    except Exception as e:
        logger.error(f"Erro ao fechar aba '{target_id}': {str(e)}")
        return False


async def open_new_tab(browser: Browser, url: Optional[str] = None) -> Optional[BrowserContext]:
    """
    Abre uma nova aba no navegador.
    
    Args:
        browser: A instância do navegador
        url: URL opcional para navegar
        
    Returns:
        Optional[BrowserContext]: O contexto da nova aba, ou None se falhou
    """
    try:
        # Cria uma nova aba
        context = await browser.create_browser_context()
        
        if url:
            await context.navigate(url)
            
        return context
    except Exception as e:
        logger.error(f"Erro ao abrir nova aba: {str(e)}")
        return None 