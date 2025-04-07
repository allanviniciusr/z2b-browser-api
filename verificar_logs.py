#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import sys
import glob
import argparse
from datetime import datetime

def verificar_diretorio(dir_path):
    """Verifica um diretório de logs e analisa sua integridade"""
    print(f"\nVerificando diretório: {dir_path}")
    
    # Verificar se o diretório existe
    if not os.path.exists(dir_path):
        print(f"ERRO: Diretório {dir_path} não existe!")
        return False
    
    # Contadores de erros e avisos
    erros = 0
    avisos = 0
    
    # Verificar estrutura de diretórios básica
    subdirs_esperados = ["etapa_0", "prompts", "results", "screenshots", "states"]
    for subdir in subdirs_esperados:
        path = os.path.join(dir_path, subdir)
        if not os.path.exists(path):
            print(f"AVISO: Subdiretório {subdir} não encontrado")
            avisos += 1
    
    # Verificar arquivo de log principal
    log_file = os.path.join(dir_path, "execucao_log.json")
    agent_log_file = os.path.join(dir_path, "agent_log.json")
    
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                log_data = json.load(f)
                
            # Verificar status e resultado
            status = log_data.get("status", "")
            if status != "concluído":
                print(f"AVISO: Status não é 'concluído' (atual: '{status}')")
                avisos += 1
            
            resultado = log_data.get("resultado_final")
            if resultado is None:
                print("AVISO: Resultado final é None")
                avisos += 1
            
            # Verificar etapas
            etapas = log_data.get("etapas", [])
            if not etapas:
                print("AVISO: Nenhuma etapa registrada")
                avisos += 1
            else:
                print(f"INFO: {len(etapas)} etapas registradas")
                
                # Verificar screenshots nas etapas
                for i, etapa in enumerate(etapas):
                    if "screenshot_path" not in etapa or not etapa["screenshot_path"]:
                        print(f"AVISO: Etapa {i+1} sem screenshot")
                        avisos += 1
                    elif not os.path.exists(etapa["screenshot_path"]):
                        print(f"ERRO: Screenshot da etapa {i+1} não existe: {etapa['screenshot_path']}")
                        erros += 1
        except json.JSONDecodeError:
            print(f"ERRO: Arquivo {log_file} não é um JSON válido")
            erros += 1
        except Exception as e:
            print(f"ERRO ao analisar {log_file}: {str(e)}")
            erros += 1
    elif os.path.exists(agent_log_file):
        try:
            with open(agent_log_file, "r", encoding="utf-8") as f:
                log_data = json.load(f)
            
            print(f"INFO: Arquivo de log do AgentTracker encontrado.")
            
            # Verificar eventos
            eventos = log_data.get("eventos", [])
            if not eventos:
                print("AVISO: Nenhum evento registrado")
                avisos += 1
            else:
                print(f"INFO: {len(eventos)} eventos registrados")
        except json.JSONDecodeError:
            print(f"ERRO: Arquivo {agent_log_file} não é um JSON válido")
            erros += 1
        except Exception as e:
            print(f"ERRO ao analisar {agent_log_file}: {str(e)}")
            erros += 1
    else:
        print(f"AVISO: Nenhum arquivo de log principal encontrado")
        avisos += 1
    
    # Verificar arquivo de pensamentos do AgentTracker
    thinking_file = os.path.join(dir_path, "thinking_logs.json")
    if os.path.exists(thinking_file):
        try:
            with open(thinking_file, "r", encoding="utf-8") as f:
                thinking_data = json.load(f)
            
            print(f"INFO: Arquivo de pensamentos encontrado com {len(thinking_data)} registros")
        except json.JSONDecodeError:
            print(f"ERRO: Arquivo {thinking_file} não é um JSON válido")
            erros += 1
        except Exception as e:
            print(f"ERRO ao analisar {thinking_file}: {str(e)}")
            erros += 1
    else:
        print(f"AVISO: Arquivo de pensamentos não encontrado")
        avisos += 1
    
    # Verificar relatório HTML
    html_file = os.path.join(dir_path, "relatorio.html")
    if not os.path.exists(html_file):
        print(f"AVISO: Relatório HTML não encontrado")
        avisos += 1
    else:
        size = os.path.getsize(html_file)
        if size < 100:
            print(f"AVISO: Relatório HTML tem tamanho suspeito ({size} bytes)")
            avisos += 1
        else:
            print(f"INFO: Relatório HTML encontrado ({size} bytes)")
    
    # Verificar screenshots
    screenshots_dir = os.path.join(dir_path, "screenshots")
    if os.path.exists(screenshots_dir):
        screenshots = glob.glob(os.path.join(screenshots_dir, "*.png"))
        if not screenshots:
            print("AVISO: Nenhum screenshot encontrado em 'screenshots/'")
            avisos += 1
        else:
            print(f"INFO: {len(screenshots)} screenshots encontrados em 'screenshots/'")
    
    # Verificar etapas
    etapas_dirs = glob.glob(os.path.join(dir_path, "etapa_*"))
    if not etapas_dirs:
        print("AVISO: Nenhum diretório de etapa encontrado")
        avisos += 1
    else:
        print(f"INFO: {len(etapas_dirs)} diretórios de etapa encontrados")
        
        # Verificar se há screenshots nas etapas
        screenshots_count = 0
        for etapa_dir in etapas_dirs:
            screenshots = glob.glob(os.path.join(etapa_dir, "*.png"))
            screenshots_count += len(screenshots)
        
        if screenshots_count == 0:
            print("AVISO: Nenhum screenshot encontrado nas etapas")
            avisos += 1
        else:
            print(f"INFO: {screenshots_count} screenshots encontrados nas etapas")
    
    # Resumo
    print("\nRESUMO DA VERIFICAÇÃO:")
    print(f"- Erros críticos: {erros}")
    print(f"- Avisos: {avisos}")
    
    if erros == 0 and avisos == 0:
        print("✅ O diretório de logs parece estar íntegro!")
        return True
    elif erros == 0:
        print("⚠️ O diretório de logs tem avisos, mas sem erros críticos.")
        return True
    else:
        print("❌ O diretório de logs apresenta problemas críticos!")
        return False

