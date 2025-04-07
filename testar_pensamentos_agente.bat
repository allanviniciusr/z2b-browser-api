@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo TESTE DE RASTREAMENTO DE PENSAMENTOS DO AGENTE LLM
echo ===================================================
echo.

REM Ativar ambiente virtual se existir
if exist venv\Scripts\activate.bat (
    echo Ativando ambiente virtual...
    call venv\Scripts\activate.bat
)

REM Executar teste de rastreamento
echo Executando teste de rastreamento em tempo real...
python test_browser_tracker.py

REM Verificar resultado
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: O teste de rastreamento falhou!
    pause
    exit /b 1
)

REM Encontrar diretório de logs mais recente
echo.
echo Procurando logs gerados...
set "newest_dir="
set "newest_time=0"

for /d %%D in (agent_logs\browser_test_pensamentos*) do (
    for /f "tokens=1,2" %%A in ('dir /tw "%%D" ^| findstr /i /c:"%%D"') do (
        set "dir_time=%%A %%B"
        set "dir_time=!dir_time:/=!"
        set "dir_time=!dir_time::=!"
        set "dir_time=!dir_time: =!"
        
        if !dir_time! GTR !newest_time! (
            set "newest_time=!dir_time!"
            set "newest_dir=%%D"
        )
    )
)

if not defined newest_dir (
    echo ERRO: Não foi possível encontrar diretório de logs!
    pause
    exit /b 1
)

echo.
echo Diretório de logs encontrado: !newest_dir!

REM Verificar existência do arquivo thinking_logs.json
if exist "!newest_dir!\thinking_logs.json" (
    echo Arquivo de pensamentos encontrado: !newest_dir!\thinking_logs.json
    
    REM Executar visualizador de logs
    echo.
    echo Executando verificador de logs...
    python verificar_logs.py "!newest_dir!" --detalhado
) else (
    echo AVISO: Arquivo thinking_logs.json não encontrado!
    echo Verificando logs principais...
    python verificar_logs.py "!newest_dir!" --detalhado
)

echo.
echo ===================================================
echo TESTE CONCLUÍDO
echo ===================================================

pause 