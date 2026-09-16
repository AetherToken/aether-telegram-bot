import os

from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    error,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from telegram.request import HTTPXRequest

from database import (
    get_user_by_telegram_id,
    get_user_by_email_and_password,
    create_user,
    get_wallet_status,
    get_wallet,
    create_wallet,
)


# ==================================================
# ENVIRONMENT
# ==================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


# ==================================================
# STATES
# ==================================================

REGISTER_NAME = "register_name"
REGISTER_EMAIL = "register_email"
REGISTER_PHONE = "register_phone"
REGISTER_PASSWORD = "register_password"

LOGIN_EMAIL = "login_email"
LOGIN_PASSWORD = "login_password"


# ==================================================
# MESSAGE MANAGEMENT
# ==================================================

async def delete_user_message(update: Update):
    try:
        if update.message:
            await update.message.delete()
    except Exception:
        pass


async def delete_previous_bot_message(context):
    chat_id = context.user_data.get("chat_id")
    message_id = context.user_data.get("bot_message_id")

    if not chat_id or not message_id:
        return

    try:
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=message_id,
        )
    except Exception:
        pass

    context.user_data.pop("bot_message_id", None)


async def send_clean_message(
    update,
    context,
    text,
    reply_markup=None,
    parse_mode=None,
):
    """
    Edit the existing bot message instead of creating
    duplicate bot prompts.

    If no usable bot message exists,
    send a new message.
    """

    chat_id = context.user_data.get(
        "chat_id",
        update.effective_chat.id,
    )

    message_id = context.user_data.get(
        "bot_message_id"
    )

    # ----------------------------------------------
    # Try to edit existing bot message
    # ----------------------------------------------

    if message_id:

        try:

            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )

            return

        except error.BadRequest as e:

            if "Message is not modified" in str(e):
                return

        except Exception:
            pass

    # ----------------------------------------------
    # Send a new message if editing failed
    # ----------------------------------------------

    message = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )

    context.user_data["chat_id"] = chat_id
    context.user_data["bot_message_id"] = (
        message.message_id
    )


async def edit_current_message(
    query,
    context,
    text,
    reply_markup=None,
    parse_mode=None,
):
    try:

        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )

        context.user_data["chat_id"] = (
            query.message.chat_id
        )

        context.user_data["bot_message_id"] = (
            query.message.message_id
        )

    except error.BadRequest as e:

        if "Message is not modified" in str(e):
            return

        raise


# ==================================================
# MAIN MENU
# ==================================================

def main_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "🔐 Login",
                callback_data="login",
            ),
            InlineKeyboardButton(
                "📝 Create Account",
                callback_data="register",
            ),
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# ==================================================
# START
# ==================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    context.user_data.clear()

    context.user_data["chat_id"] = (
        update.effective_chat.id
    )

    message = await update.message.reply_text(
        "✨ <b>Welcome to AetherCipherBot</b>\n\n"
        "Your secure digital wallet platform.\n\n"
        "Please choose an option below:",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )

    context.user_data["bot_message_id"] = (
        message.message_id
    )


# ==================================================
# LOGIN START
# ==================================================

