# Sistema de Rastreabilidade para Agentes LLM

Este documento descreve as funcionalidades de rastreabilidade do sistema AgentTracker, que permite monitorar e analisar o comportamento dos agentes LLM durante a execução de tarefas no navegador.

## Componentes Principais

- **AgentTracker**: Módulo central que rastreia e registra as ações dos agentes
- **BrowserAgent**: Agente que interage com o navegador
- **LogHandler**: Sistema de manipulação de logs
- **VisualizadorLogs**: Ferramenta para visualizar e analisar logs gerados

## Principais Funcionalidades

- **Rastreamento não intrusivo**: Utiliza o mecanismo de callbacks do agente
- **Logs Detalhados**: Captura eventos, ações, screenshots e pensamentos
- **Rastreamento em tempo real**: Intercepta e registra eventos durante a execução
- **Captura do raciocínio do LLM**: Registra pensamentos, avaliações, memórias e objetivos
- **Visualização simplificada**: Ferramentas para análise dos logs
- **Interceptação de logs**: Captura mensagens de log diretamente do browser-use

## Como Usar

### Método 1: Track Agent Execution (Recomendado)

```python
from agent_tracker import track_agent_execution
from src.agent.agent import Agent

async def run_agent():
    # Criar agente
    agent = Agent()
    
    # Prompt de exemplo
    prompt = "Navegue para o Google e pesquise por 'cotação do dólar hoje'"
    
    # Executar com rastreamento
    result, tracker = await track_agent_execution(
        agent=agent,
        prompt=prompt,
        # Parâmetros opcionais:
        log_dir="agent_logs/minha_sessao",  # Diretório para salvar logs
        include_screenshots=True,  # Capturar screenshots
        auto_summarize=True,  # Gerar resumo ao final
        compression_level=0  # Nível de compressão (0-9)
    )
    
    # Acessar informações sobre o rastreamento
    print(f"Logs salvos em: {tracker.log_file}")
    
    # Verificar pensamentos capturados
    thinking_logs = tracker.get_thinking_logs()
    for log in thinking_logs:
        print(f"Passo {log['step']}:")
        print(f"  Avaliação: {log.get('evaluation')}")
        print(f"  Memória: {log.get('memory')}")
        print(f"  Próximo objetivo: {log.get('next_goal')}")
    
    return result
```

### Método 2: Uso Direto do AgentTracker

```python
from agent_tracker import AgentTracker
from src.agent.agent import Agent

async def run_with_tracker():
    # Criar rastreador
    tracker = AgentTracker(
        log_dir="agent_logs/sessao_manual",
        include_screenshots=True,
        auto_summarize=True
    )
    
    # Criar agente
    agent = Agent()
    
    # Definir prompt
    prompt = "Navegue para o Google e pesquise por 'bitcoin price'"
    tracker.set_prompt(prompt)
    
    # Executar com callback do tracker
    result = await agent.execute_prompt_task(prompt, callback=tracker.callback)
    
    # Obter resumo da execução
    resumo = tracker.get_resumo_execucao()
    print(f"Passos executados: {resumo['passos']}")
    
    # Salvar logs de pensamento em arquivo separado
    tracker.save_thinking_logs()
    
    return result
```

## Nova Funcionalidade: Interceptação de Logs

### Visão Geral

O sistema agora inclui um interceptador de logs que captura os pensamentos, avaliações e objetivos do agente LLM diretamente das mensagens de log do browser-use, sem depender de callbacks específicos. Esta funcionalidade permite uma análise detalhada do processo de raciocínio do agente durante a execução de tarefas.

### Como Usar o BrowserUseLogInterceptor

```python
from agent_tracker import BrowserUseLogInterceptor

# Função de callback para processar pensamentos capturados
def process_pensamento(pensamento):
    print(f"Pensamento capturado: {pensamento['texto']}")

# Criar e instalar o interceptador
interceptor = BrowserUseLogInterceptor(callback_pensamento=process_pensamento)
interceptor.instalar()

# Executar seu agente normalmente...
# ...

# Ao finalizar, desinstalar o interceptador
interceptor.desinstalar()
```

### Script de Teste

O arquivo `test_log_interceptor.py` demonstra como utilizar o interceptador:

1. Cria um interceptador de logs
2. Executa uma tarefa simples com o agente
3. Captura pensamentos em tempo real
4. Salva os pensamentos para análise posterior

Para executar o teste:

```bash
python test_log_interceptor.py
```

Ou utilize o script batch:

```bash
testar_log_interceptor.bat
```

### Como Funciona

O interceptador opera da seguinte forma:

1. Registra-se como um handler para os logs do browser-use
2. Analisa as mensagens de log usando expressões regulares para identificar padrões de pensamento
3. Cria eventos estruturados a partir do texto capturado
4. Notifica via callback quando um pensamento é identificado

### Vantagens

- **Não-intrusivo**: Não requer modificações no código do agente
- **Captura completa**: Registra todos os pensamentos emitidos pelo agente
- **Compatibilidade**: Funciona com qualquer versão do browser-use
- **Padronização**: Formata os logs em estruturas consistentes para análise

### Formato de Saída

Os pensamentos capturados são estruturados como:

```json
{
  "tipo": "pensamento",
  "timestamp": "2023-04-07T12:34:56.789Z",
  "texto": "Preciso encontrar o botão de login...",
  "contexto": {
    "acao_atual": "navegação",
    "url_atual": "https://exemplo.com"
  }
}
```

## Visualização de Logs

Para visualizar os logs e pensamentos capturados, utilize o script `verificar_logs.py`:

```bash
python verificar_logs.py --dir [diretório_de_logs]
```

## Personalização

### BrowserUseTracker

Para casos específicos, é possível acessar diretamente o rastreador especializado para browser-use:

```python
# Obter rastreador especializado
browser_tracker = tracker.get_browser_use_tracker()

# Registrar manualmente em um agente browser-use
tracker.register_browser_use_callbacks(browser_agent)
```

## Exemplo de Output

```
📍 Passo 2
👍 Avaliação: Success - I have successfully navigated to Google.
🧠 Memória: Navigated to Google. Now need to search for 'Preço do bitcoin hoje'.
🎯 Próximo objetivo: Enter 'Preço do bitcoin hoje' into the search bar.
🛠️  Ação: Digitação em [8]: 'Preço do bitcoin hoje'

📍 Passo 3
👍 Avaliação: Success - I have entered the search query into the search bar.
🧠 Memória: Navigated to Google and entered the search query 'Preço do bitcoin hoje'.
🎯 Próximo objetivo: Click on the search button to submit the query.
🛠️  Ação: Clique em elemento [22]
``` 