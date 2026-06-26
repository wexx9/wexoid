import telebot
from telebot import types
import sqlite3
import json
import time
import re
from datetime import datetime
import threading

# ==================== ТОКЕН ====================
TOKEN = '8252035464:AAEPis3jNFf4dxv1Z6lBbYIzQyr7sp9uopE'
bot = telebot.TeleBot(TOKEN)

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            join_date TEXT,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица товаров
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            title TEXT,
            description TEXT,
            price INTEGER,
            category TEXT,
            image_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            views INTEGER DEFAULT 0,
            is_pinned INTEGER DEFAULT 0,
            pin_expire TEXT
        )
    ''')
    
    # Таблица для закрепленных предложений
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pinned_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            pinned_at TEXT,
            expire_at TEXT
        )
    ''')
    
    # Таблица для статистики
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

init_db()

# ==================== ФУНКЦИИ РАБОТЫ С БД ====================
def add_user(user):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user.id,))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, join_date, is_admin)
            VALUES (?, ?, ?, ?, ?)
        ''', (user.id, user.username, user.first_name, datetime.now().strftime('%Y-%m-%d %H:%M'), 0))
        conn.commit()
    conn.close()

def is_admin(user_id):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def is_banned(user_id):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def add_product(seller_id, title, description, price, category, image_id):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO products (seller_id, title, description, price, category, image_id, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (seller_id, title, description, price, category, image_id, 'pending', datetime.now().strftime('%Y-%m-%d %H:%M')))
    product_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return product_id

def get_pending_products():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, seller_id, title, description, price, category, image_id, created_at
        FROM products WHERE status = 'pending'
        ORDER BY created_at ASC
    ''')
    result = cursor.fetchall()
    conn.close()
    return result

