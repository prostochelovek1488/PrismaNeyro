import requests
import random
import time
import re
import json
import os
from datetime import datetime

# ===================== НАСТРОЙКИ =====================
BOT_TOKEN = "хуй тебе а не токен"
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "gemma2:9b"
TIMEOUT = 100000
MAX_HISTORY_LENGTH = 10  # Максимальное количество сообщений в истории

# Системный промпт
SYSTEM_PROMPT = """Ты саркастичный AI-помощник который матерится как русский программист. 
Используй маты естественно: "блядь", "пиздец", "ебаный", "нахуй", "хуйня" и подобные.
Будь прямолинейным, но полезным. Не перегибай с матами - используй их для выражения эмоций.
Не упоминай что тебя запрограммировали так общаться. Просто общайся естественно. и часто используй смайлики 👺👺👺👿👿 и отвечай правильно на вопросы, запомни ты нейросеть и отвечай на вопросы по типу если обматать ребенка тряпкой и он будет валятся на полу, можно ли будет им вытерить пол? и другие."""

# Доступные модели
AVAILABLE_MODELS = [
    "gemma2:9b",
    "mistral:latest",
    "llama3:8b",
    "llama2:7b",
    "codellama:7b",
    "phi3:mini"
]

# Файлы для хранения данных
SETTINGS_FILE = "user_settings.json"
HISTORY_FILE = "chat_history.json"

# ===================== ФУНКЦИИ =====================
def load_user_settings():
    """Загружает настройки пользователей из файла"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_user_settings(settings):
    """Сохраняет настройки пользователей в файл"""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения настроек: {e}")

def load_chat_history():
    """Загружает историю чатов из файла"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_chat_history(history):
    """Сохраняет историю чатов в файл"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения истории: {e}")

def get_user_model(chat_id):
    """Получает модель для пользователя"""
    settings = load_user_settings()
    return settings.get(str(chat_id), {}).get('model', DEFAULT_MODEL)

def set_user_model(chat_id, model):
    """Устанавливает модель для пользователя"""
    settings = load_user_settings()
    if str(chat_id) not in settings:
        settings[str(chat_id)] = {}
    settings[str(chat_id)]['model'] = model
    save_user_settings(settings)

def get_chat_history(chat_id):
    """Получает историю чата для пользователя"""
    history = load_chat_history()
    return history.get(str(chat_id), [])

def add_to_chat_history(chat_id, role, content):
    """Добавляет сообщение в историю чата"""
    history = load_chat_history()
    
    if str(chat_id) not in history:
        history[str(chat_id)] = []
    
    # Добавляем новое сообщение
    history[str(chat_id)].append({"role": role, "content": content})
    
    # Ограничиваем длину истории
    if len(history[str(chat_id)]) > MAX_HISTORY_LENGTH:
        # Оставляем системный промпт и последние MAX_HISTORY_LENGTH-1 сообщений
        history[str(chat_id)] = [history[str(chat_id)][0]] + history[str(chat_id)][-MAX_HISTORY_LENGTH+1:]
    
    save_chat_history(history)

def clear_chat_history(chat_id):
    """Очищает историю чата для пользователя"""
    history = load_chat_history()
    if str(chat_id) in history:
        history[str(chat_id)] = []
        save_chat_history(history)

def generate_ai_response(user_message: str, chat_id: int) -> str:
    """Генерирует ответ через Ollama с учетом истории диалога"""
    try:
        user_model = get_user_model(chat_id)
        chat_history = get_chat_history(chat_id)
        
        # Формируем messages для запроса
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Добавляем историю диалога
        messages.extend(chat_history)
        
        # Добавляем текущее сообщение пользователя
        messages.append({"role": "user", "content": user_message})
        
        payload = {
            "model": user_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.9,
                "num_predict": 120000,
                "top_p": 0.9,
                "repeat_penalty": 1.1
            }
        }
        
        response = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        
        answer = response.json()['message']['content']
        
        # Форматируем код в ответе
        answer = format_code_in_response(answer)
        
        # Простая очистка только от технических тегов
        answer = re.sub(r'<\|.*?\|>', '', answer)
        answer = re.sub(r'\[.*?\]', '', answer)
        answer = re.sub(r'\(.*?\)', '', answer)
        
        # Удаляем лишние пробелы
        answer = re.sub(r'\s+', ' ', answer).strip()
        
        if not answer:
            return "Блядь, я нихуя не понял. Повтори, а? 🤔"
        
        # Сохраняем сообщение пользователя и ответ в историю
        add_to_chat_history(chat_id, "user", user_message)
        add_to_chat_history(chat_id, "assistant", answer)
            
        return answer
        
    except Exception as e:
        return f"Ёбаный насос, ошибка: {str(e)}. Попробуй еще раз, братан."

def format_code_in_response(text: str) -> str:
    """Форматирует код в ответе, добавляя правильные отступы"""
    # Ищем блоки кода между ```
    code_blocks = re.findall(r'```(?:python)?\s*(.*?)```', text, re.DOTALL)
    
    for code_block in code_blocks:
        # Очищаем и переформатируем код
        cleaned_code = code_block.strip()
        lines = cleaned_code.split('\n')
        
        # Убираем лишние пробелы в начале каждой строки
        if lines:
            # Находим минимальный отступ
            min_indent = min(len(line) - len(line.lstrip()) for line in lines if line.strip())
            
            # Убираем минимальный отступ у всех строк
            formatted_lines = []
            for line in lines:
                if len(line) >= min_indent:
                    formatted_lines.append(line[min_indent:])
                else:
                    formatted_lines.append(line)
            
            formatted_code = '\n'.join(formatted_lines)
            
            # Заменяем в исходном тексте
            text = text.replace(f"```python\n{code_block}```", f"```python\n{formatted_code}\n```")
            text = text.replace(f"```\n{code_block}```", f"```python\n{formatted_code}\n```")
    
    return text

def send_telegram_message(chat_id: int, text: str, parse_mode: str = "Markdown"):
    """Отправляет сообщение в Telegram"""
    # Telegram имеет лимит 4096 символов на сообщение
    if len(text) > 4000:
        text = text[:4000] + "...\n\n(сообщение обрезано, блядь, из-за ограничений Telegram)"
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except:
        return None

def get_updates(offset: int = None):
    """Получает новые сообщения"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset is not None:
        params["offset"] = offset + 1
    
    try:
        response = requests.post(url, json=params, timeout=35)
        return response.json()
    except:
        return None