async def start_login(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    context.user_data.clear()

    context.user_data["chat_id"] = (
        query.message.chat_id
    )

    context.user_data["bot_message_id"] = (
        query.message.message_id
    )

    context.user_data["state"] = LOGIN_EMAIL

    await edit_current_message(
        query,
        context,
        "🔐 <b>Login</b>\n\n"
        "Please enter your email address:",
        parse_mode="HTML",
    )


# ==================================================
# REGISTRATION START
# ==================================================

async def start_registration(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    context.user_data.clear()

    context.user_data["chat_id"] = (
        query.message.chat_id
    )

    context.user_data["bot_message_id"] = (
        query.message.message_id
    )

    context.user_data["state"] = REGISTER_NAME

    await edit_current_message(
        query,
        context,
        "📝 <b>Create Account</b>\n\n"
        "Please enter your full name:",
        parse_mode="HTML",
    )


# ==================================================
# HANDLE TEXT
# ==================================================

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    state = context.user_data.get("state")

    if state is None:
        return

    text = update.message.text.strip()

    # Delete user's message immediately.
    await delete_user_message(update)


    # ==================================================
    # REGISTER NAME
    # ==================================================

    if state == REGISTER_NAME:

        if not text:

            await send_clean_message(
                update,
                context,
                "❌ Please enter your full name.",
            )

            return

        context.user_data["name"] = text
        context.user_data["state"] = REGISTER_EMAIL

        await send_clean_message(
            update,
            context,
            "📧 Now enter your email address:",
        )

        return


    # ==================================================
    # REGISTER EMAIL
    # ==================================================

    if state == REGISTER_EMAIL:

        email = text.lower()

        if "@" not in email or "." not in email:

            await send_clean_message(
                update,
                context,
                "❌ Please enter a valid email address.",
            )

            return

        context.user_data["email"] = email
        context.user_data["state"] = REGISTER_PHONE

        await send_clean_message(
            update,
            context,
            "📱 Enter your phone number:",
        )

        return


    # ==================================================
    # REGISTER PHONE
    # ==================================================

    if state == REGISTER_PHONE:

        if not text:

            await send_clean_message(
                update,
                context,
                "❌ Please enter your phone number.",
            )

            return

        context.user_data["phone"] = text
        context.user_data["state"] = REGISTER_PASSWORD

        await send_clean_message(
            update,
            context,
            "🔑 Create a password:",
        )

        return


    # ==================================================
    # REGISTER PASSWORD
    # ==================================================

    if state == REGISTER_PASSWORD:

        password = text

        # Delete the password prompt immediately
        # after the user submits the password.
        await delete_previous_bot_message(
            context
        )

        if len(password) < 4:

            context.user_data["bot_message_id"] = None

            await send_clean_message(
                update,
                context,
                "❌ Password must be at least 4 characters.",
            )

            return

        telegram_id = update.effective_user.id

        name = context.user_data.get("name")
        email = context.user_data.get("email")
        phone = context.user_data.get("phone")

        try:

            existing_user = get_user_by_telegram_id(
                telegram_id
            )

            if existing_user is not None:

                context.user_data.clear()

                context.user_data["chat_id"] = (
                    update.effective_chat.id
                )

                await send_clean_message(
                    update,
                    context,
                    "❌ An account already exists for "
                    "this Telegram account.\n\n"
                    "Use /start to login.",
                    reply_markup=main_menu(),
                )

                return

            user_id = create_user(
                telegram_id=telegram_id,
                name=name,
                email=email,
                phone=phone,
                password=password,
            )

            create_wallet(user_id)

        except Exception as db_error:

            print(
                "Registration database error:",
                db_error,
            )

            context.user_data.clear()

            context.user_data["chat_id"] = (
                update.effective_chat.id
            )

            await send_clean_message(
                update,
                context,
                "❌ Something went wrong while "
                "creating your account.\n\n"
                "Please try again later.",
            )

            return

        context.user_data.clear()

        context.user_data["user_id"] = user_id
        context.user_data["name"] = name
        context.user_data["logged_in"] = True
        context.user_data["chat_id"] = (
            update.effective_chat.id
        )

        await send_clean_message(
            update,
            context,
            "🎉 <b>Account Created Successfully</b>\n\n"
            f"Welcome, <b>{name}</b>.",
            parse_mode="HTML",
        )

        await show_wallet_status(
            update,
            context,
            user_id,
        )

        return


    # ==================================================
    # LOGIN EMAIL
    # ==================================================

    if state == LOGIN_EMAIL:

        email = text.lower()

        if "@" not in email or "." not in email:

            await send_clean_message(
                update,
                context,
                "❌ Please enter a valid email address.",
            )

            return

        context.user_data["login_email"] = email
        context.user_data["state"] = LOGIN_PASSWORD

        await send_clean_message(
            update,
            context,
            "🔑 Enter your password:",
        )

        return


    # ==================================================
    # LOGIN PASSWORD
    # ==================================================

    if state == LOGIN_PASSWORD:

        password = text

        # Delete the password prompt immediately
        # after the user submits the password.
        await delete_previous_bot_message(
            context
        )

        email = context.user_data.get(
            "login_email"
        )

        try:

            user = get_user_by_email_and_password(
                email,
                password,
            )

        except Exception as db_error:

            print(
                "Login database error:",
                db_error,
            )

            context.user_data.clear()

            context.user_data["chat_id"] = (
                update.effective_chat.id
            )

            await send_clean_message(
                update,
                context,
                "❌ Something went wrong while "
                "logging in.\n\n"
                "Please try again later.",
            )

            return

        if user is None:

            context.user_data.clear()

            context.user_data["chat_id"] = (
                update.effective_chat.id
            )

            await send_clean_message(
                update,
                context,
                "❌ <b>Invalid email or password.</b>\n\n"
                "Use /start to try again.",
                reply_markup=main_menu(),
                parse_mode="HTML",
            )

            return

        context.user_data.clear()

        context.user_data["user_id"] = user["id"]
        context.user_data["name"] = user["name"]
        context.user_data["logged_in"] = True
        context.user_data["chat_id"] = (
            update.effective_chat.id
        )

        await send_clean_message(
            update,
            context,
            "✅ <b>Login successful</b>\n\n"
            f"Welcome back, <b>{user['name']}</b>.",
            parse_mode="HTML",
        )

        await show_wallet_status(
            update,
            context,
            user["id"],
        )

        return


# ==================================================
# WALLET STATUS
# ==================================================

async def show_wallet_status(
    update,
    context,
    user_id,
):

    status = get_wallet_status(user_id)


    # ==================================================
    # PENDING
    # ==================================================

    if status == "pending":

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔄 Check Wallet Status",
                    callback_data="check_wallet",
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data="back_main",
                )
            ],
        ]

        text = (
            "⏳ <b>Wallet Assignment Pending</b>\n\n"
            f"Hello, <b>{context.user_data.get('name')}</b>.\n\n"
            "Your account has been created successfully.\n\n"
            "Your wallet has not been assigned yet.\n\n"
            "Please wait while your wallet is being prepared.\n\n"
            "You can check the status using the button below."
        )

        await send_clean_message(
            update,
            context,
            text,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
            parse_mode="HTML",
        )

        return


    # ==================================================
    # ACTIVE
    # ==================================================

    if status == "active":

        await show_wallet(
            update,
            context,
            user_id,
        )

        return


    await send_clean_message(
        update,
        context,
        "❌ Your wallet status could not be determined.\n\n"
        "Please contact the administrator.",
    )