def get_all_products():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, seller_id, title, description, price, category, image_id, created_at, views, is_pinned
        FROM products WHERE status = 'approved'
        ORDER BY is_pinned DESC, created_at DESC
    ''')
    result = cursor.fetchall()
    conn.close()
    return result

def get_product(product_id):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, seller_id, title, description, price, category, image_id, created_at, views, is_pinned
        FROM products WHERE id = ?
    ''', (product_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def approve_product(product_id):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE products SET status = ? WHERE id = ?', ('approved', product_id))
    conn.commit()
    conn.close()

def reject_product(product_id):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE products SET status = ? WHERE id = ?', ('rejected', product_id))
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()

def increment_views(product_id):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE products SET views = views + 1 WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()

def pin_product(product_id, hours=24):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    expire = (datetime.now().timestamp() + hours * 3600)
    cursor.execute('UPDATE products SET is_pinned = ?, pin_expire = ? WHERE id = ?', (1, expire, product_id))
    conn.commit()
    conn.close()

def unpin_product(product_id):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE products SET is_pinned = 0, pin_expire = NULL WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()

def get_user_products(user_id):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, description, price, category, image_id, status, created_at
        FROM products WHERE seller_id = ?
        ORDER BY created_at DESC
    ''', (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result

def log_stats(user_id, action):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO stats (user_id, action, created_at) VALUES (?, ?, ?)',
                   (user_id, action, datetime.now().strftime('%Y-%m-%d %H:%M')))
    conn.commit()
    conn.close()

# ==================== ОСНОВНОЕ МЕНЮ ====================
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('📦 Товары')
    btn2 = types.KeyboardButton('➕ Выставить товар')
    btn3 = types.KeyboardButton('👤 Мой аккаунт')
    btn4 = types.KeyboardButton('ℹ️ Информация')
    btn5 = types.KeyboardButton('🔍 Поиск')
    btn6 = types.KeyboardButton('⭐ Избранное')
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return markup

def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('📋 Модерация')
    btn2 = types.KeyboardButton('📊 Статистика')
    btn3 = types.KeyboardButton('📌 Управление закрепами')
    btn4 = types.KeyboardButton('🚫 Бан-лист')
    btn5 = types.KeyboardButton('📢 Рассылка')
    btn6 = types.KeyboardButton('⬅️ Главное меню')
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return markup

# ==================== КОМАНДЫ ====================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    add_user(message.from_user)
    
    if is_banned(user_id):
        bot.send_message(user_id, '🚫 Вы заблокированы в этом боте!')
        return
    
    welcome_text = (
        "🌸 **Добро пожаловать в Маркет**\n\n"
        "🛒 Здесь ты можешь покупать и продавать сеты, ресурсы и услуги.\n"
        "💰 Продавай свои товары или находи лучшие предложения!\n\n"
        "📌 Используй кнопки ниже для навигации:"
    )
    
    markup = main_keyboard()
    bot.send_message(user_id, welcome_text, parse_mode='Markdown', reply_markup=markup)

# ==================== ОБРАБОТЧИК КНОПОК ====================
@bot.message_handler(func=lambda message: message.text == '📦 Товары')
def list_products(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.send_message(user_id, '🚫 Вы заблокированы!')
        return
    
    products = get_all_products()
    
    if not products:
        bot.send_message(user_id, '📭 Пока нет доступных товаров.')
        return
    
    # Отправляем товары по одному
    for product in products[:10]:  # Показываем 10 последних
        send_product_card(user_id, product)

def send_product_card(chat_id, product):
    product_id, seller_id, title, description, price, category, image_id, created_at, views, is_pinned = product
    
    # Увеличиваем просмотры
    increment_views(product_id)
    
    # Получаем информацию о продавце
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username, first_name FROM users WHERE user_id = ?', (seller_id,))
    seller = cursor.fetchone()
    conn.close()
    
    seller_name = seller[1] if seller else 'Неизвестный'
    seller_username = f'@{seller[0]}' if seller and seller[0] else f'ID: {seller_id}'
    
    pin_emoji = '📌 ' if is_pinned else ''
    price_text = f'💰 {price}₽'
    
    text = (
        f"{pin_emoji}**{title}**\n\n"
        f"📝 {description}\n\n"
        f"{price_text}\n"
        f"📂 Категория: {category}\n"
        f"👤 Продавец: {seller_name} ({seller_username})\n"
        f"👁️ Просмотров: {views}\n"
        f"🕐 Добавлен: {created_at}\n"
    )
    
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('💬 Написать продавцу', url=f'tg://user?id={seller_id}')
    btn2 = types.InlineKeyboardButton('⭐ В избранное', callback_data=f'fav_{product_id}')
    btn3 = types.InlineKeyboardButton('📊 Пожаловаться', callback_data=f'report_{product_id}')
    markup.add(btn1, btn2, btn3)
    
    if image_id:
        try:
            bot.send_photo(chat_id, image_id, caption=text, parse_mode='Markdown', reply_markup=markup)
        except:
            bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)
    else:
        bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== ВЫСТАВЛЕНИЕ ТОВАРА ====================
@bot.message_handler(func=lambda message: message.text == '➕ Выставить товар')
def start_sell(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.send_message(user_id, '🚫 Вы заблокированы!')
        return
    
    msg = bot.send_message(user_id, 
        "📝 **Выставление товара**\n\n"
        "Отправьте:\n"
        "1️⃣ Название товара\n"
        "2️⃣ Описание\n"
        "3️⃣ Цену\n"
        "4️⃣ Категорию (сеты, ресурсы, услуги, другое)\n"
        "5️⃣ Фото (необязательно)\n\n"
        "📌 Отправляйте информацию по очереди.\n"
        "❌ Для отмены напишите /cancel"
    )
    bot.register_next_step_handler(msg, process_sell_step1)

def process_sell_step1(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, '❌ Выставление отменено')
        return
    user_id = message.from_user.id
    
    # Сохраняем название
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO temp_sell (user_id, title) VALUES (?, ?)', (user_id, message.text))
    conn.commit()
    conn.close()
    
    msg = bot.send_message(user_id, '📝 Введите описание товара:')
    bot.register_next_step_handler(msg, process_sell_step2)

def process_sell_step2(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, '❌ Отменено')
        return
    user_id = message.from_user.id
    
    # Проверка на маты и рофлы
    bad_words = ['мат', 'рофл', 'лох', 'дурак', 'идиот', 'тупой', 'херня']
    for word in bad_words:
        if word.lower() in message.text.lower():
            bot.send_message(user_id, f'🚫 Текст содержит запрещенное слово: "{word}". Измените описание.')
            msg = bot.send_message(user_id, '📝 Введите описание снова:')
            bot.register_next_step_handler(msg, process_sell_step2)
            return
    
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE temp_sell SET description = ? WHERE user_id = ?', (message.text, user_id))
    conn.commit()
    conn.close()
    
    msg = bot.send_message(user_id, '💰 Введите цену (только число):')
    bot.register_next_step_handler(msg, process_sell_step3)

def process_sell_step3(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, '❌ Отменено')
        return
    user_id = message.from_user.id
    
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError
    except:
        bot.send_message(user_id, '🚫 Введите корректное число (больше 0)!')
        msg = bot.send_message(user_id, '💰 Введите цену:')
        bot.register_next_step_handler(msg, process_sell_step3)
        return
    
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE temp_sell SET price = ? WHERE user_id = ?', (price, user_id))
    conn.commit()
    conn.close()
    
    msg = bot.send_message(user_id, 
        "📂 Введите категорию:\n"
        "• сеты\n"
        "• ресурсы\n"
        "• услуги\n"
        "• другое"
    )
    bot.register_next_step_handler(msg, process_sell_step4)

def process_sell_step4(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, '❌ Отменено')
        return
    user_id = message.from_user.id
    category = message.text.lower()
    
    if category not in ['сеты', 'ресурсы', 'услуги', 'другое']:
        bot.send_message(user_id, '🚫 Неверная категория! Выберите из списка.')
        msg = bot.send_message(user_id, '📂 Введите категорию (сеты, ресурсы, услуги, другое):')
        bot.register_next_step_handler(msg, process_sell_step4)
        return
    
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE temp_sell SET category = ? WHERE user_id = ?', (category, user_id))
    conn.commit()
    conn.close()
    
    msg = bot.send_message(user_id, '🖼️ Отправьте фото товара (или нажмите /skip)')
    bot.register_next_step_handler(msg, process_sell_step5)

def process_sell_step5(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, '❌ Отменено')
        return
    user_id = message.from_user.id
    
    image_id = None
    if message.photo:
        image_id = message.photo[-1].file_id
    elif message.text != '/skip':
        bot.send_message(user_id, '🚫 Пожалуйста, отправьте фото или нажмите /skip')
        msg = bot.send_message(user_id, '🖼️ Отправьте фото товара (или нажмите /skip)')
        bot.register_next_step_handler(msg, process_sell_step5)
        return
    
    # Сохраняем товар
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('SELECT title, description, price, category FROM temp_sell WHERE user_id = ?', (user_id,))
    data = cursor.fetchone()
    
    if data:
        title, description, price, category = data
        product_id = add_product(user_id, title, description, price, category, image_id)
        
        cursor.execute('DELETE FROM temp_sell WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, 
            f"✅ Ваш товар отправлен на модерацию!\n"
            f"📦 Название: {title}\n"
            f"💰 Цена: {price}₽\n"
            f"📂 Категория: {category}\n\n"
            f"⏳ Ожидайте подтверждения администратора."
        )
        
        # Уведомление админам
        for admin_id in [8252035464, 1087968824]:  # Добавьте свои ID админов
            try:
                bot.send_message(admin_id, 
                    f"🆕 Новый товар на модерацию!\n"
                    f"📦 {title}\n"
                    f"💰 {price}₽\n"
                    f"👤 @{message.from_user.username or 'Нет'}\n"
                    f"🆔 ID товара: {product_id}"
                )
            except:
                pass

# ==================== МОЙ АККАУНТ ====================
@bot.message_handler(func=lambda message: message.text == '👤 Мой аккаунт')
def my_account(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.send_message(user_id, '🚫 Вы заблокированы!')
        return
    
    products = get_user_products(user_id)
    
    text = (
        f"👤 **Ваш аккаунт**\n\n"
        f"🆔 ID: {user_id}\n"
        f"📛 Имя: {message.from_user.first_name}\n"
        f"👤 Username: @{message.from_user.username or 'Нет'}\n"
        f"📦 Ваших товаров: {len(products)}\n"
    )
    
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton('📦 Мои товары', callback_data=f'my_products_{user_id}')
    markup.add(btn)
    
    bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== ИНФОРМАЦИЯ ====================
@bot.message_handler(func=lambda message: message.text == 'ℹ️ Информация')
def info(message):
    text = (
        "📖 **О Маркете**\n\n"
        "🛒 Это маркетплейс для продажи сетов, ресурсов и услуг.\n\n"
        "📌 **Правила:**\n"
        "• Запрещены маты и оскорбления\n"
        "• Только честные сделки\n"
        "• Администрация не несет ответственности за сделки\n\n"
        "🤝 Удачных покупок и продаж!"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== АДМИН ПАНЕЛЬ ====================
@bot.message_handler(func=lambda message: message.text == '📋 Модерация')
def moderation_panel(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, '🚫 У вас нет прав!')
        return
    
    pending = get_pending_products()
    
    if not pending:
        bot.send_message(user_id, '📭 Нет товаров на модерации.')
        return
    
    for product in pending[:5]:
        product_id, seller_id, title, description, price, category, image_id, created_at = product
        
        text = (
            f"📦 **Товар на модерацию**\n\n"
            f"🆔 ID: {product_id}\n"
            f"📛 Название: {title}\n"
            f"📝 Описание: {description}\n"
            f"💰 Цена: {price}₽\n"
            f"📂 Категория: {category}\n"
            f"👤 Продавец: {seller_id}\n"
        )
        
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('✅ Одобрить', callback_data=f'approve_{product_id}')
        btn2 = types.InlineKeyboardButton('❌ Отклонить', callback_data=f'reject_{product_id}')
        btn3 = types.InlineKeyboardButton('✏️ Изменить', callback_data=f'edit_{product_id}')
        markup.add(btn1, btn2, btn3)
        
        if image_id:
            try:
                bot.send_photo(user_id, image_id, caption=text, parse_mode='Markdown', reply_markup=markup)
            except:
                bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== КОЛБЭКИ ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    
    # Одобрение товара
    if data.startswith('approve_'):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, '🚫 Нет прав!')
            return
        
        product_id = int(data.split('_')[1])
        approve_product(product_id)
        
        bot.answer_callback_query(call.id, '✅ Товар одобрен!')
        bot.edit_message_text('✅ Товар одобрен', call.message.chat.id, call.message.message_id)
        
        # Уведомляем продавца
        conn = sqlite3.connect('market.db')
        cursor = conn.cursor()
        cursor.execute('SELECT seller_id, title FROM products WHERE id = ?', (product_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            seller_id, title = result
            try:
                bot.send_message(seller_id, f'✅ Ваш товар "{title}" одобрен и опубликован!')
            except:
                pass
    
    # Отклонение товара
    elif data.startswith('reject_'):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, '🚫 Нет прав!')
            return
        
        product_id = int(data.split('_')[1])
        
        # Запрашиваем причину
        msg = bot.send_message(user_id, 'Введите причину отклонения:')
        bot.register_next_step_handler(msg, lambda m: process_reject(m, product_id))
        bot.answer_callback_query(call.id, '✏️ Введите причину')
    
    # Закреп товара
    elif data.startswith('pin_'):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, '🚫 Нет прав!')
            return
        
        product_id = int(data.split('_')[1])
        pin_product(product_id, hours=24)
        bot.answer_callback_query(call.id, '📌 Товар закреплен на 24 часа!')
    
    # Избранное
    elif data.startswith('fav_'):
        product_id = int(data.split('_')[1])
        bot.answer_callback_query(call.id, '⭐ Добавлено в избранное!')
    
    # Пожаловаться
    elif data.startswith('report_'):
        product_id = int(data.split('_')[1])
        
        # Уведомляем админов
        for admin_id in [8252035464, 1087968824]:
            try:
                bot.send_message(admin_id, f'⚠️ Жалоба на товар ID: {product_id}\nОт: @{call.from_user.username}')
            except:
                pass
        
        bot.answer_callback_query(call.id, '📊 Жалоба отправлена админу!')

def process_reject(message, product_id):
    reason = message.text
    reject_product(product_id)
    
    # Уведомляем продавца
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('SELECT seller_id, title FROM products WHERE id = ?', (product_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        seller_id, title = result
        try:
            bot.send_message(seller_id, f'❌ Ваш товар "{title}" отклонен.\nПричина: {reason}')
        except:
            pass
    
    bot.send_message(message.chat.id, f'❌ Товар отклонен. Причина: {reason}')

# ==================== ЗАПУСК ====================
print("🚀 Бот запущен!")
print("=" * 40)
print(f"📌 Токен: {TOKEN[:10]}...")
print("📌 Бот работает!")
print("=" * 40)

while True:
    try:
        bot.infinity_polling(timeout=60)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        time.sleep(5)
