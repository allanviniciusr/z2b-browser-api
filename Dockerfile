FROM python:3.11-slim

# Definir variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=docker \
    BROWSER_HEADLESS=true

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Instalar Google Chrome (necessário para o browser-use)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Configurar diretório de trabalho
WORKDIR /app

# Copiar apenas os arquivos de requisitos primeiro (para aproveitar o cache do Docker)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar os navegadores para o Playwright
RUN python -m playwright install chromium

# Copiar o resto do código
COPY . .

# Criar diretórios para armazenamento
RUN mkdir -p /app/data/screenshots /app/data/traces /app/data/logs

# Expor a porta da API
EXPOSE 8000

# Script para iniciar o serviço
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1280x720x24 -ac +extension GLX +render -noreset &\nexport DISPLAY=:99\nexport API_WORKERS=2\npython -m src.api.main "$@"' > /app/start.sh \
    && chmod +x /app/start.sh

# Comando para iniciar a aplicação
CMD ["/app/start.sh"] 