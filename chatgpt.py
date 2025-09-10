"""
Модуль интеграции с ChatGPT для Nova Chaloklum Health Massage Bot
"""
import logging
from typing import Optional

from config import FEATURE_CHATGPT, OPENAI_API_KEY
from utils import get_text

logger = logging.getLogger(__name__)

async def ask_chatgpt(prompt: str, user_id: int) -> str:
    """
    Отправляет запрос к ChatGPT и возвращает ответ
    
    Args:
        prompt: Вопрос пользователя
        user_id: ID пользователя для локализации
        
    Returns:
        Ответ ChatGPT или сообщение об ошибке
    """
    # Проверяем, включена ли функция AI
    if not FEATURE_CHATGPT or not OPENAI_API_KEY:
        return get_text(user_id, "ai_unavailable")
    
    try:
        # Импортируем OpenAI только при необходимости
        from openai import OpenAI
        
        # Создаем клиента OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Отправляем запрос к ChatGPT
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful assistant for Nova Chaloklum Health Massage spa. You can answer questions about massage, spa treatments, wellness, and general health topics. Keep responses concise and friendly."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=600
        )
        
        # Извлекаем ответ
        if response.choices and response.choices[0].message:
            return response.choices[0].message.content.strip()
        else:
            logger.error("Empty response from OpenAI")
            return get_text(user_id, "ai_unavailable")
            
    except ImportError:
        logger.error("OpenAI library not installed")
        return get_text(user_id, "ai_unavailable")
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return get_text(user_id, "ai_unavailable")