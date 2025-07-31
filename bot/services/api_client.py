import aiohttp
import logging

logger = logging.getLogger(__name__)

class ApiClient:
    """HTTP клиент для взаимодействия с API основного приложения"""
    
    def __init__(self, base_url: str = "http://app:8080"):
        self.base_url = base_url
    
    async def send_template_message(self, telegram_id: int, template_id: int):
        """Отправляет запрос на отправку сообщения по шаблону"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "telegram_id": telegram_id,
                    "template_id": template_id
                }
                
                url = f"{self.base_url}/bot/send-template"
                logger.info(f"Sending request to {url}: {payload}")
                
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"API response: {result}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"API error {response.status}: {error_text}")
                        return {"error": f"HTTP {response.status}: {error_text}"}
                        
        except Exception as e:
            logger.error(f"API client error: {e}", exc_info=True)
            return {"error": f"Ошибка при отправке: {str(e)}"} 