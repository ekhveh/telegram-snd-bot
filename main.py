# وارد کردن کتابخانه‌های مورد نیاز
import telebot  # برای ارتباط با بات تلگرام
from sqlalchemy import create_engine, Column, Integer, String, Boolean  # برای ساخت پایگاه داده
from sqlalchemy.orm import declarative_base, sessionmaker  # ORM برای ارتباط شی‌گرا با دیتابیس
from werkzeug.security import generate_password_hash, check_password_hash  # برای هش کردن رمز عبور
import os  # برای دسترسی به متغیرهای محیطی
from flask import Flask  # برای راه‌اندازی وب سرور فیک (برای فریب Render)
import threading  # برای اجرای همزمان وب‌سرور و بات

# ایجاد یک وب‌سرور ساختگی با Flask برای فریب دادن Render که فکر کند برنامه ما Web Service است
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"  # متن ساده‌ای که هنگام بازدید از URL نمایش داده می‌شود

# تابعی برای اجرای وب‌سرور روی پورتی که Render مشخص می‌کند
def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# گرفتن توکن بات تلگرام و آدرس پایگاه داده از متغیرهای محیطی
TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# ساخت بات تلگرام و ارتباط با پایگاه داده
bot = telebot.TeleBot(TOKEN)
engine = create_engine(DATABASE_URL)  # ایجاد اتصال با دیتابیس
Session = sessionmaker(bind=engine)  # ساخت سشن برای کار با دیتابیس
Base = declarative_base()  # پایه‌ی ORM برای تعریف مدل‌ها

# تعریف جدول کاربران
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)  # کلید اصلی
    telegram_id = Column(Integer, unique=True)  # آیدی تلگرام کاربر
    username = Column(String, unique=True)  # نام کاربری انتخابی
    password_hash = Column(String)  # رمز عبور هش‌شده
    is_logged_in = Column(Boolean, default=False)  # وضعیت ورود کاربر

# ساخت جدول‌ها در دیتابیس (در صورت نبودن)
Base.metadata.create_all(engine)

# هندلر دستور /start
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "سلام! با /signup ثبت‌نام یا با /login وارد شوید.")

# هندلر دستور /signup برای شروع ثبت‌نام
@bot.message_handler(commands=['signup'])
def signup(message):
    msg = bot.reply_to(message, "نام کاربری:")
    bot.register_next_step_handler(msg, process_username)  # مرحله بعد: گرفتن رمز عبور

# مرحله دوم ثبت‌نام: دریافت رمز عبور
def process_username(message):
    username = message.text
    msg = bot.reply_to(message, "رمز عبور:")
    bot.register_next_step_handler(msg, lambda m: save_user(m, username))  # ارسال به تابع ذخیره کاربر

# ذخیره‌سازی اطلاعات کاربر در دیتابیس
def save_user(message, username):
    password = message.text
    session = Session()
    if session.query(User).filter_by(username=username).first():
        bot.reply_to(message, "این نام کاربری قبلاً ثبت شده.")
    else:
        new_user = User(
            telegram_id=message.from_user.id,
            username=username,
            password_hash=generate_password_hash(password),  # هش کردن رمز عبور
            is_logged_in=True
        )
        session.add(new_user)
        session.commit()
        bot.reply_to(message, "ثبت‌نام با موفقیت انجام شد.")
    session.close()

# هندلر دستور /login برای ورود کاربران
@bot.message_handler(commands=['login'])
def login(message):
    msg = bot.reply_to(message, "نام کاربری:")
    bot.register_next_step_handler(msg, process_login_username)

# مرحله دوم ورود: گرفتن رمز عبور
def process_login_username(message):
    username = message.text
    msg = bot.reply_to(message, "رمز عبور:")
    bot.register_next_step_handler(msg, lambda m: check_login(m, username))

# بررسی اطلاعات ورود
def check_login(message, username):
    password = message.text
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):  # بررسی صحت رمز عبور
        user.is_logged_in = True
        session.commit()
        bot.reply_to(message, "ورود موفقیت‌آمیز بود.")
    else:
        bot.reply_to(message, "نام کاربری یا رمز عبور اشتباه است.")
    session.close()

# دستور /image: ارسال عکس طبیعت در صورتی که کاربر وارد شده باشد
@bot.message_handler(commands=['image'])
def send_image(message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if user and user.is_logged_in:
        bot.send_photo(message.chat.id, photo='https://picsum.photos/600/400')
    else:
        bot.reply_to(message, "لطفاً ابتدا وارد شوید (/login)")
    session.close()

# دستور /music: ارسال آهنگ سنتی اگر کاربر وارد شده باشد
@bot.message_handler(commands=['music'])
def send_music(message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if user and user.is_logged_in:
        bot.send_audio(message.chat.id, audio=open('music.mp3', 'rb'))  # فایل music.mp3 باید در ریشه پروژه باشد
    else:
        bot.reply_to(message, "لطفاً ابتدا وارد شوید (/login)")
    session.close()

# شروع هم‌زمان وب‌سرور و بات تلگرام
if __name__ == "__main__":
    threading.Thread(target=run_web).start()  # اجرای Flask در بک‌گراند
    bot.infinity_polling()  # اجرای همیشگی بات
