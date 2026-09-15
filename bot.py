import os

import psycopg2
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    error
)

from telegram.request import HTTPXRequest

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)


# =========================
# LOAD ENVIRONMENT
# =========================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")


# =========================
# CONVERSATION STEPS
# =========================

NAME, EMAIL, PHONE, PASSWORD, LOGIN_EMAIL, LOGIN_PASSWORD = range(6)


# =========================
# DATABASE
# =========================

def get_db_connection():

    return psycopg2.connect(
        host="aws-0-us-west-2.pooler.supabase.com",
        port=5432,
        database="postgres",
        user="postgres.nawgocxwoxmuwshkfbue",
        password=SUPABASE_DB_PASSWORD
    )


# =========================
# TEMPORARY REGISTRATION STORAGE
# =========================

registration_data = {}


# =========================
# PROMPT MESSAGE STORAGE
# =========================

prompt_messages = {}


# =========================
# DATABASE USER FUNCTIONS
# =========================

def get_user_by_telegram_id(telegram_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            telegram_id,
            name,
            email,
            phone,
            password
        FROM users
        WHERE telegram_id = %s;
        """,
        (telegram_id,)
    )

    row = cursor.fetchone()

    cursor.close()
    connection.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "telegram_id": row[1],
        "name": row[2],
        "email": row[3],
        "phone": row[4],
        "password": row[5]
    }


def get_user_by_email_and_password(email, password):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            telegram_id,
            name,
            email,
            phone,
            password
        FROM users
        WHERE email = %s
        AND password = %s;
        """,
        (email, password)
    )

    row = cursor.fetchone()

    cursor.close()
    connection.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "telegram_id": row[1],
        "name": row[2],
        "email": row[3],
        "phone": row[4],
        "password": row[5]
    }


def create_user(name, email, phone, password, telegram_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO users (
            telegram_id,
            name,
            email,
            phone,
            password
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (
            telegram_id,
            name,
            email,
            phone,
            password
        )
    )

    user_id = cursor.fetchone()[0]

    connection.commit()

    cursor.close()
    connection.close()

    return user_id


# =========================
# CREATE DEMO WALLETS
# =========================

def create_wallets(user_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO wallets (
            user_id,
            solana_address,
            solana_balance,
            ethereum_address,
            ethereum_balance,
            bitcoin_address,
            bitcoin_balance
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        );
        """,
        (
            user_id,

            "4XCyfvPo8d2xkqkDqSKAKfYkAZiQZBU3UxvNeDuzgcZi",
            0.00,

            "0xEf6ea136d7846c35e0F7148D724Fa79B4190d84a",
            0.00,

            "bc1qcpz67zmdk620quumk48ewxnrqjhz43upq4llev",
            0.00
        )
    )

    connection.commit()

    cursor.close()
    connection.close()


# =========================
# GET USER WALLETS
# =========================

def get_user_wallets(user_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            solana_address,
            solana_balance,
            ethereum_address,
            ethereum_balance,
            bitcoin_address,
            bitcoin_balance
        FROM wallets
        WHERE user_id = %s
        LIMIT 1;
        """,
        (user_id,)
    )

    row = cursor.fetchone()

    cursor.close()
    connection.close()

    if row is None:

        return {
            "solana_address": "",
            "solana_balance": 0,
            "ethereum_address": "",
            "ethereum_balance": 0,
            "bitcoin_address": "",
            "bitcoin_balance": 0
        }

    return {
        "solana_address": row[0],
        "solana_balance": row[1],
        "ethereum_address": row[2],
        "ethereum_balance": row[3],
        "bitcoin_address": row[4],
        "bitcoin_balance": row[5]
    }


# =========================
# MESSAGE CLEANUP
# =========================

async def delete_message(message):

    if message is None:
        return

    try:
        await message.delete()
    except Exception:
        pass


async def delete_prompt(bot, chat_id):

    message_id = prompt_messages.get(chat_id)

    if not message_id:
        return

    try:

        await bot.delete_message(
            chat_id=chat_id,
            message_id=message_id
        )

    except Exception:
        pass

    prompt_messages.pop(
        chat_id,
        None
    )


async def send_prompt(update, text):

    message = await update.effective_chat.send_message(text)

    chat_id = update.effective_chat.id

    prompt_messages[chat_id] = message.message_id

    return message


# =========================
# SAFE MESSAGE EDIT
# =========================

async def safe_edit_message(
    query,
    text,
    reply_markup=None,
    parse_mode=None
):

    try:

        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

    except error.BadRequest as e:

        if "Message is not modified" in str(e):

            return

        raise


# =========================
# KEYBOARDS
# =========================

def main_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "Login",
                callback_data="login"
            ),
            InlineKeyboardButton(
                "Create Account",
                callback_data="create_account"
            ),
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def logout_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "Logout",
                callback_data="logout"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# WALLET DISPLAY
