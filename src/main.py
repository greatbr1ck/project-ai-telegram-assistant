from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

from datetime import datetime, timedelta
import asyncio

import re
from datetime import datetime

from typing import Literal

from utils import classify_intent, parse_time
from config import BOT_TOKEN

# словарь для напоминаний по каждому пользователю
reminders = {}

# Создаем объекты бота и диспетчера
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# Создаем объекты инлайн-кнопок
time_button = InlineKeyboardButton(
    text='время',
    callback_data='time_button_pressed'
)

text_button = InlineKeyboardButton(
    text='текст',
    callback_data='text_button_pressed'
)

# Создаем объект инлайн-клавиатуры
keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[time_button],
                     [text_button]])

IntentType = Literal[
    "set_reminder",  # установить напоминание
    "update_reminder",  # изменить напоминание
    "delete_reminder",  # удалить напоминание
    "show_all_reminders",  # показать все напоминания
    "show_specific_reminder",  # показать конкретное напоминание
    "unknown"  # неизвестное намерение
]

# Этот хэндлер будет срабатывать на команду "/start"
@dp.message(CommandStart())
async def process_start_command(message: Message):
    await message.answer(
        'Привет! Я твой личный помощник по напоминаниям! 📅\n'
        'Я помогу тебе не забыть о важных делах. Просто напиши, например:\n'
        '👉 "Напомни в 15:30 позвонить другу"\n'
        'или используй команды:\n'
        '/myreminders — посмотреть все напоминания\n'
        '/help — узнать, что я умею\n\n'
        'Давай начнем? 😊'
    )
    # Если пользователь только запустил бота и его нет в словаре '
    if message.from_user.id not in reminders:
        reminders[message.from_user.id] = list()


# Этот хэндлер будет срабатывать на команду "/help"
@dp.message(Command(commands='help'))
async def process_help_command(message: Message):
    await message.answer(
        'Я помогу тебе организовать дела с помощью напоминаний! Вот что я умею:\n\n'
        '📌 Создать напоминание: напиши, например, "Напомни в 14:00 купить продукты"\n'
        '🔄 Изменить напоминание: напиши "Измени напоминание в 14:00 на 15:00"\n'
        '🗑 Удалить напоминание: напиши "Удали напоминание, я выведу список всех задач, и ты выберешь нужное"\n'
        '📋 Показать все напоминания: используй /myreminders\n\n'
    )

current_editing = {}  # {user_id: {'old_time': str, 'old_text': str, 'field': str}}
delete_states = {}  # {user_id: {'step': 'select'|'confirm', 'index': int}}

# хэндлер для обработки ввода значений после нажатия кнопки 
@dp.message(lambda message: message.from_user.id in current_editing)
async def process_reminder_update(message: Message):
    user_id = message.from_user.id
    edit_data = current_editing[user_id]
    
    try:
        if edit_data['field'] == 'time':
            # Парсим новое время
            time_match = re.search(r'(\d{1,2}[:.]\d{2})', message.text)
            if not time_match:
                raise ValueError
            
            time_str = time_match.group(1).replace('.', ':')
            new_time = datetime.strptime(time_str, "%H:%M")
            new_time = new_time.replace(
                year=datetime.now().year,
                month=datetime.now().month,
                day=datetime.now().day
            )
            
            if new_time < datetime.now():
                new_time += timedelta(days=1)
            
            #поменять 
            # Обновляем время
            for i in range(len(reminders[user_id])):
                if reminders[user_id][i]['time'] == edit_data['old_time'] and reminders[user_id][i]['text'] == edit_data['old_text']:
                    reminders[user_id][i]['time'] = new_time

                    asyncio.create_task(
                        send_reminder(message.from_user.id, i)
                    )
                    response = f"Время напоминания изменено на {new_time.strftime('%H:%M')}"
                    break
        elif edit_data['field'] == 'text':
            #поменять

            # Обновляем текст
            for i in range(len(reminders[user_id])):
                if reminders[user_id][i]['time'] == edit_data['old_time'] and reminders[user_id][i]['text'] == edit_data['old_text']:
                    reminders[user_id][i]['text'] = message.text

                    asyncio.create_task(
                        send_reminder(message.from_user.id, i)
                    )
                    response = f"Текст напоминания изменен на: {message.text}"
                    break
        await message.answer(response)    
    except ValueError:
        await message.answer("Неверный формат времени. Используйте ЧЧ:ММ")
    finally:
        # Очищаем состояние редактирования
        del current_editing[user_id]