# ==================================================
# WALLET
# ==================================================

async def show_wallet(
    update,
    context,
    user_id,
):

    wallet = get_wallet(user_id)

    if wallet is None:

        await send_clean_message(
            update,
            context,
            "❌ Your wallet has not been created yet.\n\n"
            "Please contact the administrator.",
        )

        return


    keyboard = [
        [
            InlineKeyboardButton(
                "💰 Deposit",
                callback_data="deposit",
            ),
            InlineKeyboardButton(
                "↗️ Withdrawal",
                callback_data="withdrawal",
            ),
        ],
        [
            InlineKeyboardButton(
                "🚪 Logout",
                callback_data="logout",
            )
        ],
    ]


    text = (
        "💳 <b>AetherCipher Wallet</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"👤 <b>User:</b> "
        f"{context.user_data.get('name', 'Member')}\n\n"

        "🟣 <b>Solana</b>\n"
        f"Balance: {wallet['solana_balance']}\n\n"

        "🔷 <b>Ethereum</b>\n"
        f"Balance: {wallet['ethereum_balance']}\n\n"

        "🟠 <b>Bitcoin</b>\n"
        f"Balance: {wallet['bitcoin_balance']}\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "Select an option below."
    )


    await send_clean_message(
        update,
        context,
        text,
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
        parse_mode="HTML",
    )


# ==================================================
# CHECK WALLET STATUS
# ==================================================

async def check_wallet_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    user_id = context.user_data.get(
        "user_id"
    )

    if not user_id:

        await edit_current_message(
            query,
            context,
            "❌ Your session has expired.\n\n"
            "Please use /start to login again.",
            reply_markup=main_menu(),
        )

        return


    status = get_wallet_status(user_id)


    if status == "pending":

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔄 Check Again",
                    callback_data="check_wallet",
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data="back_main",
                )
            ],
        ]

        await edit_current_message(
            query,
            context,
            "⏳ <b>Wallet Still Pending</b>\n\n"
            "Your wallet has not been assigned yet.\n\n"
            "Please check again later.",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
            parse_mode="HTML",
        )

        return


    if status == "active":

        await edit_current_message(
            query,
            context,
            "✅ <b>Wallet Assigned</b>\n\n"
            "Your wallet is now active.",
            parse_mode="HTML",
        )

        await show_wallet(
            update,
            context,
            user_id,
        )

        return


    await edit_current_message(
        query,
        context,
        "❌ Unable to determine wallet status.",
    )


