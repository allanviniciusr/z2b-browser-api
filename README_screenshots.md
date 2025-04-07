# Ferramenta para Rastreamento Visual do Agente

Esta ferramenta simples permite capturar screenshots durante a execução de um agente browser-use.

## Arquivo

- `test_agent_with_screenshots.py`: Script para executar o agente e capturar screenshots automaticamente.

## Como usar

Para capturar screenshots durante a execução do agente:

```bash
python test_agent_with_screenshots.py
```

Este script irá:
- Executar o agente com o prompt padrão para buscar o preço atual do Bitcoin
- Capturar screenshots em momentos relevantes da execução
- Salvar os screenshots em uma pasta `agent_screenshots/session_{timestamp}`
- Também salvar URLs e outros dados relevantes

O script usa um callback simples para interceptar os eventos durante a execução do agente. Você pode modificar o prompt na função `main()` para testar diferentes tarefas.

## Visualização

Para visualizar os screenshots capturados, você pode usar qualquer visualizador de imagens padrão do seu sistema operacional:

1. Navegue até a pasta `agent_screenshots`
2. Entre em uma das pastas de sessão (formato `session_{timestamp}`)
3. Abra os arquivos PNG para visualizar os screenshots capturados

## Dependências

- Python 3.7+
- As dependências são as mesmas do agente principal

## Personalização

Você pode facilmente personalizar o comportamento do callback no arquivo `test_agent_with_screenshots.py` para capturar outros dados ou modificar a estrutura dos arquivos salvos.

## Limitações

- Esta é uma implementação simples para fins de teste e depuração
- Não inclui análise avançada dos estados do agente
- O visualizador mostra apenas os screenshots, sem contexto adicional sobre cada estado 