def count_reminders_at_time(user_id: int, target_time: datetime) -> int:
    if user_id not in reminders:
        return 0
    return sum(1 for reminder in reminders[user_id] if reminder['time'] == target_time)

def suggest_alternative_times(current_time: datetime) -> list[datetime]:
    suggestions = []
    for offset in [-30, -15, 15, 30]:  # Минуты до/после текущего времени
        new_time = current_time + timedelta(minutes=offset)
        suggestions.append(new_time)
    return suggestions

def create_suggestion_keyboard(suggestions: list[datetime], reminder_text: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=f"{suggestion.strftime('%H:%M')}",
            callback_data=f"set_time_{suggestion.strftime('%H:%M')}_{reminder_text}"
        ) for suggestion in suggestions
    ]
    return InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])

@dp.callback_query(F.data.startswith('set_time_'))
async def process_time_suggestion(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data.split('_')
    time_str = data[2]  # Формат ЧЧ:ММ
    reminder_text = '_'.join(data[3:]) 
    try:
        new_time = datetime.strptime(time_str, "%H:%M")
        new_time = new_time.replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
        if new_time < datetime.now():
            new_time += timedelta(days=1)
        if user_id not in reminders:
            reminders[user_id] = []
        reminders[user_id].append({'time': new_time, 'text': reminder_text})
        await callback.message.edit_text(f"Напоминание установлено на {new_time.strftime('%H:%M')}: {reminder_text}", reply_markup=None)
        asyncio.create_task(send_reminder(user_id, len(reminders[user_id]) - 1))
    except ValueError:
        await callback.message.edit_text("Ошибка при установке времени. Попробуйте снова.", reply_markup=None)
    await callback.answer()

@dp.message()
async def handle_natural_language(message: Message):
    request = classify_intent(message.text)
    intent = request['type']
    text = request['name']
    time = parse_time(request['time'])
    
    if intent == "set_reminder":
        if time:
            if message.from_user.id not in reminders:
                reminders[message.from_user.id] = []
            # Проверяем количество напоминаний на это время
            if count_reminders_at_time(message.from_user.id, time) >= 5:
                suggestions = suggest_alternative_times(time)
                suggestion_keyboard = create_suggestion_keyboard(suggestions, text)
                await message.answer(
                    f"На {time.strftime('%H:%M')} уже 5 или более напоминаний. "
                    "Выберите другое время:",
                    reply_markup=suggestion_keyboard
                )
            else:
                if message.from_user.id not in reminders:
                    reminders[message.from_user.id] = []

                reminders[message.from_user.id].append({
                    'time': time,
                    'text': text
                })
                    
                await message.answer(f"Напоминание установлено на {time.strftime('%H:%M')}")
                asyncio.create_task(
                    send_reminder(message.from_user.id, len(reminders[message.from_user.id]) - 1)
                )
        else:
            await message.answer("Не удалось распознать время. Попробуйте так: 'Напомни мне в 15:30 позвонить маме'")
    
    elif intent == "update_reminder":
        if time:
            if message.from_user.id not in reminders:
                reminders[message.from_user.id] = []

            # Сохраняем индекс редактируемого напоминания
            current_editing[message.from_user.id] = {
                'old_time': time,
                'old_text': text,
                'field': None  # Пока не выбрано, что редактировать
            }    

            await message.answer(
                text='Что вы хотите изменить?',
                reply_markup=keyboard
            )    
        else:
            await message.answer("Не удалось распознать время. Попробуйте так: 'Измени напоминание в 15:30'")    
    # Модифицируем обработчик delete_reminder
    elif intent == "delete_reminder":
        if message.from_user.id not in reminders or not reminders[message.from_user.id]:
            await message.answer("У вас нет активных напоминаний для удаления")
            return
        
        # Показываем список напоминаний с кнопками для удаления
        delete_states[message.from_user.id] = {'step': 'select'}
        
        text = "Выберите напоминание для удаления:\n"
        delete_keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        for i, reminder in enumerate(reminders[message.from_user.id], 1):
            text += f"{i}. {reminder['time'].strftime('%H:%M')} - {reminder['text']}\n"
            delete_keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"Удалить {i}",
                    callback_data=f"delete_{i-1}"  # индексы начинаются с 0
                )
            ])
        
        await message.answer(text, reply_markup=delete_keyboard)
    elif intent == "show_all_reminders":
        # Показать все напоминания
        await show_reminders(message)
    else:
        await message.answer("Не совсем понял вас. Можете уточнить?")


