import subprocess
import os
import sys
import time

print("=" * 70)
print("Inicializador Manual do Chrome para Z2B Browser API")
print("=" * 70)
print("\nATENÇÃO: Este script é um método alternativo e só deve ser usado quando")
print("         o método automático falhar ou precisar de mais controle.\n")
print("         Para uso normal, simplesmente execute a API diretamente com:")
print("         python -m src.api.main\n")
print("=" * 70)
print("\n")

# Configuração
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"  # Ajuste conforme o caminho no seu sistema
if not os.path.exists(CHROME_PATH) and sys.platform == 'win32':
    CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
elif sys.platform == 'darwin':  # macOS
    CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
elif sys.platform == 'linux':  # Linux
    CHROME_PATH = "/usr/bin/google-chrome"

DEBUGGING_PORT = 9222
USER_DATA_DIR = os.path.join(os.getcwd(), "chrome_data")

# Criar diretório de dados se não existir
os.makedirs(USER_DATA_DIR, exist_ok=True)

# Comando para iniciar o Chrome com depuração remota
chrome_cmd = [
    CHROME_PATH,
    f"--remote-debugging-port={DEBUGGING_PORT}",
    f"--user-data-dir={USER_DATA_DIR}",
    "--no-first-run",
    "--no-default-browser-check",
    "--start-maximized"
]

print(f"Iniciando Chrome com porta de depuração {DEBUGGING_PORT}...")
process = subprocess.Popen(chrome_cmd)
print(f"Chrome iniciado com PID: {process.pid}")
print(f"URL de depuração: http://localhost:{DEBUGGING_PORT}")
print(f"IMPORTANTE: Mantenha esta janela aberta enquanto estiver usando o browser-use!")
print(f"Pressione Ctrl+C para encerrar o Chrome quando terminar.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Encerrando Chrome...")
    process.terminate()
    print("Chrome encerrado.") 