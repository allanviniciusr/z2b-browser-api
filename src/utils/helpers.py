import base64
import asyncio
import logging
import os
import sys
import subprocess
import tempfile
import shutil
import time

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Gerencia a inicialização e configuração do navegador
    para contornar limitações do asyncio no Windows
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.chrome_process = None
            self.chrome_user_data_dir = None
            self.is_temp_user_data = False
            self.cdp_url = None
            self._initialized = True
    
    def start_chrome_for_debugging(self, chrome_path=None, port=9222, user_data_dir=None):
        """
        Inicia o Chrome com o modo de depuração remota
        
        Args:
            chrome_path: Caminho para o executável do Chrome
            port: Porta para o modo de depuração
            user_data_dir: Diretório de dados do usuário (opcional)
            
        Returns:
            URL de depuração
        """
        # Se já existe um processo do Chrome rodando, retornar URL existente
        if self.chrome_process and self.chrome_process.poll() is None:
            return self.cdp_url
            
        # Limpar processo anterior se existir
        self.cleanup()
        
        if not chrome_path:
            # Procura o Chrome nas localizações típicas
            possible_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
            ]
            
            for path in possible_paths:
                expanded_path = os.path.expandvars(path)
                if os.path.exists(expanded_path):
                    chrome_path = expanded_path
                    break
        
        if not chrome_path or not os.path.exists(chrome_path):
            raise ValueError(f"Chrome não encontrado. Por favor, especifique o caminho manualmente.")
        
        # Criar diretório temporário para o usuário, se não especificado
        temp_user_data = False
        if not user_data_dir:
            user_data_dir = tempfile.mkdtemp(prefix="chrome_user_data_")
            temp_user_data = True
        
        # Argumentos para o Chrome
        args = [
            chrome_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-client-side-phishing-detection",
            "--disable-default-apps",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-hang-monitor",
            "--disable-popup-blocking",
            "--disable-prompt-on-repost",
            "--disable-sync",
            "--disable-translate",
            "--metrics-recording-only",
            "--no-sandbox",
            "--safebrowsing-disable-auto-update",
            "--password-store=basic",
            "--use-mock-keychain",
            "--headless=new"  # Modo headless novo
        ]
        
        logger.info(f"[CHROME] Iniciando Chrome em: {chrome_path}")
        logger.info(f"[CHROME] Porta de depuração: {port}")
        logger.info(f"[CHROME] Diretório de dados: {user_data_dir}")
        
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Espera um pouco para o Chrome iniciar
        time.sleep(2)
        
        # Verificar se o processo está rodando
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            logger.error(f"[CHROME] Falha ao iniciar Chrome: returncode={process.returncode}")
            logger.error(f"[CHROME] stdout: {stdout.decode('utf-8', errors='ignore')}")
            logger.error(f"[CHROME] stderr: {stderr.decode('utf-8', errors='ignore')}")
            if temp_user_data:
                shutil.rmtree(user_data_dir, ignore_errors=True)
            raise RuntimeError(f"Falha ao iniciar Chrome: {stderr.decode('utf-8', errors='ignore')}")
        
        # URL de depuração para o Playwright se conectar
        debug_url = f"http://localhost:{port}"
        
        # Armazenar o processo e diretório de dados para limpeza posterior
        self.chrome_process = process
        self.chrome_user_data_dir = user_data_dir
        self.is_temp_user_data = temp_user_data
        self.cdp_url = debug_url
        
        return debug_url
    
    def cleanup(self):
        """Limpa o processo do Chrome se estiver rodando"""
        if self.chrome_process:
            try:
                if self.chrome_process.poll() is None:  # Ainda está rodando
                    logger.debug("[CHROME] Matando processo do Chrome")
                    self.chrome_process.terminate()
                    self.chrome_process.wait(timeout=3)  # Espera até 3 segundos para terminar
            except Exception as e:
                logger.error(f"[CHROME] Erro ao matar processo do Chrome: {str(e)}")
            
            # Limpa o diretório de dados temporário
            if self.is_temp_user_data and self.chrome_user_data_dir:
                try:
                    logger.debug(f"[CHROME] Removendo diretório temporário: {self.chrome_user_data_dir}")
                    shutil.rmtree(self.chrome_user_data_dir, ignore_errors=True)
                except Exception as e:
                    logger.error(f"[CHROME] Erro ao remover diretório de dados: {str(e)}")
            
            self.chrome_process = None
            self.chrome_user_data_dir = None
            self.is_temp_user_data = False

async def capture_screenshot(browser_context):
    """Capture and encode a screenshot"""
    if browser_context is None:
        return None
        
    try:
        # Extract the Playwright browser instance
        playwright_browser = browser_context.browser.playwright_browser
        
        # Check if the browser instance is valid and if an existing context can be reused
        if playwright_browser and playwright_browser.contexts:
            playwright_context = playwright_browser.contexts[0]
        else:
            return None
        
        # Access pages in the context
        pages = None
        if playwright_context:
            pages = playwright_context.pages
        
        # Use an existing page or create a new one if none exist
        if pages:
            active_page = pages[0]
            for page in pages:
                if page.url != "about:blank":
                    active_page = page
        else:
            return None
        
        # Take screenshot
        screenshot = await active_page.screenshot(
            type='jpeg',
            quality=75,
            scale="css"
        )
        encoded = base64.b64encode(screenshot).decode('utf-8')
        return encoded
    except Exception as e:
        logger.error(f"Erro ao capturar screenshot: {str(e)}")
        return None