# ==================================================
# BACK TO MAIN
# ==================================================

async def back_main(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    context.user_data.clear()

    context.user_data["chat_id"] = (
        query.message.chat_id
    )

    context.user_data["bot_message_id"] = (
        query.message.message_id
    )

    await edit_current_message(
        query,
        context,
        "✨ <b>AetherCipherBot</b>\n\n"
        "Please choose an option below:",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


# ==================================================
# DEPOSIT
# ==================================================

async def deposit(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    user_id = context.user_data.get(
        "user_id"
    )

    if not user_id:

        await edit_current_message(
            query,
            context,
            "❌ Your session has expired.\n\n"
            "Please use /start to login again.",
            reply_markup=main_menu(),
        )

        return


    wallet = get_wallet(user_id)

    if wallet is None:

        await edit_current_message(
            query,
            context,
            "❌ Wallet information is unavailable.",
        )

        return


    keyboard = [
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="back_wallet",
            )
        ]
    ]


    text = (
        "💰 <b>Deposit</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "Send funds only to the corresponding "
        "wallet address.\n\n"

        "🟣 <b>Solana</b>\n"
        f"<code>{wallet['solana_address'] or 'Not assigned'}</code>\n\n"

        "🔷 <b>Ethereum</b>\n"
        f"<code>{wallet['ethereum_address'] or 'Not assigned'}</code>\n\n"

        "🟠 <b>Bitcoin</b>\n"
        f"<code>{wallet['bitcoin_address'] or 'Not assigned'}</code>\n\n"

        "⚠️ Please verify the network and address "
        "before sending."
    )


    await edit_current_message(
        query,
        context,
        text,
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
        parse_mode="HTML",
    )


# ==================================================
# WITHDRAWAL
# ==================================================

async def withdrawal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="back_wallet",
            )
        ]
    ]


    await edit_current_message(
        query,
        context,
        "↗️ <b>Withdrawal</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Sorry, withdrawal is not available "
        "at the moment.",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
        parse_mode="HTML",
    )


# ==================================================
# BACK TO WALLET
# ==================================================

async def back_wallet(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    user_id = context.user_data.get(
        "user_id"
    )

    if not user_id:

        await edit_current_message(
            query,
            context,
            "❌ Your session has expired.\n\n"
            "Please use /start to login again.",
            reply_markup=main_menu(),
        )

        return


    await show_wallet(
        update,
        context,
        user_id,
    )


# ==================================================
# LOGOUT
# ==================================================

async def logout(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    context.user_data.clear()

    context.user_data["chat_id"] = (
        query.message.chat_id
    )

    context.user_data["bot_message_id"] = (
        query.message.message_id
    )

    await edit_current_message(
        query,
        context,
        "🚪 <b>You have been logged out.</b>\n\n"
        "Please choose an option below:",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


# ==================================================
# BUTTON HANDLER
# ==================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return


    if query.data == "login":
        await start_login(update, context)
        return


    if query.data == "register":
        await start_registration(update, context)
        return


    if query.data == "check_wallet":
        await check_wallet_status(update, context)
        return


    if query.data == "back_main":
        await back_main(update, context)
        return


    if query.data == "deposit":
        await deposit(update, context)
        return


    if query.data == "withdrawal":
        await withdrawal(update, context)
        return


    if query.data == "back_wallet":
        await back_wallet(update, context)
        return


    if query.data == "logout":
        await logout(update, context)
        return


# ==================================================
# ERROR HANDLER
# ==================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    print(
        "Exception while handling update:",
        context.error,
    )


# ==================================================
# MAIN
# ==================================================

def main():

    request = HTTPXRequest(
        connect_timeout=30,
        read_timeout=30,
        write_timeout=30,
        pool_timeout=30,
        httpx_kwargs={
            "trust_env": False
        },
    )


    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .build()
    )


    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            button_handler,
            pattern=(
                "^(login|register|check_wallet|"
                "back_main|deposit|withdrawal|"
                "back_wallet|logout)$"
            ),
        )
    )


    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )


    app.add_error_handler(
        error_handler
    )


    print(
        "AetherCipherBot is running..."
    )


    app.run_polling()


if __name__ == "__main__":
    main()
