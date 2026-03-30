# services/ai.py
from ollama import AsyncClient

async def generate_response(prompt: str, model_name: str) -> str:
    """
    Асинхронно отправляет запрос к локальной модели Ollama и возвращает ответ.
    """
    try:
        # Используем AsyncClient, чтобы не блокировать Telegram-бота
        client = AsyncClient()
        response = await client.chat(
            model=model_name, 
            messages=[{'role': 'user', 'content': prompt}]
        )
        return response['message']['content']
    except Exception as e:
        return f"❌ Ошибка при подключении к Ollama: {e}\nУбедитесь, что Ollama запущена."