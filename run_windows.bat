@echo off
echo === Script de inicialização manual do Z2B Browser API para Windows ===
echo Este script é um método alternativo e só deve ser usado se o método automático falhar.
echo.

echo [1/4] Verificando requisitos...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Python não encontrado. Instale o Python 3.9 ou superior.
    exit /b 1
)

echo [2/4] Configurando modo CDP manual...
echo Configurando o .env para usar o Chrome em modo CDP manual...
echo ATENÇÃO: Isso vai modificar temporariamente seu arquivo .env
(
    type .env | findstr /v "CHROME_CDP" > .env.temp
    echo CHROME_CDP=http://localhost:9222 >> .env.temp
    move /y .env.temp .env > nul
)
echo Arquivo .env atualizado.

echo [3/4] Iniciando Chrome com depuração remota...
start "Chrome para Z2B Browser API" cmd /c "python start_chrome.py"
echo.
echo Chrome iniciado em uma nova janela. NÃO FECHE essa janela enquanto estiver usando o sistema!
echo.
echo Aguardando 5 segundos para o Chrome inicializar completamente...
timeout /t 5 /nobreak >nul

echo [4/4] Iniciando o servidor Z2B Browser API com Hypercorn...
echo.
echo Para parar o servidor, pressione Ctrl+C
echo.
python -m src.api.main

echo.
echo Encerrando o servidor...
echo Você pode fechar a janela do Chrome agora.
echo Restaurando configuração original do .env...
(
    type .env | findstr /v "CHROME_CDP" > .env.temp
    echo CHROME_CDP=auto >> .env.temp
    move /y .env.temp .env > nul
)
echo. 