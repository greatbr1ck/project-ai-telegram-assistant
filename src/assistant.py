import requests
import json

from config import API_DEEPSEEK_KEY

MODEL = "deepseek/deepseek-r1"
base_prompt = 'Проанализируй текст, который будет представлен и дай ответ в формате {type=<тип>, name=<название>, date=<дата>, time=<время>, desc=<описание>, length=<продолжительность мероприятия>}. Возможные типы запроса - добавление нового объекта в расписание (set_reminder), изменение объекта (update_reminder), его удаление (delete_reminder) и просьба показать все запланированные мероприятия (show_all_reminders). От себя ничего не придумывай, если какой-то информации нет, оставь символ "-". Если запрос типа update_reminder, то добавь в ответ поля new_name, new_time, new_length, new_date в зависимости от того, что могло измениться. Текст:'
search_base_prompt = 'Тебе будет дана база в формате [ ("название события", "время (время начала) события"),  ("название события", "время (время начала) события"),  ("название события", "время (время начала) события")...] и текст, который может относиться к одному из этих событий. Напиши только название события и его время в ответ на это сообщение в формате (name, time). Если ничего подходящего нет, то не пиши ничего. Если подходит несколько вариантов, пиши тот, который больше подходит по времени. База:  '

# AI-ассистент
def process_content(content):
    return content.replace('<think>', '').replace('</think>', '')

def search_request(data_base, text):
    prompt = search_base_prompt + data_base + '; Текст: "' + text + '"'
    return chat_stream(prompt)

def user_request(text):
    prompt = base_prompt + '"' + text + '"'
    return chat_stream(prompt)

def chat_stream(prompt):
    headers = {
        "Authorization": f"Bearer {API_DEEPSEEK_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True
    }

    with requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            stream=True
    ) as response:
        if response.status_code != 200:
            return "Ошибка API:" + " " + str(response.status_code)

        full_response = []

        for chunk in response.iter_lines():
            if chunk:
                chunk_str = chunk.decode('utf-8').replace('data: ', '')
                try:
                    chunk_json = json.loads(chunk_str)
                    if "choices" in chunk_json:
                        content = chunk_json["choices"][0]["delta"].get("content", "")
                        if content:
                            cleaned = process_content(content)
                            full_response.append(cleaned)
                except:
                    pass

        return ''.join(full_response)
