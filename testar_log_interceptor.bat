@echo off
echo ===== TESTE DO INTERCEPTADOR DE LOGS DO AGENTTRACKER =====
echo Este script testa a funcionalidade de interceptacao de logs 
echo para capturar pensamentos do agente LLM durante a execucao.

REM Verifica se o ambiente virtual existe e ativa
if exist venv\Scripts\activate.bat (
    echo Ativando ambiente virtual...
    call venv\Scripts\activate.bat
) else (
    echo Ambiente virtual nao encontrado, continuando sem ativar...
)

echo.
echo Executando teste do interceptador de logs...
python test_log_interceptor.py

REM Verifica o resultado da execução
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] O teste falhou com codigo de erro %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo.
echo Teste concluido com sucesso.
echo.
echo Verificando logs gerados...

REM Encontra o diretório de logs mais recente com o padrão log_interceptor_test
for /f "tokens=*" %%a in ('dir /b /ad /o-d "agent_logs\log_interceptor_test*" 2^>nul') do (
    set "LATEST_LOG_DIR=agent_logs\%%a"
    goto :found_log_dir
)

:found_log_dir
if not defined LATEST_LOG_DIR (
    echo [ERRO] Nenhum diretorio de log encontrado!
    exit /b 1
)

echo Diretorio de log mais recente: %LATEST_LOG_DIR%

REM Verifica se o arquivo de timeline existe
if exist "%LATEST_LOG_DIR%\timeline.json" (
    echo.
    echo Timeline encontrada: %LATEST_LOG_DIR%\timeline.json
    
    REM Exibe informações resumidas sobre a timeline
    powershell -Command "Get-Content '%LATEST_LOG_DIR%\timeline.json' | ConvertFrom-Json | Select-Object start_time, end_time, total_steps | ConvertTo-Json" 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo Nao foi possivel exibir o resumo da timeline usando PowerShell.
    )
    
    REM Exibe os primeiros passos da timeline
    echo.
    echo Primeiros passos da timeline:
    powershell -Command "$data = Get-Content '%LATEST_LOG_DIR%\timeline.json' | ConvertFrom-Json; $data.timeline | Select-Object -First 3 | ForEach-Object { Write-Output ('Passo: ' + $_.step + ', Fase: ' + $_.phase) }" 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo Nao foi possivel exibir os passos da timeline usando PowerShell.
    )
) else (
    echo [AVISO] Arquivo de timeline nao encontrado em %LATEST_LOG_DIR%
)

REM Verifica se o arquivo de pensamentos existe
if exist "%LATEST_LOG_DIR%\thinking_logs.json" (
    echo.
    echo Arquivo de pensamentos encontrado: %LATEST_LOG_DIR%\thinking_logs.json
    
    REM Conta quantos registros existem no arquivo JSON (aproximadamente)
    for /f "tokens=*" %%j in ('type "%LATEST_LOG_DIR%\thinking_logs.json" ^| find /c "step"') do (
        echo Arquivo contem aproximadamente %%j registros de pensamentos.
    )
    
    echo.
    echo Conteudo resumido do arquivo (primeiros 10 registros):
    echo ------------------------------
    powershell -Command "Get-Content '%LATEST_LOG_DIR%\thinking_logs.json' | ConvertFrom-Json | Select-Object -First 10 | ConvertTo-Json -Depth 1" 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo Nao foi possivel exibir o conteudo JSON usando PowerShell.
        echo Exibindo as primeiras 10 linhas do arquivo:
        type "%LATEST_LOG_DIR%\thinking_logs.json" | find /v "" /n | find " 1:" > nul
        if %ERRORLEVEL% EQU 0 (
            type "%LATEST_LOG_DIR%\thinking_logs.json" | find /v "" /n | find " 1:" 
            type "%LATEST_LOG_DIR%\thinking_logs.json" | find /v "" /n | find " 2:" 
            type "%LATEST_LOG_DIR%\thinking_logs.json" | find /v "" /n | find " 3:" 
            type "%LATEST_LOG_DIR%\thinking_logs.json" | find /v "" /n | find " 4:" 
            type "%LATEST_LOG_DIR%\thinking_logs.json" | find /v "" /n | find " 5:" 
            echo ... restante do arquivo omitido ...
        ) else (
            echo Erro ao exibir linhas do arquivo.
        )
    )
    echo ------------------------------
) else (
    echo [ERRO] Arquivo de pensamentos nao encontrado em %LATEST_LOG_DIR%!
    exit /b 1
)

REM Verifica se o arquivo de resumo existe
if exist "%LATEST_LOG_DIR%\summary_logs.json" (
    echo.
    echo Resumo estatistico encontrado: %LATEST_LOG_DIR%\summary_logs.json
    
    REM Exibe estatísticas resumidas
    powershell -Command "$data = Get-Content '%LATEST_LOG_DIR%\summary_logs.json' | ConvertFrom-Json; Write-Output ('Total de pensamentos: ' + $data.total_thoughts + ', Total de passos: ' + $data.step_count)" 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo Nao foi possivel exibir as estatisticas usando PowerShell.
    )
) else (
    echo [AVISO] Arquivo de resumo estatistico nao encontrado em %LATEST_LOG_DIR%
)

echo.
echo Executando visualizador de logs para analise detalhada...
echo.
python verificar_logs.py "%LATEST_LOG_DIR%" --thinking-only

echo.
echo ===== TESTE CONCLUIDO COM SUCESSO =====
echo Para visualizar logs completos, execute:
echo python verificar_logs.py "%LATEST_LOG_DIR%" --detalhado
echo.
echo Para visualizar a timeline em formato JSON, execute:
echo type "%LATEST_LOG_DIR%\timeline.json" 