import telebot
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask import Flask
import threading

# راه‌اندازی وب‌سرور ساختگی برای فریب Render
app = Flask(__name__)
@app.route('/')
def index():
    return "Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# تنظیمات بات و پایگاه داده
TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

bot = telebot.TeleBot(TOKEN)
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String, unique=True)
    password_hash = Column(String)
    is_logged_in = Column(Boolean, default=False)

Base.metadata.create_all(engine)

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "سلام! با /signup ثبت‌نام یا با /login وارد شوید.")

@bot.message_handler(commands=['signup'])
def signup(message):
    msg = bot.reply_to(message, "نام کاربری:")
    bot.register_next_step_handler(msg, process_username)

def process_username(message):
    username = message.text
    msg = bot.reply_to(message, "رمز عبور:")
    bot.register_next_step_handler(msg, lambda m: save_user(m, username))

def save_user(message, username):
    password = message.text
    session = Session()
    if session.query(User).filter_by(username=username).first():
        bot.reply_to(message, "این نام کاربری قبلاً ثبت شده.")
    else:
        new_user = User(
            telegram_id=message.from_user.id,
            username=username,
            password_hash=generate_password_hash(password),
            is_logged_in=True
        )
        session.add(new_user)
        session.commit()
        bot.reply_to(message, "ثبت‌نام با موفقیت انجام شد.")
    session.close()

@bot.message_handler(commands=['login'])
def login(message):
    msg = bot.reply_to(message, "نام کاربری:")
    bot.register_next_step_handler(msg, process_login_username)

def process_login_username(message):
    username = message.text
    msg = bot.reply_to(message, "رمز عبور:")
    bot.register_next_step_handler(msg, lambda m: check_login(m, username))

def check_login(message, username):
    password = message.text
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        user.is_logged_in = True
        session.commit()
        bot.reply_to(message, "ورود موفقیت‌آمیز بود.")
    else:
        bot.reply_to(message, "نام کاربری یا رمز عبور اشتباه است.")
    session.close()

@bot.message_handler(commands=['image'])
def send_image(message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if user and user.is_logged_in:
        bot.send_photo(message.chat.id, photo='https://picsum.photos/600/400')
    else:
        bot.reply_to(message, "لطفاً ابتدا وارد شوید (/login)")
    session.close()

@bot.message_handler(commands=['music'])
def send_music(message):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if user and user.is_logged_in:
        bot.send_audio(message.chat.id, audio=open('music.mp3', 'rb'))
    else:
        bot.reply_to(message, "لطفاً ابتدا وارد شوید (/login)")
    session.close()

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    bot.infinity_polling()
