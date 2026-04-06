from telebot import types
from django.utils.timezone import now
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models import PricingNode, PricingSession


def step_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⬅️ Orqaga qaytish", "❌ Bekor qilish")
    return markup

def ask_question(chat_id, step, bot):
    questions = {
        1: "📷 Telefon rasmlarini yuboring (kamida 4 ta, ko‘pi bilan 6 ta):",
        2: "📱 Telefon markasini kiriting (masalan: Iphone 16; Redmi Note 14 pro):",
        3: "🛠 Telefon holatini kiriting (masalan: Yangi; Yaxshi; O'rtacha):",
        4: "🔋 Batareka sig'imini kiriting (masalan: 4500 mAH; 95%):",
        5: "💾 Telefon xotirasini kiriting",
        6: "🎨 Rangini kiriting:",
        7: "📦 Karobka/dokument bormi? (Bor / Yo'q)",
        8: "💰 Narxni kiriting: (So'm / USD)",
        9: "♻️ Obmen bormi? (Ha / Yo‘q):",
        10: "🚩 Manzilni kiriting:",
        11: "📞 Telefon raqamingizni yuboring:",
    }
    bot.send_message(chat_id, questions[step], reply_markup=step_keyboard())

def ask_questions(call, bot):
    session = PricingSession.objects.filter(
        user__telegram_id=call.from_user.id
    ).last()
    q = get_next_question(session)
    if not q:
        show_result(call, bot)
        return
    text = f"""{q.text}"""
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=answers_keyboard(q)
    )

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📢 E'lon joylash", "📱 Telefonlarni narxlash 💲")
    markup.add("📜 Mening e'lonlarim", "📞 Admin bilan bog‘lanish")
    return markup


def get_next_question(session):
    questions = PricingNode.objects.filter(
        parent=session.model,
        type="question"
    ).order_by("order")
    answered_ids = session.answers.values_list("id", flat=True)
    for q in questions[session.step:]:
        if q.show_if_answer:
            if q.show_if_answer.id not in answered_ids:
                continue
        return q
    return None

def calculate_preview(session):
    price = session.model.price_change
    for ans in session.answers.all():
        price += ans.price_change
    return price

def answers_keyboard(question):
    kb = types.InlineKeyboardMarkup()
    for ans in question.children.filter(type="answer"):
        kb.add(
            types.InlineKeyboardButton(
                ans.text,
                callback_data=f"ans_{ans.id}"
            )
        )
    if question.allow_skip:
        kb.add(
            types.InlineKeyboardButton(
                "⏭ Skip",
                callback_data="skip"
            )
        )
    kb.add(
        types.InlineKeyboardButton(
            "⬅ Back",
            callback_data="back"
        )
    )
    return kb

def show_result(call, bot):
    session = PricingSession.objects.filter(
        user__telegram_id=call.from_user.id
    ).last()
    price = calculate_preview(session)
    lines = []
    for ans in session.answers.select_related("parent").order_by("parent__order"):
        question = ans.parent
        icon = question.icon or ""
        label = question.label or question.text
        lines.append(f"{icon} {label}: {ans.text}")
    answers_text = "\n".join(lines)
    date_str = now().strftime("%d.%m.%Y")
    text = f"""
📱 {session.model.text}
💰 Taxminiy narx: {price}$
🕒 Narxlash sanasi: {date_str}
📝 Configuration
{answers_text}
"""

    session.is_active = False
    session.save()
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "📢 Shu narxda e'lon berish",
            callback_data=f"post_price:{session.id}"
        )
    )
    kb.add(
        types.InlineKeyboardButton(
            "✏️ Narxni o‘zgartirish",
            callback_data=f"change_price:{session.id}"
        )
    )
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup = kb
    )

MODELS_PER_PAGE = 6

def models_keyboard(page=0):
    models = list(
        PricingNode.objects
        .filter(type="model")
        .order_by("-order")   # newest first
    )
    start = page * MODELS_PER_PAGE
    end = start + MODELS_PER_PAGE
    current = models[start:end]
    kb = types.InlineKeyboardMarkup(row_width=2)
    row = []
    for m in current:
        btn = types.InlineKeyboardButton(
            m.text,
            callback_data=f"model_{m.id}"
        )
        row.append(btn)
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("⬅️ Oldingi", callback_data=f"models_page_{page-1}"))
    if end < len(models):
        nav.append(types.InlineKeyboardButton("Keyingi ➡️", callback_data=f"models_page_{page+1}"))
    if nav:
        kb.row(*nav)
    return kb

PRICING_PACKAGES = {
    "1": {"count": 1, "price": 5000},
    "5": {"count": 5, "price": 20000},
    "10": {"count": 10, "price": 35000},
    "15": {"count": 15, "price": 50000},
    "15d": {"days": 15, "price": 60000},
    "30d": {"days": 30, "price": 100000},
}

PACKAGE_NAMES = {
    "1": "1 marta",
    "5": "5 marta",
    "10": "10 marta",
    "15": "15 marta",
    "15d": "15 kun",
    "30d": "30 kun",
}

def pricing_packages_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("1 ta narxlash", callback_data="pkg_1"),
        InlineKeyboardButton("5 ta narxlash", callback_data="pkg_5"),
    )
    kb.add(
        InlineKeyboardButton("10 ta narxlash", callback_data="pkg_10"),
        InlineKeyboardButton("15 ta narxlash", callback_data="pkg_15"),
    )
    kb.add(
        InlineKeyboardButton("15 kunlik", callback_data="pkg_15d"),
        InlineKeyboardButton("30 kunlik", callback_data="pkg_30d"),
    )
    return kb