# =========================

def wallet_dashboard(user):

    wallets = get_user_wallets(user["id"])

    return (
        "Hey Dear welcome\n\n"

        f"Name; {user['name']}\n"
        f"Email; {user['email']}\n\n"

        "You can now make a deposit inside any of your Aether wallet\n\n"

        "Solana · 🅴\n"
        f"<code>{wallets['solana_address']}</code>\n"
        "(Tap to copy)\n"
        f"Balance: <code>{wallets['solana_balance']:.2f}</code> SOL\n\n"

        "Ethereum · 🅴\n"
        f"<code>{wallets['ethereum_address']}</code>\n"
        "(Tap to copy)\n"
        f"Balance: <code>{wallets['ethereum_balance']:.2f}</code> ETH\n\n"

        "Bitcoin · 🅴\n"
        f"<code>{wallets['bitcoin_address']}</code>\n"
        "(Tap to copy)\n"
        f"Balance: <code>{wallets['bitcoin_balance']:.2f}</code> BTC"
    )


# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    telegram_id = update.effective_user.id
    chat_id = update.effective_chat.id

    registration_data.pop(
        telegram_id,
        None
    )

    context.user_data.pop(
        "login_email",
        None
    )

    prompt_messages.pop(
        chat_id,
        None
    )

    await update.message.reply_text(
        "Welcome to Aether.\n\n"
        "Your gateway to decentralized coordination. "
        "Select an option below to begin.",
        reply_markup=main_menu()
    )


# =========================
# CREATE ACCOUNT
# =========================

