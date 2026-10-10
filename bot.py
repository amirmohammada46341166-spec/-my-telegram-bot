from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from aiohttp import web
import asyncio

TOKEN = "8965190209:AAEI62bucEHeQwAu2WS-cB0mKHV3hZS08y4"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("دریافت کانفیگ تست", callback_data='get_config')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("سلام! برای دریافت کانفیگ روی دکمه زیر بزن:", reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'get_config':
        fake_config = "vless://test-config-123456@1.2.3.4:443?type=tcp#MyTestConfig"
        await query.edit_message_text(text=f"این کانفیگ تستی شماست:\n\n{fake_config}")

async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    web_app = web.Application()
    web_app.router.add_get('/', handle)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    print("Bot and Web Server are running...")
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())
