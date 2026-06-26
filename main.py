import telebot
from telebot import types
import sqlite3
import time
import re
from datetime import datetime
import threading
import os

# ==================== ТОКЕН ====================
TOKEN = '8252035464:AAEPis3jNFf4dxv1Z6lBbYIzQyr7sp9uopE'
bot = telebot.TeleBot(TOKEN)

# ==================== АДМИНЫ ====================
ADMINS = ['wexx9', 'eyewz', 'sollacrime']

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    
    # Пользователи
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            join_date TEXT,
            balance INTEGER DEFAULT 0,
            referrer_id INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )
    ''')
    
    # Товары
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            title TEXT,
            description TEXT,
            price INTEGER,
            category TEXT,
            server TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    ''')
    
    # Реферальные награды
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reward INTEGER DEFAULT 50,
            claimed INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных готова")

init_db()

# ==================== ФУНКЦИИ БД ====================
def add_user(user, referrer_id=0):
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user.id,))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, join_date, referrer_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (user.id, user.username, user.first_name, datetime.now().strftime('%Y-%m-%d %H:%M'), referrer_id))
        
        # Награда рефереру
        if referrer_id != 0:
            cursor.execute('UPDATE users SET referrals = referrals + 1 WHERE user_id = ?', (referrer_id,))
            cursor.execute('UPDATE users SET balance = balance + 50 WHERE user_id = ?', (referrer_id,))
        conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def get_all_users():
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    result = cursor.fetchall()
    conn.close()
    return [row[0] for row in result]

def is_admin(user_id):
    user = get_user(user_id)
    if not user:
        return False
    return user[7] == 1

def is_banned(user_id):
    user = get_user(user_id)
    if not user:
        return False
    return user[8] == 1

def add_product(seller_id, title, description, price, category, server):
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO products (seller_id, title, description, price, category, server, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (seller_id, title, description, price, category, server, 'pending', datetime.now().strftime('%Y-%m-%d %H:%M')))
    product_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return product_id

def get_pending_products():
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, seller_id, title, description, price, category, server, created_at
        FROM products WHERE status = 'pending'
        ORDER BY created_at ASC
    ''')
    result = cursor.fetchall()
    conn.close()
    return result

def get_approved_products():
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, seller_id, title, description, price, category, server, created_at
        FROM products WHERE status = 'approved'
        ORDER BY created_at DESC
    ''')
    result = cursor.fetchall()
    conn.close()
    return result

def approve_product(product_id):
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE products SET status = ? WHERE id = ?', ('approved', product_id))
    conn.commit()
    conn.close()

def reject_product(product_id):
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE products SET status = ? WHERE id = ?', ('rejected', product_id))
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()

