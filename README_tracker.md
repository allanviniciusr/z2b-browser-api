# AgentTracker - Rastreador Não-Intrusivo para Agentes Browser-Use

Este módulo fornece uma solução para rastrear detalhadamente a execução do agente browser-use sem modificar seu comportamento interno.

## Características Principais

- **Não-Intrusivo**: Utiliza o mecanismo de callback existente, sem modificar o comportamento do agente
- **Rastreamento Completo**: Captura prompts, respostas, screenshots, estados do navegador e ações
- **Relatório HTML**: Gera um relatório visual detalhado da execução
- **Armazenamento Otimizado**: Opções configuráveis para controlar o volume de dados armazenados
- **Fácil Integração**: Requer apenas uma linha de código para integrar a qualquer execução existente

## Como Usar

### Forma Simples (Função Auxiliar)

```python
from agent_tracker import track_agent_execution
from src.agent.agent import Agent

# Criar agente normalmente
agent = Agent(prompt="sua consulta aqui")

# Executar com rastreamento automático
result, tracker = await track_agent_execution(agent, "sua consulta aqui")

# Acessar informações do rastreamento
print(f"Logs salvos em: {tracker.log_dir}")
print(f"Relatório HTML: {os.path.join(tracker.log_dir, 'relatorio.html')}")
```

### Forma Detalhada (Uso Direto)

```python
from agent_tracker import AgentTracker
from src.agent.agent import Agent

# Criar rastreador com configurações personalizadas
tracker = AgentTracker(
    log_dir="meus_logs/sessao_teste",
    include_screenshots=True,
    include_html=False
)

# Definir o prompt
tracker.set_prompt("Abra o Google e pesquise por preço do Bitcoin")

# Criar agente normalmente
agent = Agent(prompt="Abra o Google e pesquise por preço do Bitcoin")

# Executar agente com o callback do tracker
resultado = await agent.execute_prompt_task(
    prompt="Abra o Google e pesquise por preço do Bitcoin", 
    callback=tracker.callback
)
```

### Executar o Exemplo Completo

```bash
python test_agent_tracker.py
```

## Estrutura de Arquivos Gerados

```
agent_tracker_logs/
└── session_{timestamp}/
    ├── execucao_log.json       # Log principal da execução
    ├── relatorio.html          # Relatório HTML com visualização detalhada
    ├── screenshots/            # Diretório para screenshots
    ├── states/                 # Estados do navegador
    ├── prompts/                # Prompts enviados e respostas recebidas
    ├── results/                # Resultados finais
    └── etapa_{numero}/         # Diretório para cada etapa
        ├── etapa_info.json     # Detalhes da etapa
        └── screenshot_{ts}.png # Screenshot da etapa
```

## Configurações Disponíveis

O `AgentTracker` aceita as seguintes opções de configuração:

- **log_dir**: Diretório onde os logs serão salvos (padrão: "agent_tracker_logs/session_{timestamp}")
- **include_screenshots**: Se True, salva screenshots durante a execução (padrão: True)
- **include_html**: Se True, salva o HTML da página (padrão: True)
- **include_element_tree**: Se True, salva a árvore de elementos (padrão: False)
- **max_screenshot_per_step**: Número máximo de screenshots por etapa (padrão: 5)

## Limitações

- O rastreador depende dos eventos emitidos pelo agente. Se o agente não emitir eventos para certas ações, elas não serão capturadas.
- O HTML e árvore de elementos podem ocupar muito espaço em disco quando habilitados.

## Complementação com Análises

O rastreador gera dados JSON estruturados que podem ser facilmente analisados por ferramentas de análise de dados ou scripts personalizados:

```python
import json
import os

# Carregar log de execução
with open("agent_tracker_logs/session_X/execucao_log.json", "r") as f:
    log_data = json.load(f)

# Análise de duração média por etapa
total_steps = len(log_data["etapas"])
total_duration = log_data["duracao_segundos"]
print(f"Duração média por etapa: {total_duration / total_steps:.2f} segundos")
``` 