# Этот хэндлер будет срабатывать на апдейт типа CallbackQuery
# с data 'time_button_pressed'
@dp.callback_query(F.data == 'time_button_pressed')
async def process_time_button_press(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Устанавливаем, что будем менять время
    current_editing[user_id]['field'] = 'time'
    
    await callback.message.edit_text(
        text='Введите новое время для напоминания (формат ЧЧ:ММ)',
        reply_markup=None  # Убираем клавиатуру после выбора
    )
    await callback.answer()

# с data 'text_button_pressed'
@dp.callback_query(F.data == 'text_button_pressed')
async def process_text_button_press(callback: CallbackQuery):
    user_id = callback.from_user.id
     
    # Устанавливаем, что будем менять текст
    current_editing[user_id]['field'] = 'text'
    
    await callback.message.edit_text(
        text='Введите новый текст напоминания',
        reply_markup=None  # Убираем клавиатуру после выбора
    )
    await callback.answer()

# Добавляем обработчик кнопок удаления
@dp.callback_query(F.data.startswith('delete_'))
async def process_delete_button(callback: CallbackQuery):
    user_id = callback.from_user.id
    reminder_index = int(callback.data.split('_')[1])
    
    if user_id not in reminders or reminder_index >= len(reminders[user_id]):
        await callback.answer("Напоминание не найдено")
        return
    
    reminder = reminders[user_id][reminder_index]
    delete_states[user_id] = {'step': 'confirm', 'index': reminder_index}
    
    # Создаем клавиатуру подтверждения
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data=f"confirm_delete_{reminder_index}"),
            InlineKeyboardButton(text="Нет", callback_data="cancel_delete")
        ]
    ])
    
    await callback.message.edit_text(
        text=f"Вы уверены, что хотите удалить напоминание:\n"
             f"{reminder['time'].strftime('%H:%M')} - {reminder['text']}?",
        reply_markup=confirm_keyboard
    )
    await callback.answer()

# Обработчик подтверждения удаления
@dp.callback_query(F.data.startswith('confirm_delete_'))
async def process_confirm_delete(callback: CallbackQuery):
    user_id = callback.from_user.id
    reminder_index = int(callback.data.split('_')[2])
    
    if user_id in reminders and reminder_index < len(reminders[user_id]):
        deleted = reminders[user_id].pop(reminder_index)
        await callback.message.edit_text(
            text=f"Напоминание удалено:\n{deleted['time'].strftime('%H:%M')} - {deleted['text']}",
            reply_markup=None
        )
        if user_id in delete_states:
            del delete_states[user_id]
    else:
        await callback.message.edit_text("Ошибка: напоминание не найдено", reply_markup=None)
    
    await callback.answer()

# Обработчик отмены удаления
@dp.callback_query(F.data == "cancel_delete")
async def process_cancel_delete(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in delete_states:
        del delete_states[user_id]
    
    await callback.message.edit_text("Удаление отменено", reply_markup=None)
    await callback.answer()

# Отправка напоминания
async def send_reminder(user_id, reminder_index):
    """Асинхронная задача для отправки напоминания"""
    reminder = reminders[user_id][reminder_index]
    delay = (reminder['time'] - datetime.now()).total_seconds()
    
    if delay > 0:
        await asyncio.sleep(delay)
        await bot.send_message(user_id, f"⏰ Напоминание: {reminder['text']}")
        # Удаляем напоминание после отправки
        reminders[user_id].pop(reminder_index)

# все напоминания
@dp.message(Command(commands=['myreminders', 'мои напоминания']))
async def show_reminders(message: Message):
    if message.from_user.id not in reminders or not reminders[message.from_user.id]:
        await message.answer("У вас нет активных напоминаний")
        return
    
    text = "Ваши напоминания:\n"
    for i, reminder in enumerate(reminders[message.from_user.id], 1):
        text += (f"{i}. {reminder['time'].strftime('%H:%M')} - "
                f"{reminder['text']}\n")
    
    await message.answer(text)

if __name__ == '__main__':
    dp.run_polling(bot)