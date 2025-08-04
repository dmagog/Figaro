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
    
    async def get_route_data(self, telegram_id: int):
        """Получает данные маршрута пользователя"""
        try:
            url = f"{self.base_url}/bot/route-data/{telegram_id}"
            logger.info(f"Getting route data from {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Route data response: {result}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Route data API error {response.status}: {error_text}")
                        return {"error": f"HTTP {response.status}: {error_text}"}
                        
        except Exception as e:
            logger.error(f"Route data API client error: {e}", exc_info=True)
            return {"error": f"Ошибка при получении маршрута: {str(e)}"}
    
    async def get_route_day(self, telegram_id: int, day_number: int):
        """Получает маршрут на конкретный день"""
        try:
            url = f"{self.base_url}/bot/route-day/{telegram_id}/{day_number}"
            logger.info(f"Getting route day from {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Route day response: {result}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Route day API error {response.status}: {error_text}")
                        return {"error": f"HTTP {response.status}: {error_text}"}
                        
        except Exception as e:
            logger.error(f"Route day API client error: {e}", exc_info=True)
            return {"error": f"Ошибка при получении маршрута на день: {str(e)}"}
    
    async def get_route_days(self, telegram_id: int):
        """Получает список доступных дней в маршруте"""
        try:
            url = f"{self.base_url}/bot/route-days/{telegram_id}"
            logger.info(f"Getting route days from {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Route days response: {result}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Route days API error {response.status}: {error_text}")
                        return {"error": f"HTTP {response.status}: {error_text}"}
                        
        except Exception as e:
            logger.error(f"Route days API client error: {e}", exc_info=True)
            return {"error": f"Ошибка при получении дней маршрута: {str(e)}"} 