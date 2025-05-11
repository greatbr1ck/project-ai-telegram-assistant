from assistant import user_request

from typing import Dict
from datetime import datetime, timedelta
import re

#разные функции

def parse_ai_string(reminder_str):
    # Удаляем фигурные скобки и разбиваем строку по запятым
    cleaned_str = reminder_str.strip('{}').split(', ')
    
    # Создаем словарь для хранения результатов
    result = {}
    
    # Парсим каждую пару ключ=значение
    for item in cleaned_str:
        key, value = item.split('=')
        result[key] = value
        
    return result

def classify_intent(text: str) -> Dict[str, str]:
    text = text.lower()
    
    # Ключевые слова для каждого намерения
    # patterns = {
    #     "set_reminder": ["напомни", "добавь напоминание", "создай напоминание", "установи"],
    #     "update_reminder": ["измени", "обнови", "перенеси"],
    #     "delete_reminder": ["удали", "отмени", "убери"],
    #     "show_all_reminders": ["все", "список", "всех"]
    # }

    print(text)
    r = user_request(text)
    print(r)
    return parse_ai_string(user_request(text))


def parse_time(text: str) -> str | None:
    # Ищем время в формате "12:30"
    time_match = re.search(r'(\d{1,2}[:.]\d{2})', text)
    if not time_match:
        return None
    
    time_str = time_match.group(1).replace('.', ':')
    try:
        remind_time = datetime.strptime(time_str, "%H:%M")
        remind_time = remind_time.replace(year=datetime.now().year, 
                                        month=datetime.now().month, 
                                        day=datetime.now().day)
        
        if remind_time < datetime.now():
            remind_time += timedelta(days=1)
                    
        return remind_time
    except ValueError:
        return None    