def analisar_eventos(events_file):
    """Analisa arquivo de eventos capturados para diagnóstico"""
    if not os.path.exists(events_file):
        print(f"ERRO: Arquivo de eventos {events_file} não encontrado")
        return
    
    try:
        with open(events_file, "r", encoding="utf-8") as f:
            events = json.load(f)
        
        print(f"\nANÁLISE DE EVENTOS ({len(events)} eventos):")
        
        # Agrupar por tipo de evento
        event_types = {}
        for event in events:
            event_type = event.get("event_type", "unknown")
            if event_type not in event_types:
                event_types[event_type] = 0
            event_types[event_type] += 1
        
        # Mostrar contagem por tipo
        print("Contagem por tipo de evento:")
        for event_type, count in event_types.items():
            print(f"- {event_type}: {count}")
        
        # Verificar se houve erros
        errors = [e for e in events if e.get("event_type") == "task.error" or "error" in e.get("data", {})]
        if errors:
            print(f"\nERROS DETECTADOS ({len(errors)}):")
            for i, error in enumerate(errors):
                error_msg = error.get("data", {}).get("error", "Erro não especificado")
                print(f"{i+1}. {error_msg}")
        
        # Verificar resultados
        results = [e for e in events if e.get("event_type") == "task.result"]
        if results:
            print(f"\nRESULTADOS ({len(results)}):")
            for i, result in enumerate(results):
                result_data = result.get("data", {}).get("result", "Resultado não especificado")
                if isinstance(result_data, dict):
                    print(f"{i+1}. {json.dumps(result_data, ensure_ascii=False)[:200]}...")
                else:
                    print(f"{i+1}. {str(result_data)[:200]}...")
        else:
            print("\nNenhum resultado encontrado nos eventos")
            
    except json.JSONDecodeError:
        print(f"ERRO: Arquivo {events_file} não é um JSON válido")
    except Exception as e:
        print(f"ERRO ao analisar {events_file}: {str(e)}")

