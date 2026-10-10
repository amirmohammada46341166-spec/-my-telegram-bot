import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8965190209:AAEI62bucEHeQwAu2WS-cB0mKHV3hZS08y4"
ADMIN_ID = 7049905125
CARD_NUMBER = "5892-1012-5656-8888"
CARD_NAME = "رامین زارع"

def init_db():
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price TEXT, description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configs (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, config TEXT, sold INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_products():
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    p = c.fetchall()
    conn.close()
    return p

def get_product(pid):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id=?", (pid,))
    p = c.fetchone()
    conn.close()
    return p

def get_available_config(pid):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("SELECT * FROM configs WHERE product_id=? AND sold=0 LIMIT 1", (pid,))
    cfg = c.fetchone()
    if cfg:
        c.execute("UPDATE configs SET sold=1 WHERE id=?", (cfg[0],))
        conn.commit()
    conn.close()
    return cfg

def add_order(uid, pid):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("INSERT INTO orders (user_id, product_id) VALUES (?, ?)", (uid, pid))
    oid = c.lastrowid
    conn.commit()
    conn.close()
    return oid

def get_order(oid):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE id=?", (oid,))
    o = c.fetchone()
    conn.close()
    return o

def confirm_order(oid):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("UPDATE orders SET status='confirmed' WHERE id=?", (oid,))
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = get_products()
    if not products:
        await update.message.reply_text("هنوز محصولی اضافه نشده. بعداً مراجعه کن.")
        return
    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(f"{p[1]} - {p[2]}", callback_data=f"product_{p[0]}")])
    await update.message.reply_text("سلام! محصول مورد نظرت رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))

async def product_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pid = int(query.data.split("_")[1])
    product = get_product(pid)
    if not product:
        await query.edit_message_text("محصول پیدا نشد.")
        return
    text = f"🛒 {product[1]}\n💰 قیمت: {product[2]}\n📝 {product[3]}\n\n"
    text += f"مبلغ {product[2]} رو به کارت زیر واریز کن:\n\n💳 {CARD_NUMBER}\n👤 {CARD_NAME}\n\nبعد از واریز، روی دکمه بزن."
    keyboard = [[InlineKeyboardButton("✅ پرداخت کردم", callback_data=f"paid_{pid}")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def payment_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pid = int(query.data.split("_")[1])
    uid = query.from_user.id
    oid = add_order(uid, pid)
    product = get_product(pid)
    admin_text = f"🔔 سفارش جدید #{oid}\n\n👤 {query.from_user.full_name}\n🆔 `{uid}`\n🛒 {product[1]} | {product[2]}\n\nبرای تایید و ارسال کانفیگ، دکمه زیر رو بزن:"
    keyboard = [[InlineKeyboardButton("✅ تایید و ارسال کانفیگ", callback_data=f"confirm_{oid}")]]
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        print(f"خطا در ارسال به ادمین: {e}")
    await query.edit_message_text("✅ سفارش ثبت شد!\n\nمنتظر تایید ادمین باش. بعد از تایید، کانفیگ برات ارسال میشه.")

async def admin_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.answer("شما ادمین نیستید!", show_alert=True)
        return
    oid = int(query.data.split("_")[1])
    order = get_order(oid)
    if not order:
        await query.edit_message_text("سفارش پیدا نشد.")
        return
    if order[3] == 'confirmed':
        await query.edit_message_text("این سفارش قبلاً تایید شده.")
        return
    cfg = get_available_config(order[2])
    if not cfg:
        await query.edit_message_text("❌ کانفیگ موجود نیست! به کاربر اطلاع بده و کانفیگ جدید اضافه کن.")
        return
    confirm_order(oid)
    try:
        await context.bot.send_message(chat_id=order[1], text=f"🎉 سفارش شما تایید شد!\n\n🔑 کانفیگ شما:\n`{cfg[2]}`\n\nموفق باشی!", parse_mode="Markdown")
    except Exception as e:
        print(f"خطا در ارسال به کاربر: {e}")
    await query.edit_message_text(f"✅ سفارش #{oid} تایید شد و کانفیگ ارسال شد.")

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("فرمت: /add_product [نام] [قیمت] [توضیح]\nمثال: /add_product یک‌ماهه 50000 کانفیگ ۳۰ روزه")
        return
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("INSERT INTO products (name, price, description) VALUES (?, ?, ?)", (args[0], args[1], " ".join(args[2:])))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ محصول '{args[0]}' با قیمت {args[1]} اضافه شد.")

async def add_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("فرمت: /add_config [آیدی محصول] [کانفیگ]\nمثال: /add_config 1 vless://...")
        return
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("INSERT INTO configs (product_id, config) VALUES (?, ?)", (int(args[0]), " ".join(args[1:])))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ کانفیگ به محصول {args[0]} اضافه شد.")

async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    products = get_products()
    if not products:
        await update.message.reply_text("محصولی وجود ندارد.")
        return
    text = "📋 محصولات:\n\n"
    for p in products:
        text += f"ID {p[0]} | {p[1]} | {p[2]}\n"
    await update.message.reply_text(text)

async def list_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 20")
    orders = c.fetchall()
    conn.close()
    if not orders:
        await update.message.reply_text("سفارشی نیست.")
        return
    text = "📋 آخرین سفارش‌ها:\n\n"
    for o in orders:
        text += f"#{o[0]} | کاربر {o[1]} | محصول {o[2]} | {o[3]}\n"
    await update.message.reply_text(text)

def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(product_selected, pattern="^product_"))
    app.add_handler(CallbackQueryHandler(payment_done, pattern="^paid_"))
    app.add_handler(CallbackQueryHandler(admin_confirm, pattern="^confirm_"))
    app.add_handler(CommandHandler("add_product", add_product))
    app.add_handler(CommandHandler("add_config", add_config))
    app.add_handler(CommandHandler("list_products", list_products))
    app.add_handler(CommandHandler("list_orders", list_orders))
    print("ربات فروشگاهی روشن شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