async def create_account(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    telegram_id = update.effective_user.id
    chat_id = update.effective_chat.id

    existing_user = get_user_by_telegram_id(
        telegram_id
    )

    if existing_user:

        await safe_edit_message(
            query,
            "An Aether account already exists for this Telegram account.\n\n"
            "Please use Login instead.",
            reply_markup=main_menu()
        )

        return ConversationHandler.END

    registration_data[telegram_id] = {}

    prompt_messages.pop(
        chat_id,
        None
    )

    message = await query.edit_message_text(
        "Create Account\n\n"
        "Let's create your Aether account.\n\n"
        "Please enter your full name:"
    )

    prompt_messages[chat_id] = message.message_id

    return NAME


# =========================
# GET NAME
# =========================

async def get_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    telegram_id = update.effective_user.id
    chat_id = update.effective_chat.id

    name = update.message.text.strip()

    registration_data.setdefault(
        telegram_id,
        {}
    )

    registration_data[telegram_id]["name"] = name

    await delete_message(update.message)

    await delete_prompt(
        context.bot,
        chat_id
    )

    await send_prompt(
        update,
        "Great.\n\n"
        "Now enter your email address:"
    )

    return EMAIL


# =========================
# GET EMAIL
# =========================

async def get_email(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    telegram_id = update.effective_user.id
    chat_id = update.effective_chat.id

    email = update.message.text.strip()

    registration_data.setdefault(
        telegram_id,
        {}
    )

    registration_data[telegram_id]["email"] = email

    await delete_message(update.message)

    await delete_prompt(
        context.bot,
        chat_id
    )

    await send_prompt(
        update,
        "Email received.\n\n"
        "Now enter your phone number:"
    )

    return PHONE


# =========================
# GET PHONE
# =========================

async def get_phone(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    telegram_id = update.effective_user.id
    chat_id = update.effective_chat.id

    phone = update.message.text.strip()

    registration_data.setdefault(
        telegram_id,
        {}
    )

    registration_data[telegram_id]["phone"] = phone

    await delete_message(update.message)

    await delete_prompt(
        context.bot,
        chat_id
    )

    await send_prompt(
        update,
        "Phone number received.\n\n"
        "Now create a password:"
    )

    return PASSWORD


# =========================
# GET PASSWORD
# =========================

async def get_password(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    telegram_id = update.effective_user.id
    chat_id = update.effective_chat.id

    password = update.message.text.strip()

    registration_data.setdefault(
        telegram_id,
        {}
    )

    registration_data[telegram_id]["password"] = password

    await delete_message(update.message)

    await delete_prompt(
        context.bot,
        chat_id
    )

    data = registration_data[telegram_id]

    try:

        user_id = create_user(
            name=data["name"],
            email=data["email"],
            phone=data["phone"],
            password=data["password"],
            telegram_id=telegram_id
        )

        create_wallets(user_id)

        new_user = get_user_by_telegram_id(
            telegram_id
        )

    except psycopg2.errors.UniqueViolation:

        await update.effective_chat.send_message(
            "❌ An account with that email or Telegram account already exists.\n\n"
            "Please use /start and try again."
        )

        registration_data.pop(
            telegram_id,
            None
        )

        return ConversationHandler.END

    except Exception as db_error:

        print(
            "Database error during registration:",
            db_error
        )

        await update.effective_chat.send_message(
            "❌ Something went wrong while creating your account.\n\n"
            "Please try again later."
        )

        registration_data.pop(
            telegram_id,
            None
        )

        return ConversationHandler.END

    registration_data.pop(
        telegram_id,
        None
    )

    await update.effective_chat.send_message(
        "Account created successfully.\n\n"
        f"Name: {new_user['name']}\n"
        f"Email: {new_user['email']}\n"
        f"Phone: {new_user['phone']}\n\n"
        "Welcome to Aether."
    )

    await update.effective_chat.send_message(
        wallet_dashboard(new_user),
        parse_mode="HTML",
        reply_markup=logout_menu()
    )

    return ConversationHandler.END


# =========================
# LOGIN
# =========================

async def login(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    chat_id = update.effective_chat.id

    # Clear previous login data.
    context.user_data.pop(
        "login_email",
        None
    )

    prompt_messages.pop(
        chat_id,
        None
    )

    message = await query.edit_message_text(
        "Login\n\n"
        "Please enter your email address:"
    )

    prompt_messages[chat_id] = message.message_id

    return LOGIN_EMAIL


# =========================
# GET LOGIN EMAIL
# =========================

async def get_login_email(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat_id = update.effective_chat.id

    email = update.message.text.strip()

    # Store email inside this user's conversation data.
    context.user_data["login_email"] = email

    await delete_message(update.message)

    await delete_prompt(
        context.bot,
        chat_id
    )

    await send_prompt(
        update,
        "Email received.\n\n"
        "Please enter your password:"
    )

    return LOGIN_PASSWORD


# =========================
# GET LOGIN PASSWORD
# =========================

async def get_login_password(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat_id = update.effective_chat.id

    password = update.message.text.strip()

    email = context.user_data.get(
        "login_email"
    )

    await delete_message(update.message)

    await delete_prompt(
        context.bot,
        chat_id
    )

    print(
        f"LOGIN ATTEMPT | email={email} | "
        f"password_length={len(password)}"
    )

    try:

        logged_in_user = get_user_by_email_and_password(
            email,
            password
        )

    except Exception as db_error:

        print(
            "Database error during login:",
            db_error
        )

        context.user_data.pop(
            "login_email",
            None
        )

        await update.effective_chat.send_message(
            "❌ Something went wrong while logging in.\n\n"
            "Please try again later."
        )

        return ConversationHandler.END

    context.user_data.pop(
        "login_email",
        None
    )

    # =========================
    # LOGIN FAILED
    # =========================

    if logged_in_user is None:

        print(
            "LOGIN FAILED: email/password did not match."
        )

        await update.effective_chat.send_message(
            "❌ Invalid email or password.\n\n"
            "Please use /start to try again."
        )

        return ConversationHandler.END

    # =========================
    # LOGIN SUCCESSFUL
    # =========================

    print(
        f"LOGIN SUCCESSFUL: {logged_in_user['email']}"
    )

    await update.effective_chat.send_message(
        "Login successful.\n\n"
        f"Welcome back, {logged_in_user['name']}."
    )

    await update.effective_chat.send_message(
        wallet_dashboard(logged_in_user),
        parse_mode="HTML",
        reply_markup=logout_menu()
    )

    return ConversationHandler.END


# =========================
# BUTTON HANDLER
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    telegram_id = update.effective_user.id

    if query.data == "logout":

        chat_id = update.effective_chat.id

        registration_data.pop(
            telegram_id,
            None
        )

        context.user_data.pop(
            "login_email",
            None
        )

        prompt_messages.pop(
            chat_id,
            None
        )

        await safe_edit_message(
            query,
            "You have been logged out.\n\n"
            "Use /start to return to Aether.",
            reply_markup=main_menu()
        )


# =========================
# ERROR HANDLER
# =========================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    print(
        "Exception while handling update:",
        context.error
    )


# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:

        raise ValueError(
            "BOT_TOKEN was not found in the .env file."
        )

    if not SUPABASE_DB_PASSWORD:

        raise ValueError(
            "SUPABASE_DB_PASSWORD was not found in the .env file."
        )

    # =========================
    # TELEGRAM CONNECTION
    # =========================

    request = HTTPXRequest(
        connect_timeout=30,
        read_timeout=30,
        write_timeout=30,
        pool_timeout=30,
        httpx_kwargs={
            "trust_env": False
        },
    )

    # =========================
    # CREATE APPLICATION
    # =========================

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .build()
    )

    # =========================
    # /START
    # =========================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # =========================
    # REGISTRATION
    # =========================

    registration_handler = ConversationHandler(

        entry_points=[
            CallbackQueryHandler(
                create_account,
                pattern="^create_account$"
            )
        ],

        states={

            NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_name
                )
            ],

            EMAIL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_email
                )
            ],

            PHONE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_phone
                )
            ],

            PASSWORD: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_password
                )
            ],
        },

        fallbacks=[],

        per_user=True,

        per_chat=True,

        per_message=False,
    )

    app.add_handler(
        registration_handler
    )

    # =========================
    # LOGIN
    # =========================

    login_handler = ConversationHandler(

        entry_points=[
            CallbackQueryHandler(
                login,
                pattern="^login$"
            )
        ],

        states={

            LOGIN_EMAIL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_login_email
                )
            ],

            LOGIN_PASSWORD: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_login_password
                )
            ],
        },

        fallbacks=[],

        per_user=True,

        per_chat=True,

        per_message=False,
    )

    app.add_handler(
        login_handler
    )

    # =========================
    # LOGOUT BUTTON
    # =========================

    app.add_handler(
        CallbackQueryHandler(
            button_handler,
            pattern="^logout$"
        )
    )

    # =========================
    # ERROR HANDLER
    # =========================

    app.add_error_handler(
        error_handler
    )

    # =========================
    # START BOT
    # =========================

    print("Aether bot is running...")

    app.run_polling()


# =========================
# RUN
# =========================

if __name__ == "__main__":
    main()

