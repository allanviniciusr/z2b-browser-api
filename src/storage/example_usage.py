from storage_manager import StorageManager
from pathlib import Path

def main():
    # Exemplo 1: Criar um novo gerenciador com task_id automático
    storage = StorageManager(client_id="cliente123")
    print(f"Task ID gerado automaticamente: {storage.task_id}")
    
    # Inicializar a estrutura de diretórios
    storage.init_storage()
    
    # Exemplo 2: Acessar os diferentes diretórios
    print("\nCaminhos dos diretórios:")
    print(f"Diretório base da tarefa: {storage.get_task_path()}")
    print(f"Diretório de vídeos: {storage.get_videos_path()}")
    print(f"Diretório de screenshots: {storage.get_screenshots_path()}")
    print(f"Diretório de logs: {storage.get_logs_path()}")
    print(f"Diretório de traces: {storage.get_traces_path()}")
    print(f"Diretório temporário: {storage.get_tmp_path()}")
    
    # Exemplo 3: Criar um gerenciador com task_id específico
    storage2 = StorageManager(
        client_id="cliente123",
        task_id="20240404_123456_abc123"
    )
    print(f"\nTask ID específico: {storage2.task_id}")
    
    # Exemplo 4: Gerar um novo task_id
    new_task_id = StorageManager.generate_task_id()
    print(f"\nNovo task_id gerado: {new_task_id}")

if __name__ == "__main__":
    main() 