def get_user_products(user_id):
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, description, price, category, server, status, created_at
        FROM products WHERE seller_id = ?
        ORDER BY created_at DESC
    ''', (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result

def update_balance(user_id, amount):
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_user_referrals(user_id):
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT referrals FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_referral_link(user_id):
    return f'https://t.me/EasyShopMarketBot?start=ref_{user_id}'

# ==================== КЛАВИАТУРЫ ====================
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('🛒 Товары'),
        types.KeyboardButton('📦 Маркет')
    )
    markup.add(
        types.KeyboardButton('👤 Профиль'),
        types.KeyboardButton('➕ Выставить товар')
    )
    markup.add(
        types.KeyboardButton('ℹ️ Информация'),
        types.KeyboardButton('🆘 Поддержка')
    )
    if is_admin_quick():
        markup.add(types.KeyboardButton('👑 Админ панель'))
    return markup

def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('📋 Модерация'),
        types.KeyboardButton('📊 Статистика')
    )
    markup.add(
        types.KeyboardButton('📢 Рассылка'),
        types.KeyboardButton('🚫 Бан-лист')
    )
    markup.add(
        types.KeyboardButton('⬅️ Главное меню')
    )
    return markup

def is_admin_quick():
    # Проверка в момент создания клавиатуры
    return False  # Заменяется на проверку в обработчиках

# ==================== КОМАНДЫ ====================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    referrer_id = 0
    
    # Проверяем реферальную ссылку
    if message.text and 'ref_' in message.text:
        try:
            referrer_id = int(message.text.split('_')[1])
        except:
            pass
    
    add_user(message.from_user, referrer_id)
    
    if is_banned(user_id):
        bot.send_message(user_id, '🚫 Вы заблокированы!')
        return
    
    welcome = (
        "🌸 **Добро пожаловать в EasyShop!**\n\n"
        "🛒 Твой магазин для покупки и продажи:\n"
        "• 💎 Сапфиры\n"
        "• 💰 Валюта\n"
        "• ⚔️ Сеты\n"
        "• 👤 Аккаунты\n\n"
        "📌 Используй кнопки ниже:"
    )
    
    markup = main_keyboard()
    # Добавляем админку если есть
    if is_admin(user_id):
        markup.add(types.KeyboardButton('👑 Админ панель'))
    
    bot.send_message(user_id, welcome, parse_mode='Markdown', reply_markup=markup)

# ==================== ТОВАРЫ ====================
@bot.message_handler(func=lambda message: message.text == '🛒 Товары')
def products_menu(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.send_message(user_id, '🚫 Вы заблокированы!')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('💎 Сапфиры', callback_data='cat_sapphires'),
        types.InlineKeyboardButton('💰 Валюта', callback_data='cat_currency'),
        types.InlineKeyboardButton('⚔️ Сеты', callback_data='cat_sets'),
        types.InlineKeyboardButton('👤 Аккаунты', callback_data='cat_accounts')
    )
    
    bot.send_message(user_id, '📂 **Выбери категорию:**', parse_mode='Markdown', reply_markup=markup)

# ==================== МАРКЕТ ====================
@bot.message_handler(func=lambda message: message.text == '📦 Маркет')
def market_menu(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.send_message(user_id, '🚫 Вы заблокированы!')
        return
    
    products = get_approved_products()
    
    if not products:
        bot.send_message(user_id, '📭 Пока нет товаров в маркете.')
        return
    
    # Отправляем первые 5 товаров
    for product in products[:5]:
        send_product_card(user_id, product)

def send_product_card(chat_id, product):
    product_id, seller_id, title, description, price, category, server, created_at = product
    
    seller = get_user(seller_id)
    seller_name = seller[2] if seller else 'Неизвестный'
    seller_username = f'@{seller[1]}' if seller and seller[1] else f'ID: {seller_id}'
    
    text = (
        f"**{title}**\n\n"
        f"📝 {description}\n\n"
        f"💰 Цена: {price}₽\n"
        f"📂 Категория: {category}\n"
        f"🖥️ Сервер: {server}\n"
        f"👤 Продавец: {seller_name} ({seller_username})\n"
        f"🕐 Добавлен: {created_at}\n"
    )
    
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('💬 Написать продавцу', url=f'tg://user?id={seller_id}')
    btn2 = types.InlineKeyboardButton('📊 Пожаловаться', callback_data=f'report_{product_id}')
    markup.add(btn1, btn2)
    
    bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== ВЫСТАВИТЬ ТОВАР ====================
@bot.message_handler(func=lambda message: message.text == '➕ Выставить товар')
def start_sell(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.send_message(user_id, '🚫 Вы заблокированы!')
        return
    
    msg = bot.send_message(user_id, 
        "📝 **Выставление товара**\n\n"
        "Отправь название товара:\n"
        "❌ /cancel — отмена"
    )
    bot.register_next_step_handler(msg, process_title)

def process_title(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, '❌ Отменено')
        return
    
    user_id = message.from_user.id
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO temp_sell (user_id, title) VALUES (?, ?)', (user_id, message.text))
    conn.commit()
    conn.close()
    
    msg = bot.send_message(user_id, '📝 Напиши описание товара:')
    bot.register_next_step_handler(msg, process_description)

def process_description(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, '❌ Отменено')
        return
    
    user_id = message.from_user.id
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE temp_sell SET description = ? WHERE user_id = ?', (message.text, user_id))
    conn.commit()
    conn.close()
    
    msg = bot.send_message(user_id, '💰 Введите цену (только число):')
    bot.register_next_step_handler(msg, process_price)

def process_price(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, '❌ Отменено')
        return
    
    user_id = message.from_user.id
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError
    except:
        bot.send_message(user_id, '🚫 Введи корректное число!')
        msg = bot.send_message(user_id, '💰 Введите цену:')
        bot.register_next_step_handler(msg, process_price)
        return
    
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE temp_sell SET price = ? WHERE user_id = ?', (price, user_id))
    conn.commit()
    conn.close()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('💎 Сапфиры', callback_data='sell_sapphires'),
        types.InlineKeyboardButton('💰 Валюта', callback_data='sell_currency'),
        types.InlineKeyboardButton('⚔️ Сеты', callback_data='sell_sets'),
        types.InlineKeyboardButton('👤 Аккаунты', callback_data='sell_accounts')
    )
    
    msg = bot.send_message(user_id, '📂 Выбери категорию:', reply_markup=markup)
    bot.register_next_step_handler(msg, process_category)

def process_category(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, '❌ Отменено')
        return
    
    # Обработка выбора категории через callback
    pass

# ==================== ПРОФИЛЬ ====================
@bot.message_handler(func=lambda message: message.text == '👤 Профиль')
def profile(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.send_message(user_id, '🚫 Вы заблокированы!')
        return
    
    user = get_user(user_id)
    if not user:
        bot.send_message(user_id, '❌ Профиль не найден!')
        return
    
    referrals = get_user_referrals(user_id)
    link = get_referral_link(user_id)
    
    text = (
        f"👤 **Ваш профиль**\n\n"
        f"🆔 ID: {user[0]}\n"
        f"📛 Имя: {user[2]}\n"
        f"👤 Username: @{user[1] or 'Нет'}\n"
        f"💰 Баланс: {user[4]}₽\n"
        f"👥 Рефералов: {referrals}\n"
        f"🔗 Ссылка: {link}\n"
        f"📅 Дата регистрации: {user[3]}\n"
    )
    
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('🔗 Реферальная ссылка', callback_data='ref_link')
    btn2 = types.InlineKeyboardButton('📊 Мои товары', callback_data='my_products')
    markup.add(btn1, btn2)
    
    bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== ИНФОРМАЦИЯ ====================
@bot.message_handler(func=lambda message: message.text == 'ℹ️ Информация')
def info(message):
    text = (
        "📖 **О EasyShop**\n\n"
        "🛒 Это магазин для покупки и продажи:\n"
        "• 💎 Сапфиры\n"
        "• 💰 Валюта\n"
        "• ⚔️ Сеты\n"
        "• 👤 Аккаунты\n\n"
        "📌 **Правила:**\n"
        "• Запрещены маты и оскорбления\n"
        "• Только честные сделки\n"
        "• Администрация не несет ответственности\n\n"
        "🤝 Удачных покупок и продаж!"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== ПОДДЕРЖКА ====================
@bot.message_handler(func=lambda message: message.text == '🆘 Поддержка')
def support(message):
    text = (
        "🆘 **Поддержка**\n\n"
        "Если у тебя возникли вопросы или проблемы:\n\n"
        "📩 Напиши нам:\n"
        "• @sollacrime\n"
        "• @eyewz\n"
        "• @wexx9\n\n"
        "⏳ Отвечаем в течение 24 часов."
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== КОЛБЭКИ ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    
    # Категории товаров
    if data.startswith('cat_'):
        category = data.replace('cat_', '')
        products = get_approved_products()
        found = [p for p in products if p[5] == category]
        
        if not found:
            bot.answer_callback_query(call.id, '📭 Нет товаров в этой категории')
            return
        
        for product in found[:5]:
            send_product_card(user_id, product)
        bot.answer_callback_query(call.id, f'📦 Найдено {len(found)} товаров')
    
    # Реферальная ссылка
    elif data == 'ref_link':
        link = get_referral_link(user_id)
        bot.send_message(user_id, f'🔗 Твоя реферальная ссылка:\n{link}')
        bot.answer_callback_query(call.id)
    
    # Мои товары
    elif data == 'my_products':
        products = get_user_products(user_id)
        if not products:
            bot.send_message(user_id, '📭 У тебя нет товаров.')
        else:
            for p in products[:5]:
                text = f"📦 {p[1]}\n💰 {p[3]}₽\n📂 {p[4]}\n🖥️ {p[5]}\n📊 {p[6]}"
                bot.send_message(user_id, text)
        bot.answer_callback_query(call.id)
    
    # Пожаловаться
    elif data.startswith('report_'):
        product_id = data.split('_')[1]
        for admin in ADMINS:
            try:
                bot.send_message(f'@{admin}', f'⚠️ Жалоба на товар ID: {product_id}\nОт: @{call.from_user.username}')
            except:
                pass
        bot.answer_callback_query(call.id, '📊 Жалоба отправлена!')
    
    # Выбор категории при продаже
    elif data.startswith('sell_'):
        category = data.replace('sell_', '')
        conn = sqlite3.connect('easyshop.db')
        cursor = conn.cursor()
        cursor.execute('SELECT title, description, price FROM temp_sell WHERE user_id = ?', (user_id,))
        data = cursor.fetchone()
        conn.close()
        
        if data:
            title, description, price = data
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton('NeverTime', callback_data=f'server_NeverTime_{category}'),
                types.InlineKeyboardButton('FunTime', callback_data=f'server_FunTime_{category}'),
                types.InlineKeyboardButton('Phoenix', callback_data=f'server_Phoenix_{category}'),
                types.InlineKeyboardButton('Frizmine', callback_data=f'server_Frizmine_{category}')
            )
            
            bot.send_message(user_id, '🖥️ Выбери сервер:', reply_markup=markup)
    
    # Выбор сервера
    elif data.startswith('server_'):
        parts = data.split('_')
        server = parts[1]
        category = parts[2]
        
        conn = sqlite3.connect('easyshop.db')
        cursor = conn.cursor()
        cursor.execute('SELECT title, description, price FROM temp_sell WHERE user_id = ?', (user_id,))
        data = cursor.fetchone()
        
        if data:
            title, description, price = data
            product_id = add_product(user_id, title, description, price, category, server)
            
            cursor.execute('DELETE FROM temp_sell WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            
            bot.send_message(user_id, 
                f"✅ Товар отправлен на модерацию!\n\n"
                f"📦 {title}\n"
                f"💰 {price}₽\n"
                f"📂 {category}\n"
                f"🖥️ {server}\n\n"
                f"⏳ Ожидай подтверждения."
            )
            
            # Уведомляем админов
            for admin in ADMINS:
                try:
                    bot.send_message(f'@{admin}', 
                        f"🆕 Новый товар!\n"
                        f"📦 {title}\n"
                        f"💰 {price}₽\n"
                        f"👤 @{call.from_user.username}\n"
                        f"🖥️ {server}"
                    )
                except:
                    pass

# ==================== АДМИН ПАНЕЛЬ ====================
@bot.message_handler(func=lambda message: message.text == '👑 Админ панель')
def admin_panel(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(user_id, '🚫 Нет доступа!')
        return
    
    bot.send_message(user_id, '👑 **Админ панель**', parse_mode='Markdown', reply_markup=admin_keyboard())

@bot.message_handler(func=lambda message: message.text == '📋 Модерация')
def moderation(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    
    pending = get_pending_products()
    
    if not pending:
        bot.send_message(user_id, '📭 Нет товаров на модерации.')
        return
    
    for product in pending[:5]:
        product_id, seller_id, title, description, price, category, server, created_at = product
        
        text = (
            f"📦 **Товар на модерацию**\n\n"
            f"🆔 ID: {product_id}\n"
            f"📛 {title}\n"
            f"📝 {description}\n"
            f"💰 {price}₽\n"
            f"📂 {category}\n"
            f"🖥️ {server}\n"
            f"👤 Продавец: {seller_id}\n"
        )
        
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('✅ Одобрить', callback_data=f'approve_{product_id}')
        btn2 = types.InlineKeyboardButton('❌ Отклонить', callback_data=f'reject_{product_id}')
        markup.add(btn1, btn2)
        
        bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '📊 Статистика')
def stats(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    
    users = get_all_users()
    products = get_approved_products()
    pending = get_pending_products()
    
    text = (
        f"📊 **Статистика**\n\n"
        f"👥 Пользователей: {len(users)}\n"
        f"📦 Одобрено: {len(products)}\n"
        f"⏳ На модерации: {len(pending)}\n"
    )
    bot.send_message(user_id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '📢 Рассылка')
def broadcast_start(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    
    msg = bot.send_message(user_id, '📝 Введите сообщение для рассылки:')
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    
    users = get_all_users()
    sent = 0
    failed = 0
    
    status = bot.send_message(user_id, f'⏳ Рассылка... 0/{len(users)}')
    
    for i, uid in enumerate(users):
        try:
            bot.send_message(uid, f'📢 {message.text}')
            sent += 1
        except:
            failed += 1
        time.sleep(0.05)
        
        if i % 10 == 0:
            bot.edit_message_text(f'⏳ Рассылка... {i}/{len(users)}', user_id, status.message_id)
    
    bot.edit_message_text(
        f'✅ Рассылка завершена!\n'
        f'📤 Отправлено: {sent}\n'
        f'❌ Ошибок: {failed}',
        user_id, status.message_id
    )

@bot.message_handler(func=lambda message: message.text == '🚫 Бан-лист')
def ban_menu(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    
    msg = bot.send_message(user_id, 'Введи ID пользователя для бана (или /unban ID для разбана):')
    bot.register_next_step_handler(msg, process_ban)

def process_ban(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    
    if message.text.startswith('/unban'):
        try:
            uid = int(message.text.split(' ')[1])
            conn = sqlite3.connect('easyshop.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (uid,))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f'✅ Пользователь {uid} разбанен!')
        except:
            bot.send_message(user_id, '❌ Неверный формат! Используй: /unban ID')
    else:
        try:
            uid = int(message.text)
            conn = sqlite3.connect('easyshop.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (uid,))
            conn.commit()
            conn.close()
            bot.send_message(user_id, f'✅ Пользователь {uid} забанен!')
            try:
                bot.send_message(uid, '🚫 Вы забанены!')
            except:
                pass
        except:
            bot.send_message(user_id, '❌ Введи корректный ID!')

@bot.message_handler(func=lambda message: message.text == '⬅️ Главное меню')
def back_to_main(message):
    user_id = message.from_user.id
    markup = main_keyboard()
    if is_admin(user_id):
        markup.add(types.KeyboardButton('👑 Админ панель'))
    bot.send_message(user_id, '⬅️ Главное меню', reply_markup=markup)

# ==================== ОБРАБОТЧИК КОЛБЭКОВ АДМИНОВ ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_') or call.data.startswith('reject_'))
def admin_actions(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, '🚫 Нет прав!')
        return
    
    action, product_id = call.data.split('_')
    product_id = int(product_id)
    
    if action == 'approve':
        approve_product(product_id)
        bot.answer_callback_query(call.id, '✅ Одобрено!')
        bot.edit_message_text('✅ Товар одобрен', call.message.chat.id, call.message.message_id)
        
        # Уведомляем продавца
        conn = sqlite3.connect('easyshop.db')
        cursor = conn.cursor()
        cursor.execute('SELECT seller_id, title FROM products WHERE id = ?', (product_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            try:
                bot.send_message(result[0], f'✅ Ваш товар "{result[1]}" одобрен!')
            except:
                pass
    
    elif action == 'reject':
        reject_product(product_id)
        bot.answer_callback_query(call.id, '❌ Отклонено!')
        bot.edit_message_text('❌ Товар отклонен', call.message.chat.id, call.message.message_id)
        
        # Уведомляем продавца
        conn = sqlite3.connect('easyshop.db')
        cursor = conn.cursor()
        cursor.execute('SELECT seller_id, title FROM products WHERE id = ?', (product_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            try:
                bot.send_message(result[0], f'❌ Ваш товар "{result[1]}" отклонен.')
            except:
                pass

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    # Создаём таблицу temp_sell если нет
    conn = sqlite3.connect('easyshop.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS temp_sell (
            user_id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            price INTEGER,
            category TEXT
        )
    ''')
    conn.commit()
    conn.close()
    
    print("=" * 40)
    print("🚀 БОТ ЗАПУЩЕН")
    print("=" * 40)
    print(f"👑 Админы: {', '.join(ADMINS)}")
    print("=" * 40)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