def analisar_pensamentos(thinking_file, detalhado=False):
    """Analisa arquivo de pensamentos capturados pelo interceptador de logs"""
    if not os.path.exists(thinking_file):
        print(f"ERRO: Arquivo de pensamentos {thinking_file} não encontrado")
        return
    
    try:
        with open(thinking_file, "r", encoding="utf-8") as f:
            pensamentos = json.load(f)
        
        print(f"\nANÁLISE DE PENSAMENTOS ({len(pensamentos)} registros):")
        
        # Contar tipos de pensamentos
        tipos = {"evaluation": 0, "memory": 0, "next_goal": 0, "thought": 0}
        
        for p in pensamentos:
            for tipo in tipos.keys():
                if p.get(tipo):
                    tipos[tipo] += 1
        
        # Mostrar estatísticas
        print("Contagem por tipo de pensamento:")
        for tipo, count in tipos.items():
            print(f"- {tipo}: {count}")
        
        # Mostrar sequência de pensamentos
        if detalhado:
            print("\nSEQUÊNCIA DE PENSAMENTOS:")
            
            for i, p in enumerate(pensamentos):
                print(f"\n--- Passo {p.get('step', '?')} ({p.get('timestamp', 'sem data')}) ---")
                
                # Mostrar todos os tipos de pensamento disponíveis
                if p.get("evaluation"):
                    print(f"👍 Avaliação: {p.get('evaluation')}")
                
                if p.get("memory"):
                    print(f"🧠 Memória: {p.get('memory')}")
                
                if p.get("next_goal"):
                    print(f"🎯 Próximo objetivo: {p.get('next_goal')}")
                
                if p.get("thought"):
                    print(f"💭 Pensamento: {p.get('thought')}")
                
                if p.get("action"):
                    # Formatar a ação de maneira legível
                    if isinstance(p.get("action"), dict):
                        action_name = p.get("action").get("name", "desconhecida")
                        action_args = p.get("action").get("args", {})
                        print(f"🛠️ Ação: {action_name}")
                        for arg_name, arg_value in action_args.items():
                            if isinstance(arg_value, str) and len(arg_value) > 50:
                                arg_value = arg_value[:50] + "..."
                            print(f"  - {arg_name}: {arg_value}")
                    else:
                        print(f"🛠️ Ação: {p.get('action')}")
        else:
            # Mostrar apenas um resumo dos primeiros passos
            print("\nRESUMO DOS PRIMEIROS PENSAMENTOS:")
            for i, p in enumerate(pensamentos[:5]):
                if i >= 5:
                    break
                
                print(f"\n--- Passo {p.get('step', '?')} ---")
                
                if p.get("evaluation"):
                    print(f"👍 Avaliação: {p.get('evaluation')[:100]}...")
                
                if p.get("next_goal"):
                    print(f"🎯 Próximo objetivo: {p.get('next_goal')[:100]}...")
            
            if len(pensamentos) > 5:
                print(f"\n... e mais {len(pensamentos) - 5} registros de pensamento.")
                
    except json.JSONDecodeError:
        print(f"ERRO: Arquivo {thinking_file} não é um JSON válido")
    except Exception as e:
        print(f"ERRO ao analisar {thinking_file}: {str(e)}")

