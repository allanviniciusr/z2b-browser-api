#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import time

# Configurar logging
logging.basicConfig(level=logging.INFO,  # Reduzir para INFO para diminuir o ruído
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('log_interceptor_test')

# Adicionar handler específico para simular logs do browser-use sobre LLM
browser_logger = logging.getLogger("browser_use.agent.service")

# Desativar logs de debug dos módulos que geram muito ruído
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("browser_use").setLevel(logging.INFO)
logging.getLogger("playwright").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("charset_normalizer").setLevel(logging.WARNING)

# Carregar variáveis de ambiente
load_dotenv()

# Importar as classes necessárias
from src.agent.agent import Agent
from agent_tracker import AgentTracker, track_agent_execution, BrowserUseLogInterceptor

# Função para simular logs de uso de LLM
def simular_logs_llm(model=None, prompt_tokens=None):
    """
    Gera logs simulados de uso de LLM para testar a captura.
    
    Args:
        model: Modelo LLM a ser usado (ou será escolhido um padrão)
        prompt_tokens: Quantidade de tokens de prompt (ou será escolhido um padrão)
    """
    # Usar valores fornecidos ou padrões
    model = model or "gpt-4"
    prompt_tokens = prompt_tokens or 1024
    
    # Simulando request para LLM com valores do config atual
    browser_logger.info(f"LLM Request: model={model}, prompt_tokens={prompt_tokens}")
    time.sleep(0.2)
    
    # Calcular tokens de resposta como aproximadamente metade dos tokens de prompt
    completion_tokens = int(prompt_tokens / 2)
    
    # Simulando resposta do LLM com valores realistas
    browser_logger.info(f"LLM Response: completion_tokens={completion_tokens}, time=1.75s")
    time.sleep(0.1)
    
    # Calcular custo estimado baseado em valores da OpenAI
    # GPT-4: $0.03 por 1K tokens de prompt, $0.06 por 1K tokens de completion
    if "gpt-4" in model:
        prompt_cost = (prompt_tokens / 1000) * 0.03
        completion_cost = (completion_tokens / 1000) * 0.06
    # GPT-3.5: $0.0015 por 1K tokens de prompt, $0.002 por 1K tokens de completion
    elif "gpt-3.5" in model:
        prompt_cost = (prompt_tokens / 1000) * 0.0015
        completion_cost = (completion_tokens / 1000) * 0.002
    # Claude: $0.008 por 1K tokens de prompt, $0.024 por 1K tokens de completion
    elif "claude" in model:
        prompt_cost = (prompt_tokens / 1000) * 0.008
        completion_cost = (completion_tokens / 1000) * 0.024
    else:
        # Modelo genérico
        prompt_cost = (prompt_tokens / 1000) * 0.01
        completion_cost = (completion_tokens / 1000) * 0.02
    
    total_cost = prompt_cost + completion_cost
    
    # Simulando custo estimado com valor calculado
    browser_logger.info(f"Estimated cost: ${total_cost:.6f}")

async def test_log_interceptor():
    """Teste do interceptador de logs do browser-use"""
    # Prompt de exemplo que explora várias funcionalidades
    prompt = "Navegue para o site do Google, pesquise por 'Preço do bitcoin hoje', " \
             "encontre o valor atual do bitcoin e me informe o resultado."
    
    print("\n" + "="*80)
    print(f"TESTE DO INTERCEPTADOR DE LOGS DO BROWSER-USE\n")
    print(f"Prompt: '{prompt}'")
    print("="*80 + "\n")
    
    # Criar diretório de teste específico com timestamp para evitar conflitos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_log_dir = os.path.join("agent_logs", f"log_interceptor_test_{timestamp}")
    os.makedirs(test_log_dir, exist_ok=True)
    logger.info(f"Logs sendo salvos em: {test_log_dir}")
    
    # Caminhos para os arquivos de logs
    thinking_logs_file = os.path.join(test_log_dir, "thinking_logs.json")
    unknown_logs_file = os.path.join(test_log_dir, "unknown_messages.json")
    summary_logs_file = os.path.join(test_log_dir, "summary_logs.json")
    timeline_file = os.path.join(test_log_dir, "timeline.json")
    pensamentos = []
    
    # Função para processar pensamentos capturados
    def process_pensamento(pensamento):
        """Callback para processar pensamentos capturados pelo interceptador"""
        pensamentos.append(pensamento)
        
        # Logar apenas fragmentos úteis para não poluir o console
        texto = pensamento.get('texto', '')[:50] if pensamento.get('texto') else 'Sem texto'
        categoria = ""
        
        # Verificar se há categorias
        if pensamento.get('pensamentos_por_categoria'):
            categorias = list(pensamento.get('pensamentos_por_categoria').keys())
            if categorias:
                categoria = f" [Categorias: {', '.join(categorias)}]"
        
        logger.info(f"Pensamento capturado (Passo {pensamento.get('passo')}): {texto}...{categoria}")
        
        # Salvar pensamentos em tempo real no arquivo JSON
        with open(thinking_logs_file, 'w', encoding='utf-8') as f:
            json.dump(pensamentos, f, ensure_ascii=False, indent=2)
    
    # Criar rastreador
    tracker = AgentTracker(
        log_dir=test_log_dir,
        include_screenshots=True,
        auto_summarize=True
    )
    tracker.set_prompt(prompt)
    
    # Criar agente Z2B
    os.environ["AGENT_IMPLEMENTATION"] = "z2b"
    agent = Agent(prompt=prompt)
    
    # Criar contador para eventos capturados
    pensamentos_capturados = []
    
    # Criar função de callback para contar eventos
    async def contador_callback(event_data):
        # Primeiro, repassar para o tracker original
        await tracker.callback(event_data)
        
        # Verificar se é um evento de passo com pensamentos
        if event_data.get("event_type") == "browser_use.agent.step" and (
            event_data.get("evaluation") or 
            event_data.get("memory") or 
            event_data.get("next_goal") or
            event_data.get("thought") or
            event_data.get("unstructured_thought") or
            (event_data.get("all_thoughts") and len(event_data.get("all_thoughts")) > 0)
        ):
            # Capturar para verificação
            pensamentos_capturados.append(event_data)
            
            # Log de diagnóstico
            step = event_data.get("step", "?")
            logger.info(f"Evento de pensamento capturado no passo {step}")
            
            # Logar estatísticas sobre os pensamentos (apenas em nível INFO)
            thoughts_by_category = event_data.get("thoughts_by_category", {})
            if thoughts_by_category:
                categories = [f"{cat}({len(thoughts)})" for cat, thoughts in thoughts_by_category.items()]
                logger.info(f"  Categorias: {', '.join(categories)}")
            
            # A cada 2 passos, simular alguns logs de LLM para testar a captura
            # Usar modelos reais e tokens realistas
            if step % 2 == 0:
                # Alternar entre diferentes modelos para simular variação
                if step % 6 == 0:
                    logger.info(f"Simulando logs de LLM (gpt-4) no passo {step}")
                    simular_logs_llm("gpt-4", 1200)
                elif step % 6 == 2:
                    logger.info(f"Simulando logs de LLM (gpt-3.5-turbo) no passo {step}")
                    simular_logs_llm("gpt-3.5-turbo", 800)
                else:
                    logger.info(f"Simulando logs de LLM (claude-3-opus) no passo {step}")
                    simular_logs_llm("claude-3-opus", 1500)
    
    # Criar e instalar o interceptador de logs
    interceptor = BrowserUseLogInterceptor(
        callback=contador_callback,
        callback_pensamento=process_pensamento,
        log_dir=test_log_dir
    )
    interceptor.instalar()
    
    # Simular alguns logs iniciais de LLM
    logger.info("Simulando logs de LLM iniciais")
    # Usar o modelo configurado no agente, obtendo diretamente do llm_config
    modelo_agente = "gpt-4"  # Valor padrão
    try:
        # Verificar primeiro no llm_config, que é a fonte mais confiável
        if hasattr(agent, 'llm_config') and agent.llm_config and "model_name" in agent.llm_config:
            modelo_agente = agent.llm_config["model_name"]
            logger.info(f"Usando modelo do llm_config: {modelo_agente}")
        # Verificar na implementação Z2B como fallback
        elif hasattr(agent, 'z2b_agent') and hasattr(agent.z2b_agent, 'llm') and hasattr(agent.z2b_agent.llm, 'model_name'):
            modelo_agente = agent.z2b_agent.llm.model_name
            logger.info(f"Usando modelo do z2b_agent: {modelo_agente}")
        else:
            # Tentar obter do ambiente como último recurso
            env_model = os.getenv("LLM_MODEL_NAME") or os.getenv("OPENAI_MODEL", "gpt-4")
            if env_model and env_model != "unknown":
                modelo_agente = env_model
                logger.info(f"Usando modelo das variáveis de ambiente: {modelo_agente}")
    except Exception as e:
        logger.info(f"Não foi possível detectar o modelo do agente: {e}")
        logger.info(f"Usando modelo padrão: {modelo_agente}")
    
    # Verificar o provider também
    provider = "openai"  # Valor padrão
    try:
        if hasattr(agent, 'llm_config') and agent.llm_config and "provider" in agent.llm_config:
            provider = agent.llm_config["provider"]
            logger.info(f"Provider detectado: {provider}")
    except:
        pass
        
    # Capturar tokens realistas para o modelo específico
    tokens_prompt = 1800
    # Ajustar os tokens com base no modelo
    if "gpt-4" in modelo_agente:
        tokens_prompt = 2200
    elif "gpt-3.5" in modelo_agente:
        tokens_prompt = 1500
    elif "claude" in modelo_agente:
        tokens_prompt = 2500
    
    # Gerar logs com valores reais do modelo
    simular_logs_llm(modelo_agente, tokens_prompt)
    
    # Executar o agente
    print("\nExecutando agente com interceptador de logs...")
    start_time = datetime.now()
    
    # Executar o agente com o callback do tracker
    try:
        result = await agent.execute_prompt_task(prompt, callback=contador_callback)
        
        end_time = datetime.now()
        print(f"\nExecução concluída em {(end_time - start_time).total_seconds():.2f} segundos")
        
        # Simular logs finais de LLM
        logger.info("Simulando logs de LLM finais")
        # Usar o mesmo modelo que foi detectado inicialmente
        simular_logs_llm(modelo_agente, 2400)
        
        # Aguardar mais um pouco para garantir que todos os eventos assíncronos foram processados
        await asyncio.sleep(1)
        
        # Finalizar explicitamente o rastreamento antes de continuar
        await interceptor.finish_tracking()
        
        # Obter resumo dos pensamentos do interceptador
        thoughts_summary = interceptor.get_thoughts_summary()
        
        # Salvar resumo dos pensamentos
        with open(summary_logs_file, 'w', encoding='utf-8') as f:
            json.dump(thoughts_summary, f, ensure_ascii=False, indent=2)
        
        # Salvar timeline
        interceptor.save_timeline(timeline_file)
        
        # Salvar mensagens desconhecidas para análise
        unknown_messages = interceptor.get_unknown_messages()
        with open(unknown_logs_file, 'w', encoding='utf-8') as f:
            json.dump(unknown_messages, f, ensure_ascii=False, indent=2)
        
        # Mostrar estatísticas da execução de forma concisa
        print(f"\nResumo da captura:")
        print(f"  • Pensamentos: {thoughts_summary.get('total_thoughts', 0)}")
        print(f"  • Passos: {thoughts_summary.get('step_count', 0)}")
        print(f"  • Categorias: {', '.join([f'{k}({v})' for k, v in thoughts_summary.get('categories', {}).items()])}")

        # Resumo de dados LLM
        timeline = interceptor.get_timeline()
        llm_data_captured = any([step.get("llm_usage") or step.get("llm_events") for step in timeline.get("timeline", [])])
        
        if llm_data_captured:
            llm_usage_steps = [step for step in timeline.get("timeline", []) if step.get("llm_usage")]
            llm_events_steps = [step for step in timeline.get("timeline", []) if step.get("llm_events")]
            
            print(f"\nInformações de LLM:")
            print(f"  • Eventos capturados: {len(llm_events_steps)} passos")
            print(f"  • Uso total: {len(llm_usage_steps)} passos")
            
            if llm_usage_steps:
                # Calcular estatísticas de uso
                total_prompt_tokens = sum(step.get("llm_usage", {}).get("prompt_tokens", 0) for step in llm_usage_steps)
                total_completion_tokens = sum(step.get("llm_usage", {}).get("completion_tokens", 0) for step in llm_usage_steps)
                total_cost = sum(step.get("llm_usage", {}).get("estimated_cost", 0) for step in llm_usage_steps)
                
                print(f"  • Total tokens: {total_prompt_tokens + total_completion_tokens}")
                print(f"  • Tokens de prompt: {total_prompt_tokens}")
                print(f"  • Tokens de resposta: {total_completion_tokens}")
                if total_cost > 0:
                    print(f"  • Custo estimado: ${total_cost:.6f}")
                
                # Mostrar modelos utilizados
                modelos = {}
                for step in llm_usage_steps:
                    modelo = step.get("llm_usage", {}).get("model", "desconhecido")
                    modelos[modelo] = modelos.get(modelo, 0) + 1
                    
                if modelos:
                    print(f"  • Modelos utilizados: {', '.join([f'{k}({v})' for k, v in modelos.items()])}")
                    
        # Mostrar mensagens brutas
        print(f"\nMensagens brutas capturadas: {len(unknown_messages)}")
        print(f"Mensagens salvas em: {unknown_logs_file}")
        
        # Mostrar pensamentos formatados
        if pensamentos:
            print("\nExemplos de pensamentos capturados:")
            for i, p in enumerate(pensamentos[:3]):
                if i >= 3:
                    break
                    
                print(f"\n--- Passo {p.get('passo', '?')} ---")
                
                # Verificar se tem categorias para mostrar
                if p.get("pensamentos_por_categoria"):
                    categories = list(p.get("pensamentos_por_categoria").keys())
                    if categories:
                        print(f"Categorias: {', '.join(categories)}")
                
                # Mostrar texto principal
                if p.get("texto"):
                    print(f"Texto: {p.get('texto')[:100]}...")
                
                # Mostrar detalhes se disponíveis
                if p.get("todos_pensamentos") and len(p.get("todos_pensamentos")) > 0:
                    print(f"Total de pensamentos neste passo: {len(p.get('todos_pensamentos'))}")
            
            if len(pensamentos) > 3:
                print(f"\n... e mais {len(pensamentos) - 3} eventos de pensamento.")
        else:
            print("\nNenhum pensamento foi capturado!")
            
        # Verificar se os logs foram salvos corretamente
        pensamentos_salvos = tracker.get_thinking_logs()
        print(f"\nRegistros de pensamento salvos no tracker: {len(pensamentos_salvos)}")
        
        # Mostrar caminhos dos arquivos para análise
        print(f"\nArquivos gerados:")
        print(f"  • Timeline: {timeline_file}")
        print(f"  • Pensamentos: {thinking_logs_file}")
        print(f"  • Resumo: {summary_logs_file}")
        print(f"  • Diretório: {test_log_dir}")
        
        # Resultado do teste
        return {
            "success": True,
            "log_dir": test_log_dir,
            "total_thoughts": thoughts_summary.get('total_thoughts', 0),
            "total_steps": timeline.get('total_steps', 0),
            "llm_data_captured": llm_data_captured,
            "files": {
                "timeline": timeline_file,
                "thinking_logs": thinking_logs_file,
                "summary": summary_logs_file,
                "unknown_messages": unknown_logs_file
            }
        }
    
    except Exception as e:
        logger.error(f"Erro durante execução do teste: {e}", exc_info=True)
        
        # Tentar finalizar o rastreamento mesmo em caso de erro
        try:
            # Tenta finalizar o interceptador
            await interceptor.finish_tracking()
        except Exception as inner_e:
            logger.error(f"Erro ao finalizar o rastreamento após falha: {inner_e}")
            
        # Desinstalar o interceptador antes de finalizar
        interceptor.desinstalar()
        print(f"\nTeste falhou com erro: {e}")
        return {
            "success": False,
            "error": str(e),
            "log_dir": test_log_dir
        }
    
    finally:
        # Desinstalar o interceptador para não afetar outras execuções
        interceptor.desinstalar()
        print("\nInterceptador de logs desinstalado.")

if __name__ == "__main__":
    # Executar o teste
    result = asyncio.run(test_log_interceptor())
    
    if result.get("success"):
        print("\n✅ Teste concluído com sucesso!")
        sys.exit(0)
    else:
        print("\n❌ Teste falhou!")
        sys.exit(1) 