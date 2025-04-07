import asyncio
import websockets
import requests
import json

class APIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = f"ws://localhost:8000/ws"

    def create_task(self, client_id: str, task_type: str, data: dict):
        url = f"{self.base_url}/tasks"
        payload = {
            "client_id": client_id,
            "task_type": task_type,
            "data": data
        }
        response = requests.post(url, json=payload)
        return response.json()

    def get_task_status(self, task_id: str):
        url = f"{self.base_url}/tasks/{task_id}"
        response = requests.get(url)
        return response.json()

    async def listen_task_updates(self, client_id: str):
        async with websockets.connect(f"{self.ws_url}/{client_id}") as websocket:
            while True:
                try:
                    message = await websocket.recv()
                    print(f"Recebido: {message}")
                except websockets.exceptions.ConnectionClosed:
                    break

# Exemplo de uso
async def main():
    client = APIClient()
    
    # Criar uma tarefa
    task = client.create_task(
        client_id="teste",
        task_type="browser",
        data={"url": "https://www.google.com"}
    )
    print(f"Tarefa criada: {task}")
    
    # Verificar status
    status = client.get_task_status(task["task_id"])
    print(f"Status: {status}")
    
    # Ouvir atualizações
    await client.listen_task_updates("teste")

if __name__ == "__main__":
    asyncio.run(main())