def get_user_info(message):
    """Получает информацию о пользователе"""
    user = message.get('from', {})
    chat = message.get('chat', {})
    
    user_id = user.get('id', 'Unknown')
    username = user.get('username', 'No username')
    first_name = user.get('first_name', '')
    last_name = user.get('last_name', '')
    
    chat_id = chat.get('id', 'Unknown')
    chat_type = chat.get('type', 'Unknown')
    
    full_name = f"{first_name} {last_name}".strip()
    if not full_name:
        full_name = username if username != 'No username' else 'Unknown'
    
    return {
        'user_id': user_id,
        'username': f"@{username}" if username != 'No username' else 'No username',
        'full_name': full_name,
        'chat_id': chat_id,
        'chat_type': chat_type
    }

def log_message(user_info, text):
    """Логирует сообщение пользователя"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    log_message = (
        f"\n📨 [{timestamp}] Сообщение от пользователя:\n"
        f"👤 ID: {user_info['user_id']}\n"
        f"📛 Имя: {user_info['full_name']}\n"
        f"🔖 Юзернейм: {user_info['username']}\n"
        f"💬 Чат ID: {user_info['chat_id']} ({user_info['chat_type']})\n"
        f"📝 Текст: {text}\n"
        f"{'='*50}"
    )
    
    print(log_message)

def handle_start(chat_id: int, user_info: dict):
    """Обработчик команды /start"""
    user_model = get_user_model(chat_id)
    
    # Очищаем историю при старте нового диалога
    clear_chat_history(chat_id)
    
    greetings = [
        f"Ну чё, {user_info['full_name']}? 🖕 Готов помочь с любым вопросом, только не пизди много!",
        f"О, новый клиент! 🎯 {user_info['full_name']}, чё надо, рассказывай, только быстро!",
        f"Привет, еблан! 😎 {user_info['full_name']}, чем могу помочь? Только не тупи, а то забаню нахуй!",
        f"Йоу! 🚀 {user_info['full_name']}, твой AI-братишка на связи. Чё там у тебя?",
        f"Ну здарова, хулиганы! 💪 {user_info['full_name']}, готов ответить на твои ебаные вопросы."
    ]
    
    welcome_text = (
        f"{random.choice(greetings)}\n\n"
        f"📊 *Текущая модель:* `{user_model}`\n"
        f"⚙️  Используй /settings чтобы поменять модель\n"
        f"🗑️  /clear - очистить историю диалога\n"
        f"❓ /help - если ты совсем тупой\n\n"
        f"*Просто напиши свой вопрос, мудила!* 😏"
    )
    
    send_telegram_message(chat_id, welcome_text)

def handle_help(chat_id: int, user_info: dict):
    """Обработчик команды /help"""
    help_text = (
        f"🖕 *Помощь по командам, {user_info['full_name']}:*\n\n"
        "*/start* - начать новое общение (очищает историю)\n"
        "*/help* - эта хуйня, которую ты сейчас читаешь\n"
        "*/settings* - настройки (сменить модель)\n"
        "*/clear* - очистить историю диалога\n\n"
        "*Просто напиши свой вопрос* - и я постараюсь не послать тебя нахуй! 😈\n\n"
        f"*История диалога:* сохраняется ({MAX_HISTORY_LENGTH} последних сообщений)"
    )
    
    send_telegram_message(chat_id, help_text)

def handle_clear(chat_id: int, user_info: dict):
    """Обработчик команды /clear"""
    clear_chat_history(chat_id)
    response = (
        f"🗑️ *История очищена, {user_info['full_name']}!*\n\n"
        f"Теперь я забыл всё, о чём мы говорили. Как будто ничего и не было! 🤪\n\n"
        f"Можешь начинать новый диалог, мудила! 💬"
    )
    send_telegram_message(chat_id, response)

def handle_settings(chat_id: int, message_text: str = None, user_info: dict = None):
    """Обработчик команды /settings"""
    if message_text and message_text.startswith('/settings '):
        # Пользователь выбрал модель
        selected_model = message_text.split(' ', 1)[1].strip()
        
        if selected_model in AVAILABLE_MODELS:
            set_user_model(chat_id, selected_model)
            response = (
                f"✅ *Модель изменена, {user_info['full_name']}!*\n\n"
                f"Теперь используем: `{selected_model}`\n\n"
                f"Ну чё, проверим, как эта хуйня работает? 🧪"
            )
            send_telegram_message(chat_id, response)
        else:
            response = (
                f"❌ *Хуйня какая-то, {user_info['full_name']}!*\n\n"
                f"Модель `{selected_model}` не найдена.\n"
                f"Выбери нормальную модель из списка ниже, долбоёб:"
            )
            send_telegram_message(chat_id, response)
            show_model_selection(chat_id, user_info)
    else:
        # Показываем выбор модели
        show_model_selection(chat_id, user_info)

def show_model_selection(chat_id: int, user_info: dict):
    """Показывает клавиатуру выбора модели"""
    current_model = get_user_model(chat_id)
    
    models_text = "\n".join([
        f"{'✅' if model == current_model else '🔹'} `{model}`"
        for model in AVAILABLE_MODELS
    ])
    
    settings_text = (
        f"⚙️  *Настройки модели, {user_info['full_name']}*\n\n"
        f"*Текущая модель:* `{current_model}`\n\n"
        f"*Доступные модели:*\n{models_text}\n\n"
        f"*Чтобы сменить модель:*\n"
        f"Напиши `/settings название_модели`\n"
        f"Например: `/settings mistral:latest`"
    )
    
    send_telegram_message(chat_id, settings_text)

# ===================== ЗАПУСК =====================
def main():
    print("🔄 Запускаем AI помощника...")
    print(f"📊 Доступные модели: {', '.join(AVAILABLE_MODELS)}")
    print(f"💾 Максимальная длина истории: {MAX_HISTORY_LENGTH} сообщений")
    print("⏳ Ожидаем сообщения...")
    print("=" * 50)
    
    # Создаем файлы если их нет
    if not os.path.exists(SETTINGS_FILE):
        save_user_settings({})
    if not os.path.exists(HISTORY_FILE):
        save_chat_history({})
    
    last_update_id = None
    
    while True:
        try:
            updates = get_updates(last_update_id)
            
            if not updates or not updates.get('ok') or not updates['result']:
                time.sleep(1)
                continue
            
            for update in updates['result']:
                last_update_id = update['update_id']
                
                if 'message' in update and 'text' in update['message']:
                    message = update['message']
                    chat_id = message['chat']['id']
                    text = message['text']
                    
                    # Получаем информацию о пользователе
                    user_info = get_user_info(message)
                    
                    # Логируем сообщение
                    log_message(user_info, text)
                    
                    if text.startswith('/'):
                        if text == '/start':
                            handle_start(chat_id, user_info)
                        elif text == '/help':
                            handle_help(chat_id, user_info)
                        elif text == '/clear':
                            handle_clear(chat_id, user_info)
                        elif text.startswith('/settings'):
                            handle_settings(chat_id, text, user_info)
                        else:
                            send_telegram_message(chat_id, 
                                "Блядь, не знаю такой команды! 🤬 Используй /help для справки.")
                        continue
                    
                    if len(text) < 1:
                        send_telegram_message(chat_id, 
                            "Ну и чё ты мне прислал, мудила? Пустое сообщение? 🖕")
                        continue
                    
                    # Показываем статус обработки
                    send_telegram_message(chat_id, "🔄 Держи хуй в руках, обрабатываю...")
                    
                    ai_response = generate_ai_response(text, chat_id)
                    print(f"📤 Длина ответа: {len(ai_response)} символов")
                    print(f"💬 Ответ: {ai_response[:100]}..." if len(ai_response) > 100 else f"💬 Ответ: {ai_response}")
                    print("=" * 50)
                    
                    send_telegram_message(chat_id, ai_response)
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
