import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession

TOKEN = '7766745718:AAHAGngCtyriqOdF1-nJ-fB4ckxD1WQFCAk'
ADMIN_ID = 5000649010
proxy_url = "http://proxy.server:3128"
session = AiohttpSession(proxy=proxy_url)

bot = Bot(token=TOKEN, session=session)
dp = Dispatcher()

class OrderProcess(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_time = State()
    waiting_for_document = State()

def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="⚖️ Послуги та ціни"), types.KeyboardButton(text="📍 Контакти"))
    builder.row(types.KeyboardButton(text="📅 Записатися на прийом"))
    return builder.as_markup(resize_keyboard=True)

def get_services_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🏠 Цивільні справи", callback_data='civil'))
    builder.row(types.InlineKeyboardButton(text="🚔 Адмін. правопорушення", callback_data='admin'))
    builder.row(types.InlineKeyboardButton(text="📋 Список документів", callback_data='send_docs'))
    return builder.as_markup()

def get_back_button():
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="⬅️ Назад до послуг", callback_data='back_to_services'))
    return builder.as_markup()

def get_docs_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📸 Надіслати фото документів", callback_data='upload_docs'))
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад до послуг", callback_data='back_to_services'))
    return builder.as_markup()

@dp.message(Command("start"))
async def start(message: types.Message):
    welcome_text = (
        f"Вітаємо, *{message.from_user.first_name}*! 👋\n\n"
        "Я — ваш персональний асистент у юридичних питаннях.\n"
        "Допоможу дізнатися вартість послуг або записатися на консультацію."
    )
    await message.answer(welcome_text, parse_mode='Markdown', reply_markup=get_main_menu())

@dp.message(F.text == "⚖️ Послуги та ціни")
async def services(message: types.Message):
    await message.answer("⬇️ *Оберіть потрібний розділ:*", parse_mode='Markdown', reply_markup=get_services_menu())

@dp.message(F.text == "📍 Контакти")
async def contacts(message: types.Message):
    info = (
        "🏛 **Адвокатський кабінет**\n"
        "───────────────\n"
        "📍 **Адреса:** м. Івано-Франківськ\n"
        "⏰ **Графік:** Пн-Пт 09:00 - 18:00\n"
        "💼 Адвокат працює за попереднім записом."
    )
    await message.answer(info, parse_mode='Markdown')

@dp.message(F.text == "📅 Записатися на прийом")
async def process_appointment(message: types.Message, state: FSMContext):
    await message.answer("👤 *Введіть ваше Прізвище та Ім'я:*", parse_mode='Markdown')
    await state.set_state(OrderProcess.waiting_for_name)

@dp.message(OrderProcess.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📱 *Введіть номер телефону (10 цифр):*", parse_mode='Markdown')
    await state.set_state(OrderProcess.waiting_for_phone)

@dp.message(OrderProcess.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text
    if len(re.findall(r'\d', phone)) < 10:
        await message.answer("⚠️ *Помилка!* Введіть коректний номер (10 цифр):", parse_mode='Markdown')
        return
    await state.update_data(phone=phone)
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="Зранку"), types.KeyboardButton(text="В обід"), types.KeyboardButton(text="Ввечері"))
    await message.answer("⏰ *Коли вам зручно отримати дзвінок?*", parse_mode='Markdown', 
                         reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True))
    await state.set_state(OrderProcess.waiting_for_time)

@dp.message(OrderProcess.waiting_for_time)
async def process_finish(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    name = user_data.get('name', 'Не вказано')
    phone = user_data.get('phone', 'Не вказано')
    time = message.text
    await message.answer("✅ **Готово!** Очікуйте на дзвінок адвоката.", 
                         parse_mode='Markdown', reply_markup=get_main_menu())
    admin_info = (f"🔔 **НОВИЙ ЗАПИС!**\n\n👤 **Клієнт:** {name}\n"
                  f"📱 **Телефон:** {phone}\n⏰ **Зручний час:** {time}")
    await bot.send_message(ADMIN_ID, admin_info, parse_mode='Markdown')
    await state.clear()

@dp.callback_query(F.data == 'upload_docs')
async def ask_photo(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📸 Будь ласка, зробіть фото документа та надішліть його сюди:")
    await state.set_state(OrderProcess.waiting_for_document)

@dp.message(OrderProcess.waiting_for_document, F.photo)
async def handle_docs(message: types.Message, state: FSMContext):
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id,
                       caption=f"📄 **Новий документ!**\nВід: {message.from_user.first_name}\nID: {message.chat.id}")
    await message.answer("✅ Документ отримано та передано адвокату!", reply_markup=get_main_menu())
    await state.clear()

@dp.callback_query()
async def callbacks_handler(callback: types.CallbackQuery):
    if callback.data == 'civil':
        text = "🏠 **ЦИВІЛЬНІ СПРАВИ**\n...\n💰 **Вартість:** від 1000 грн."
        await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=get_back_button())
    elif callback.data == 'admin':
        text = "🚔 **АДМІНІСТРАТИВНІ СПРАВИ**\n...\n💰 **Вартість:** від 1500 грн."
        await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=get_back_button())
    elif callback.data == 'send_docs':
        text = "📋 **СПИСОК ДОКУМЕНТІВ:**\n1. Паспорт\n2. ІПН"
        await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=get_docs_menu())
    elif callback.data == 'back_to_services':
        await callback.message.edit_text("⬇️ *Оберіть потрібний розділ:*", parse_mode='Markdown', reply_markup=get_services_menu())

async def main():
    logging.basicConfig(level=logging.INFO)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())