def listar_diretorios_log():
    """Lista diretórios de log disponíveis para análise"""
    # Procurar em agent_logs
    agent_logs = []
    if os.path.exists("agent_logs"):
        agent_logs = glob.glob(os.path.join("agent_logs", "*"))
    
    # Procurar em agent_tracker_logs
    tracker_logs = []
    if os.path.exists("agent_tracker_logs"):
        tracker_logs = glob.glob(os.path.join("agent_tracker_logs", "session_*"))
    
    # Procurar diretórios de debug
    debug_logs = glob.glob("debug_logs_*")
    
    # Combinar resultados
    all_logs = agent_logs + tracker_logs + debug_logs
    
    if not all_logs:
        print("Nenhum diretório de log encontrado!")
        return []
    
    print(f"\nDIRETÓRIOS DE LOG ENCONTRADOS ({len(all_logs)}):")
    for i, log_dir in enumerate(all_logs):
        mtime = os.path.getmtime(log_dir)
        mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{i+1}. {log_dir} (modificado em {mtime_str})")
    
    return all_logs

def parse_args():
    """Analisa argumentos da linha de comando"""
    parser = argparse.ArgumentParser(description="Verificador de logs do AgentTracker")
    
    parser.add_argument("dir", nargs="?", help="Diretório de logs para analisar")
    parser.add_argument("--thinking-only", action="store_true", help="Mostra apenas os logs de pensamento")
    parser.add_argument("--detalhado", action="store_true", help="Mostra informações detalhadas")
    
    return parser.parse_args()

def main():
    """Função principal"""
    args = parse_args()
    
    print("=" * 80)
    print("VERIFICADOR DE LOGS DO AGENTTRACKER")
    print("=" * 80)
    
    # Se um diretório foi especificado na linha de comando
    if args.dir:
        log_dir = args.dir
        
        # Se queremos apenas os logs de pensamento
        if args.thinking_only:
            thinking_file = os.path.join(log_dir, "thinking_logs.json")
            if os.path.exists(thinking_file):
                analisar_pensamentos(thinking_file, args.detalhado)
            else:
                print(f"ERRO: Arquivo de pensamentos não encontrado em {log_dir}")
                return
        else:
            # Verificação completa
            verificar_diretorio(log_dir)
            
            # Procurar arquivo de pensamentos
            thinking_file = os.path.join(log_dir, "thinking_logs.json")
            if os.path.exists(thinking_file):
                analisar_pensamentos(thinking_file, args.detalhado)
            
            # Procurar arquivos de eventos
            events_files = glob.glob(os.path.join(log_dir, "events_*.json"))
            if events_files:
                for events_file in events_files:
                    analisar_eventos(events_file)
        
        return
    
    # Listar diretórios de log
    log_dirs = listar_diretorios_log()
    
    if not log_dirs:
        print("Nenhum diretório de log para verificar. Execute o AgentTracker primeiro.")
        return
    
    # Perguntar qual diretório verificar
    try:
        if len(log_dirs) == 1:
            choice = 1
        else:
            choice = int(input("\nDigite o número do diretório a verificar (ou 0 para todos): "))
        
        if choice == 0:
            # Verificar todos
            for log_dir in log_dirs:
                verificar_diretorio(log_dir)
                
                # Procurar arquivo de pensamentos
                thinking_file = os.path.join(log_dir, "thinking_logs.json")
                if os.path.exists(thinking_file):
                    analisar_pensamentos(thinking_file, args.detalhado)
                
                # Procurar arquivos de eventos
                events_files = glob.glob(os.path.join(log_dir, "events_*.json"))
                if events_files:
                    for events_file in events_files:
                        analisar_eventos(events_file)
        elif 1 <= choice <= len(log_dirs):
            log_dir = log_dirs[choice-1]
            verificar_diretorio(log_dir)
            
            # Procurar arquivo de pensamentos
            thinking_file = os.path.join(log_dir, "thinking_logs.json")
            if os.path.exists(thinking_file):
                analisar_pensamentos(thinking_file, args.detalhado)
            
            # Procurar arquivos de eventos
            events_files = glob.glob(os.path.join(log_dir, "events_*.json"))
            if events_files:
                for events_file in events_files:
                    analisar_eventos(events_file)
        else:
            print("Escolha inválida!")
    except ValueError:
        print("Entrada inválida!")

if __name__ == "__main__":
    main() 