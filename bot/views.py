import re
from datetime import timedelta

import telebot
from django.utils.timezone import now
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from conf.settings import HOST, TELEGRAM_BOT_TOKEN, ADMINS, CHANNEL_ID
import json
import traceback
from django.http import HttpResponse
from telebot import TeleBot, types

from .helpers import calculate_preview, main_menu, ask_questions, ask_question, models_keyboard, \
    pricing_packages_keyboard, PRICING_PACKAGES, PACKAGE_NAMES
from .models import TgUser, PhoneAd, PhoneAdImage, BroadcastTask, PricingSession, PricingNode, PricingSessionImage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import time
from .utils import get_stats, make_caption

bot = TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)

@csrf_exempt
def telegram_webhook(request):
    try:
        if request.method == 'POST':
            update_data = request.body.decode('utf-8')
            update_json = json.loads(update_data)
            update = telebot.types.Update.de_json(update_json)
            if update.message:
                tg_user = update.message.from_user
                telegram_id = tg_user.id
                first_name = tg_user.first_name
                last_name = tg_user.last_name
                username = tg_user.username
                is_bot = tg_user.is_bot
                language_code = tg_user.language_code
                deleted = False
                tg_user_instance, _ = TgUser.objects.update_or_create(
                    telegram_id=telegram_id,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'username': username,
                        'is_bot': is_bot,
                        'language_code': language_code,
                        'deleted': deleted,
                    }
                )
            try:
                if update.my_chat_member.new_chat_member.status == 'kicked':
                    telegram_id = update.my_chat_member.from_user.id
                    user = TgUser.objects.get(telegram_id=telegram_id)
                    user.deleted = True
                    user.save()
            except:
                pass
            bot.process_new_updates(
                [telebot.types.Update.de_json(request.body.decode("utf-8"))])

        return HttpResponse("ok")
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        return HttpResponse("error")

@bot.callback_query_handler(func=lambda c: c.data.startswith("ans_"))
def answer_handler(call):
    ans_id = int(call.data.split("_")[1])
    answer = PricingNode.objects.get(id=ans_id)
    session = PricingSession.objects.filter(
        user__telegram_id=call.from_user.id,
        is_active=True
    ).last()
    session.answers.add(answer)
    session.step += 1
    session.price_preview = calculate_preview(session)
    session.save()
    ask_questions(call, bot)

@bot.callback_query_handler(func=lambda c: c.data == "back")
def go_back(call):
    session = PricingSession.objects.filter(
        user__telegram_id=call.from_user.id,
        is_active=True
    ).last()
    if not session:
        return
    if session.step == 0:
        session.is_active = False
        session.save()
        bot.edit_message_text(
            "📱 Telefon modelini tanlang:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=models_keyboard(0)
        )
        return
    session.step -= 1
    session.save()
    last_answer = session.answers.last()
    if last_answer:
        session.answers.remove(last_answer)
    ask_questions(call, bot)

@bot.callback_query_handler(func=lambda c: c.data == "skip")
def skip_question(call):
    session = PricingSession.objects.filter(
        user__telegram_id=call.from_user.id, is_active=True
    ).last()
    session.step += 1
    session.save()
    ask_questions(call, bot)


@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.send_message(message.chat.id, f"Salom, {message.from_user.full_name}!😊", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📱 Telefonlarni narxlash 💲")
def choose_model(message):
    user = TgUser.objects.get(telegram_id=message.from_user.id)
    if not user.can_use_pricing():
        bot.send_message(
            message.chat.id,
            "❌ Sizda narxlash limiti tugagan.\nPaket tanlang:",
            reply_markup=pricing_packages_keyboard()
        )
        return
    user.pricing_used += 1
    user.save()
    PricingSession.objects.filter(user=user, is_active=True).delete()
    bot.send_message(
        message.chat.id,
        "📱 Telefon modelini tanlang:",
        reply_markup=models_keyboard(0)
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("pkg_"))
def choose_package(call):
    key = call.data.split("_")[1]
    pkg = PRICING_PACKAGES[key]
    text = f"📦 Paket:\n\n"
    if "count" in pkg:
        text += f"{pkg['count']} ta narxlash\n"
    if "days" in pkg:
        text += f"{pkg['days']} kun foydalanish\n"
    text += f"\n💰 Narxi: {pkg['price']} so'm"
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("💳 To'lov qilish", callback_data=f"pay_{key}")
    )
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def request_payment(call):
    key = call.data.split("_")[1]
    user = TgUser.objects.get(telegram_id=call.from_user.id)
    user.step = 200
    user.step_package = key   # store selected package temporarily
    user.save()
    bot.send_message(
        call.message.chat.id,
        "💳 To'lov chekini rasm sifatida yuboring."
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("models_page_"))
def models_page(call):
    page = int(call.data.split("_")[-1])
    bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=models_keyboard(page)
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("model_"))
def choose_model_callback(call):
    model_id = int(call.data.split("_")[1])
    model = PricingNode.objects.get(id=model_id)
    user, _ = TgUser.objects.get_or_create(
        telegram_id=call.from_user.id
    )
    session = PricingSession.objects.create(
        user=user,
        model=model,
        step=0,
        price_preview=model.price_change,
        is_active=True
    )
    ask_questions(call, bot)
    user.save()

@bot.callback_query_handler(func=lambda c: c.data.startswith("post_price:"))
def post_with_price(call):
    session_id = int(call.data.split(":")[1])
    session = PricingSession.objects.get(id=session_id)
    session.final_price = session.price_preview
    session.step = 300
    session.is_active = True
    session.save()
    bot.send_message(
        call.message.chat.id,
        "📷 Telefon rasmlarini yuboring (kamida 4 ta):"
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("change_price:"))
def change_price(call):
    session_id = int(call.data.split(":")[1])
    session = PricingSession.objects.get(id=session_id)
    session.step = 301
    session.is_active = True
    session.save()
    bot.send_message(
        call.message.chat.id,
        "💰 Yangi narxni kiriting:"
    )

@bot.message_handler(func=lambda m: m.text == "📢 E'lon joylash")
def start_ad_process(message):
    tg_user = TgUser.objects.get(telegram_id=message.from_user.id)
    tg_user.step = 1
    tg_user.save()
    PhoneAd.objects.create(
        user=tg_user,
        marka='',
        holati='',
        batareka_holati='',
        rangi='',
        komplekt='',
        narx_usd_sum=0,
        obmen=False,
        manzil='',
        tel_raqam='',
        status='active'
    )

    ask_question(message.chat.id, 1, bot)

@bot.message_handler(commands=["send_to_all"])
def handle_send_to_all(message):
    if not message.reply_to_message:
        bot.send_message(message.chat.id, "❌ Reply to a message with /send_to_all")
        return

    task = BroadcastTask.objects.create(
        admin_chat_id=message.chat.id,
        message_id=message.reply_to_message.message_id,
        created_at=now()
    )

    bot.send_message(message.chat.id, f"✅ Task #{task.id} added to broadcast queue")


@bot.message_handler(commands=['stats'])
def stats_handler(message):
    if str(message.from_user.id) not in ADMINS:  # optional admin check
        bot.reply_to(message, "❌ You don’t have permission.")
        return
    stats_text = get_stats()
    bot.send_message(message.chat.id, stats_text, parse_mode="HTML")

@bot.message_handler(commands=["status"])
def broadcast_status(message):
    try:
        task = BroadcastTask.objects.latest("created_at")
    except BroadcastTask.DoesNotExist:
        bot.reply_to(message, "📭 No broadcast tasks yet.")
        return

    status = "✅ Finished" if task.finished else "⏳ In progress"
    text = (
        f"📢 Broadcast Task #{task.id}\n"
        f"Status: {status}\n"
        f"Progress: {task.progress_percent()}%\n"
        f"Sent: {task.sent}/{task.total}\n"
        f"Failed: {task.failed}\n"
        f"Created: {task.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )
    if task.finished and task.finished_at:
        text += f"Finished: {task.finished_at.strftime('%d.%m.%Y %H:%M')}"

    bot.reply_to(message, text)


@bot.message_handler(func=lambda m: m.text in ["❌ Bekor qilish", "⬅️ Orqaga qaytish"])
def cancel_or_back(message):
    tg_user = TgUser.objects.get(telegram_id=message.from_user.id)
    if message.text == "❌ Bekor qilish":
        PhoneAd.objects.filter(user=tg_user, status='active', marka='').delete()
        tg_user.step = 0
        tg_user.save()
        bot.send_message(message.chat.id, "❌ E'lon berish bekor qilindi", reply_markup=main_menu())
    elif message.text == "⬅️ Orqaga qaytish":
        if tg_user.step > 1:
            tg_user.step -= 1
            tg_user.save()
            ask_question(message.chat.id, tg_user.step, bot)
        else:
            bot.send_message(message.chat.id, "⏪ Boshlanishga qaytdingiz", reply_markup=main_menu())
            tg_user.step = 0
            tg_user.save()

@bot.message_handler(func=lambda m: m.forward_from_chat is not None, content_types=['text','photo'])
def handle_forwarded_post(message):
    channelid = message.forward_from_chat.id
    original_msg_id = message.forward_from_message_id
    if str(message.from_user.id) not in ADMINS or str(channelid) != CHANNEL_ID[0]:
        bot.reply_to(message, "❌ Sizda ruxsat yo'q.")
        return
    if message.text:
        old_text = message.text
        if "#Продается" in old_text:
            new_text = old_text.replace("#Продается", "#sotildi")
            bot.edit_message_text(new_text, chat_id=channelid, message_id=original_msg_id)
            bot.reply_to(message, "✅ Post tahrir qilindi: #sotildi")
        else:
            bot.reply_to(message, "ℹ️ Bu postda #Продается yo'q.")
    elif message.caption:
        old_caption = message.caption
        if "#Продается" in old_caption:
            new_caption = old_caption.replace("#Продается", "#sotildi")
            bot.edit_message_caption(new_caption, chat_id=channelid, message_id=original_msg_id)
            bot.reply_to(message, "✅ Post tahrir qilindi: #sotildi")
        else:
            bot.reply_to(message, "ℹ️ Bu postda #Продается yo'q.")

@bot.message_handler(content_types=['photo'])
def handle_photos(message):
    tg_user = TgUser.objects.get(telegram_id=message.from_user.id)
    file_id = message.photo[-1].file_id
    session = PricingSession.objects.filter(user=tg_user, is_active=True).last()
    if session:
        if session.step == 300:
            PricingSessionImage.objects.create(
                session=session,
                file_id=file_id
            )
            count = session.images.count()
            if count >= 4:
                session.step = 302
                session.save()

                bot.send_message(
                    message.chat.id,
                    "♻️ Obmen bormi? (Ha / Yo‘q)"
                )
            else:
                bot.send_message(
                    message.chat.id,
                    f"📷 {count} ta rasm qabul qilindi. Yana yuboring."
                )
            return
        if session.step == 305:
            session.payment_image = file_id
            session.step = 306
            session.save()
            text = (
                f"📢 Yangi e'lon tasdiqlash\n\n"
                f"💰 Narx: {session.final_price}\n"
                f"♻️ Obmen: {'Bor' if session.obmen else 'Yo‘q'}\n"
                f"🚩 Manzil: {session.manzil}\n"
                f"📞 Tel: {session.tel_raqam}"
            )
            bot.send_message(
                message.chat.id,
                "✅ Chek yuborildi. Admin tasdiqlashini kuting."
            )
            media = []
            for i, photo in enumerate(session.images.all()):
                if i == 0:
                    media.append(
                        InputMediaPhoto(
                            photo,
                            caption=build_channel_caption(session),
                            parse_mode="HTML"
                        )
                    )
                else:
                    media.append(InputMediaPhoto(photo))

            media = []
            images = list(session.images.all())  # get all images

            if not images:
                return  # nothing to send

            # Prepare media group
            for i, img in enumerate(images):
                if i == 0:
                    media.append(
                        InputMediaPhoto(
                            img.file_id,
                            caption=build_channel_caption(session),  # your function
                            parse_mode="HTML"
                        )
                    )
                else:
                    media.append(InputMediaPhoto(img.file_id))

            for admin in ADMINS:
                if len(images) == 1:
                    # only 1 image, send as single photo
                    preview_message_id = bot.send_photo(
                        admin,
                        images[0].file_id,
                        caption=build_channel_caption(session),
                        parse_mode="HTML"
                    ).message_id
                else:
                    # multiple images, send media group
                    preview_msgs = bot.send_media_group(admin, media)
                    preview_message_id = preview_msgs[0].message_id

                # inline keyboard
                kb = InlineKeyboardMarkup()
                kb.add(
                    InlineKeyboardButton(
                        "✅ Tasdiqlash",
                        callback_data=f"approve_price_{session.id}"
                    ),
                    InlineKeyboardButton(
                        "❌ Rad etish",
                        callback_data=f"reject_price_{session.id}"
                    )
                )

                # send user info
                user_text = (
                    "👤 <b>Foydalanuvchi</b>\n\n"
                    f"Ism: {tg_user.first_name}\n"
                    f"Username: @{tg_user.username if tg_user.username else '-'}\n"
                    f"ID: <code>{tg_user.telegram_id}</code>\n\n"
                    f"💰 Narx: {session.final_price}$"
                )

                bot.send_photo(
                    admin,
                    images[0].file_id,
                    caption=user_text,
                    parse_mode="HTML",
                    reply_markup=kb,
                    reply_to_message_id=preview_message_id
                )
            return
    if tg_user.step == 200:
        pkg_key = tg_user.step_package
        username = f"@{tg_user.username}" if tg_user.username else tg_user.first_name
        package_name = PACKAGE_NAMES.get(pkg_key, pkg_key)
        caption = (
            "💳 <b>Yangi to'lov cheki</b>\n\n"
            f"👤 <b>Foydalanuvchi:</b> {username}\n"
            f"🆔 <b>User ID:</b> {tg_user.id}\n"
            f"📦 <b>Paket:</b> {package_name}\n"
            f"⏰ <b>Vaqt:</b> {now().strftime('%d-%m-%Y %H:%M')}"
        )
        bot.send_message(
            message.chat.id,
            "📩 Sizning to'lov chek qabul qilindi.\n"
            "⏳ Admin tasdiqlashi kutilmoqda."
        )
        for admin in ADMINS:
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton(
                    "✅ Tasdiqlash",
                    callback_data=f"approve_{tg_user.id}_{pkg_key}"
                ),
                InlineKeyboardButton(
                    "❌ Rad etish",
                    callback_data=f"reject_{tg_user.id}"
                )
            )
            bot.send_photo(
                admin,
                file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb
            )

        return
    if tg_user.step == 13:
        try:
            ad = PhoneAd.objects.filter(
                user=tg_user,
                status='active'
            ).latest('created_at')
        except PhoneAd.DoesNotExist:
            bot.send_message(
                message.chat.id,
                "❌ Hech qanday e'lon topilmadi."
            )
            return
        ad.payment_image = file_id
        ad.is_paid = True
        ad.save()
        tg_user.step = 0
        tg_user.save()
        caption = make_caption(ad) + "\n💳 To‘lov tasdiqlangan."
        photos = list(ad.images.all())
        if photos:
            media = []
            for i, img in enumerate(photos):
                if i == 0:
                    media.append(
                        types.InputMediaPhoto(
                            media=img.file_id,
                            caption=caption,
                            parse_mode='HTML'
                        )
                    )
                else:
                    media.append(
                        types.InputMediaPhoto(media=img.file_id)
                    )
            bot.send_media_group(message.chat.id, media)
        else:
            bot.send_message(
                message.chat.id,
                caption,
                parse_mode='HTML'
            )
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                "✅ Adminga yuborish",
                callback_data=f"ad_user_send:{ad.id}"
            ),
            types.InlineKeyboardButton(
                "🗑 O‘chirib yuborish",
                callback_data=f"ad_user_delete:{ad.id}"
            )
        )
        bot.send_message(
            message.chat.id,
            "E'lon ma'lumotlarini tasdiqlang:",
            reply_markup=kb
        )
        return
    if tg_user.step != 1 and not session:
        bot.send_message(
            message.chat.id,
            "📌 Iltimos, hozir rasm emas, so‘ralgan ma'lumotni yuboring."
        )
        return

    ad = PhoneAd.objects.filter(
        user=tg_user,
        status='active'
    ).latest('created_at')
    PhoneAdImage.objects.create(
        ad=ad,
        file_id=file_id
    )
    image_count = ad.images.count()
    if image_count >= 4:
        bot.send_message(
            message.chat.id,
            f"✅ {image_count} ta rasm qabul qilindi."
        )
        tg_user.step = 2
        tg_user.save()
        ask_question(message.chat.id, 2, bot)
    else:
        bot.send_message(
            message.chat.id,
            f"📷 {image_count} ta rasm qo‘shildi. Yana rasm yuboring."
        )

@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_") and not c.data.startswith("approve_price_"))
def approve_payment(call):
    print(call.data)
    _, user_id, pkg_key = call.data.split("_")
    user = TgUser.objects.get(id=user_id)
    pkg = PRICING_PACKAGES.get(pkg_key)
    if not pkg:
        bot.answer_callback_query(call.id, "❌ Paket topilmadi.")
        return
    text = ""
    if "count" in pkg:
        user.pricing_limit += pkg["count"]
        text = f"✅ To'lov tasdiqlandi!\n\n📱 Telefon narxlash funksiyasidan {pkg['count']} marta foydalanishingiz mumkin."
    if "days" in pkg:
        user.pricing_expire = now() + timedelta(days=pkg["days"])
        user.pricing_limit = 999999
        text = f"✅ To'lov tasdiqlandi!\n\n📱 Telefon narxlash funksiyasidan {pkg['days']} kun davomida foydalanishingiz mumkin."
    user.step = 0
    user.step_package = None
    user.save()
    bot.send_message(user.telegram_id, text)
    bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=None
    )

@bot.message_handler(func=lambda m: m.text == "📜 Mening e'lonlarim")
def my_ads(message):
    tg_user = TgUser.objects.get(telegram_id=message.from_user.id)
    ads = PhoneAd.objects.filter(user=tg_user).order_by('-created_at')
    if not ads.exists():
        bot.send_message(message.chat.id, "📭 Sizda hali e'lonlar yo'q.")
        return
    if ads.count() <= 3:
        # Directly send all ads
        for ad in ads:
            send_ad_details(message.chat.id, ad)
    else:
        # Monospace list
        lines = []
        for i, ad in enumerate(ads, start=1):
            # inline monospace with Markdown
            lines.append(f"""`{i}. {ad.marka} {ad.narx_usd_sum} {ad.created_at.strftime("%d.%m.%y")}`""")
        ad_list_text = "📜 E'lonlaringiz ro'yxati:\n\n" + "\n".join(lines)
        # Numbered buttons where label = index, callback_data = real ad.id
        markup = InlineKeyboardMarkup(row_width=4)
        buttons = [InlineKeyboardButton(str(i), callback_data=f"myad_{ad.id}")
                   for i, ad in enumerate(ads, start=1)]
        # add in rows of 4
        for start in range(0, len(buttons), 4):
            markup.row(*buttons[start:start+4])
        bot.send_message(message.chat.id, ad_list_text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("myad_"))
def show_ad_detail(call):
    try:
        ad_id = int(call.data.split("_")[1])
        ad = PhoneAd.objects.get(id=ad_id)
    except (ValueError, PhoneAd.DoesNotExist):
        bot.answer_callback_query(call.id, "❌ E'lon topilmadi.")
        return
    send_ad_details(call.message.chat.id, ad)
    bot.answer_callback_query(call.id)

# Helper function to send ad with photos
def send_ad_details(chat_id, ad: PhoneAd):
    kanal_status = "✅" if ad.is_published == True else "❌"
    caption = make_caption(ad) + f"\n📡 Kanalga joylangan: {kanal_status}"
    images = ad.images.all()
    if images.exists():
        if images.count() == 1:
            bot.send_photo(chat_id, images[0].file_id, caption=caption, parse_mode="HTML")
        else:
            media_group = [
                telebot.types.InputMediaPhoto(
                    img.file_id,
                    caption=caption if i == 0 else None,
                    parse_mode="HTML"
                )
                for i, img in enumerate(images)
            ]
            bot.send_media_group(chat_id, media_group)
    else:
        bot.send_message(chat_id, caption, parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == "📞 Admin bilan bog‘lanish")
def contact_admins(message):
    markup = types.InlineKeyboardMarkup()
    admins = ["ayfon_ol", "ferrezis"]
    for username in admins:
        btn = types.InlineKeyboardButton(
            text=f"@{username}",
            url=f"https://t.me/{username}"
        )
        markup.add(btn)
    bot.send_message(
        message.chat.id,
        "Adminlar bilan bog‘lanishingiz mumkin 👇",
        reply_markup=markup
    )

def build_channel_caption(session):
    """
    Build nicely formatted caption for channel post with question: answer format
    """
    model_name = session.model.text if session.model else "N/A"

    # Build answers: "Question: Answer"
    lines = [f"📱 Model: {model_name}"]

    for ans in session.answers.select_related("parent").order_by("parent__order"):
        question = ans.parent
        if question:
            icon = question.icon or ""
            label = question.label or question.text
            lines.append(f"{icon} {label}: {ans.text}")
        else:
            lines.append(f"{ans.text}")

    # Add pricing and other info
    lines.append(f"💰 Narx: {session.final_price or 0}")
    lines.append(f"♻️ Obmen: {'Bor' if session.obmen else 'Yo‘q'}")
    lines.append(f"🚩 Manzil: {session.manzil or 'N/A'}")
    lines.append(f"📞 Tel: {session.tel_raqam or 'N/A'}")

    if session.user.username:
        lines.append(f"👤 @{session.user.username}")

    lines.append("\nTelefon adminga tegishli emas 🚩")
    lines.append("Zaklat bilan savdo qilmang🫱🏻‍🫲🏽")
    lines.append("@IS_telefonsavdo_bot")

    return "\n".join(lines)


@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_price_"))
def approve_price(call):
    try:
        session_id = int(call.data.split("_")[-1])
        session = PricingSession.objects.get(id=session_id)

        if session.is_posted:
            bot.answer_callback_query(call.id, "Bu narx allaqachon e'lon qilingan ✅")
            return

        # mark as approved and posted
        session.is_active = False
        session.is_posted = True
        session.save()

        caption = build_channel_caption(session)

        images = [img.file_id for img in session.images.all()[:4]]  # first 4 images
        if images:
            media = []
            for i, file_id in enumerate(images):
                if i == 0:
                    media.append(InputMediaPhoto(file_id, caption=caption))
                else:
                    media.append(InputMediaPhoto(file_id))
            bot.send_media_group(CHANNEL_ID, media)
        else:
            bot.send_message(CHANNEL_ID, caption)

        # notify admin
        bot.answer_callback_query(call.id, "✅ Narx kanalga e'lon qilindi")
        bot.send_message(call.from_user.id, "Narx muvaffaqiyatli kanalga e'lon qilindi ✅")

    except PricingSession.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Session topilmadi")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Xatolik yuz berdi: {str(e)}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_price_"))
def reject_price(call):
    session_id = int(call.data.split("_")[-1])
    session = PricingSession.objects.get(id=session_id)
    bot.send_message(
        session.user.telegram_id,
        "❌ Admin e'lonni rad etdi."
    )
    session.delete()

@bot.message_handler(content_types=['text'])
def handle_steps(message):
    tg_user = TgUser.objects.get(telegram_id=message.from_user.id)
    session = PricingSession.objects.filter(user=tg_user, is_active=True).last()
    if message.text in ["❌ Bekor qilish", "⬅️ Orqaga qaytish"]:
        return
    try:
        ad = PhoneAd.objects.filter(user=tg_user, status='active').latest('created_at')
    except PhoneAd.DoesNotExist:
        ad = None
    if session and session.step == 301:
        try:
            price = int(message.text.replace("$", ""))
        except:
            bot.send_message(message.chat.id, "❌ Narx noto‘g‘ri")
            return
        session.final_price = price
        session.step = 300
        session.save()
        bot.send_message(
            message.chat.id,
            "📷 Telefon rasmlarini yuboring (kamida 4 ta)"
        )
        return
    # OBMEN
    if session and session.step == 302:
        session.obmen = message.text.lower() in ["ha", "bor"]
        session.step = 303
        session.save()
        bot.send_message(message.chat.id, "🚩 Manzilni kiriting")
        return
    # MANZIL
    if session and session.step == 303:
        session.manzil = message.text
        session.step = 304
        session.save()
        bot.send_message(message.chat.id, "📞 Telefon raqamini yuboring")
        return
    # PHONE
    if session and session.step == 304:
        session.tel_raqam = message.text
        session.step = 305
        session.save()
        bot.send_message(message.chat.id, "💳 To‘lov chekini yuboring")
        return
    if tg_user.step == 2:
        if len(message.text) > 25:
            bot.reply_to(
                message,
                "❌ Marka nomi 25 ta belgidan oshmasligi kerak. Qisqaroq kiriting."
            )
            return
        ad.marka = message.text
        ad.save()
        tg_user.step = 3
    elif tg_user.step == 3:
        ad.holati = message.text
        ad.save()
        tg_user.step = 4
    elif tg_user.step == 4:
        ad.batareka_holati = message.text
        ad.save()
        tg_user.step = 5
    elif tg_user.step == 5:
        ad.xotira = message.text
        ad.save()
        tg_user.step = 6
    elif tg_user.step == 6:
        ad.rangi = message.text
        ad.save()
        tg_user.step = 7
    elif tg_user.step == 7:
        ad.komplekt = message.text
        ad.save()
        tg_user.step = 8
    elif tg_user.step == 8:
        text = message.text.strip().lower()
        text_clean = text.replace(",", "").replace(" ", "")
        if text_clean.endswith("$") or text_clean.endswith("usd"):
            currency = "USD"
            text_clean = text_clean.replace("$", "").replace("usd", "")
        elif text_clean.endswith("so'm") or text_clean.endswith("som") or text_clean.endswith("uzs"):
            currency = "UZS"
            text_clean = text_clean.replace("so'm", "").replace("som", "").replace("uzs", "")
        else:
            if text_clean.isdigit():
                currency = "USD"
            else:
                bot.send_message(message.chat.id,
                                 "❌ Narxni raqam va valyuta bilan kiriting (masalan: 1500 $, 1200300 so'm).")
                return
        try:
            amount = int(text_clean)
        except ValueError:
            bot.send_message(message.chat.id, "❌ Narx noto‘g‘ri kiritildi. Masalan: 1500 $, 1200300 so'm")
            return
        # Save in model
        ad.narx_usd_sum = f"{amount} {currency}"
        ad.save()
        tg_user.step = 9
    elif tg_user.step == 9:
        ad.obmen = message.text.lower() in ["ha", "bor"]
        ad.save()
        tg_user.step = 10
    elif tg_user.step == 10:
        ad.manzil = message.text
        ad.save()
        tg_user.step = 11
    elif tg_user.step == 11:
        phone = message.text.strip()
        pattern = r"^\+998\d{9}$"
        if not re.match(pattern, phone):
            bot.send_message(
                message.chat.id,
                "❌ Telefon raqamini to‘g‘ri kiriting. Masalan: +998901234567"
            )
            return
        ad.tel_raqam = phone
        ad.save()
        tg_user.step = 12
        tg_user.save()
        # Ask payment
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ Ha", callback_data=f"ad_payment_yes:{ad.id}"),
            types.InlineKeyboardButton("❌ Yo‘q", callback_data=f"ad_payment_no:{ad.id}")
        )
        bot.send_message(message.chat.id, "❓ Reklamani chiqarish pullik. To‘lov qildingizmi?", reply_markup=kb)
        return
    tg_user.save()
    if tg_user.step != 0:
        ask_question(message.chat.id, tg_user.step, bot)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ad_payment_"))
def cb_payment(call):
    action, ad_id = call.data.split(":")
    ad = PhoneAd.objects.get(id=ad_id)
    tg_user = TgUser.objects.get(telegram_id=call.from_user.id)
    if action == "ad_payment_no":
        caption = make_caption(ad)
        photos = list(ad.images.all())
        if photos:
            media = []
            for i, img in enumerate(photos):
                if i == 0:
                    media.append(types.InputMediaPhoto(media=img.file_id, caption=caption, parse_mode='HTML'))
                else:
                    media.append(types.InputMediaPhoto(media=img.file_id))
            bot.send_media_group(call.message.chat.id, media)
        else:
            bot.send_message(call.message.chat.id, caption, parse_mode='HTML')
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ Adminga yuborish", callback_data=f"ad_user_send:{ad.id}"),
            types.InlineKeyboardButton("🗑 O‘chirib yuborish", callback_data=f"ad_user_delete:{ad.id}")
        )
        bot.send_message(call.message.chat.id, "E'lon ma'lumotlarini tasdiqlang:", reply_markup=kb)
        tg_user.step = 0
        tg_user.save()
    elif action == "ad_payment_yes":
        tg_user.step = 13  # wait for payment screenshot
        tg_user.save()
        bot.send_message(call.message.chat.id, "📸 To‘lov chekini rasm sifatida yuboring.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("ad_user_send:"))
def cb_user_send_to_admin(call):
    ad_id = int(call.data.split(":")[1])
    try:
        ad = PhoneAd.objects.get(id=ad_id)
    except PhoneAd.DoesNotExist:
        bot.answer_callback_query(call.id, "E'lon topilmadi.")
        return

    caption = make_caption(ad)
    if ad.is_paid:
        caption += "\n\n💳 To‘lov: ✅ Tasdiqlangan"

    admin_kb = types.InlineKeyboardMarkup()
    admin_kb.add(
        types.InlineKeyboardButton("✅ Faollashtirish", callback_data=f"ad_admin_activate:{ad.id}"),
        types.InlineKeyboardButton("🗑 O‘chirish", callback_data=f"ad_admin_delete:{ad.id}")
    )
    imgs = list(ad.images.all())
    for admin_chat_id in ADMINS:
        if imgs:
            media = []
            for i, img in enumerate(imgs):
                if i == 0:
                    media.append(types.InputMediaPhoto(media=img.file_id, caption=caption, parse_mode='HTML'))
                else:
                    media.append(types.InputMediaPhoto(media=img.file_id))
            msg_list = bot.send_media_group(admin_chat_id, media)
            first_msg = msg_list[0]
        else:
            first_msg  = bot.send_message(admin_chat_id, caption, parse_mode='HTML')
        if ad.payment_image:
            bot.send_photo(admin_chat_id, ad.payment_image, caption="💳 To‘lov cheki", reply_to_message_id=first_msg.message_id)
        bot.send_message(admin_chat_id, "E'lonni boshqarish:", reply_markup=admin_kb)
    bot.answer_callback_query(call.id, "Adminga yuborildi ✅")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    bot.send_message(call.message.chat.id, "✅ E'loningiz adminga yuborildi. Javob kuting.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("ad_user_delete:"))
def cb_user_delete(call):
    ad_id = int(call.data.split(":")[1])
    try:
        ad = PhoneAd.objects.get(id=ad_id)
    except PhoneAd.DoesNotExist:
        bot.answer_callback_query(call.id, "E'lon topilmadi.")
        return
    ad.delete()  # PhoneAdImage lar CASCADE bilan o‘chadi
    bot.answer_callback_query(call.id, "E'lon o‘chirildi.")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    bot.send_message(call.message.chat.id, "🗑 E'loningiz o‘chirildi.", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: c.data.startswith("ad_admin_activate:"))
def cb_admin_activate(call):
    ad_id = int(call.data.split(":")[1])
    try:
        ad = PhoneAd.objects.get(id=ad_id)
    except PhoneAd.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ E'lon topilmadi.")
        return

    if ad.is_published:
        bot.answer_callback_query(call.id, "⚠️ Bu e'lon allaqachon kanalga joylangan.")
        return

    bot.send_message(
        chat_id=ad.user.telegram_id,
        text=f"`{ad.marka} {ad.narx_usd_sum}` E'loningiz tasdiqlandi!",
        parse_mode="Markdown"
    )
    caption = make_caption(ad)
    imgs = list(ad.images.all())
    if imgs:
        media = []
        for i, img in enumerate(imgs):
            if i == 0:
                media.append(types.InputMediaPhoto(media=img.file_id, caption=caption, parse_mode='HTML'))
            else:
                media.append(types.InputMediaPhoto(media=img.file_id))
        bot.send_media_group(CHANNEL_ID[0], media)
    else:
        bot.send_message(CHANNEL_ID[0], caption, parse_mode='HTML')
    ad.status = 'active'
    ad.is_published = True
    ad.save()
    bot.answer_callback_query(call.id, "Kanalga joylandi ✅")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    bot.send_message(call.message.chat.id, "✅ Kanalga joylandi.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("ad_admin_delete:"))
def cb_admin_delete(call):
    ad_id = int(call.data.split(":")[1])
    try:
        ad = PhoneAd.objects.get(id=ad_id)
        bot.send_message(chat_id=ad.user.telegram_id, text=f"`{ad.marka} {ad.narx_usd_sum}` E'loningiz o'chirildi!",
                         parse_mode="Markdown")
    except PhoneAd.DoesNotExist:
        bot.answer_callback_query(call.id, "E'lon topilmadi.")
        return
    ad.delete()
    bot.answer_callback_query(call.id, "E'lon o‘chirildi.")
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    bot.send_message(call.message.chat.id, "🗑 E'lon o‘chirildi.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("myad_"))
def show_ad_detail(call):
    ad_id = int(call.data.split("_")[1])
    ad = PhoneAd.objects.get(id=ad_id)
    send_ad_details(call.message.chat.id, ad)
    bot.answer_callback_query(call.id)

BATCH_SIZE = 100  # adjust based on cron interval
@csrf_exempt
def run_broadcast(request):
    task = BroadcastTask.objects.filter(finished=False).order_by("created_at").first()
    if not task:
        return JsonResponse({"status": "idle", "message": "No active tasks"})
    if task.total == 0:
        task.total = TgUser.objects.count()
        task.save(update_fields=["total"])
    users = TgUser.objects.filter(deleted=False).order_by("id")[task.sent:task.sent+BATCH_SIZE]
    if not users:
        task.finished = True
        task.finished_at = now()
        task.save(update_fields=["finished", "finished_at"])
        return JsonResponse({
            "status": "done",
            "task_id": task.id,
            "total": task.total,
            "sent": task.sent,
            "failed": task.failed,
            "progress": f"{task.sent}/{task.total}"
        })
    sent = 0
    failed = 0
    for user in users:
        try:
            bot.copy_message(
                chat_id=user.telegram_id,
                from_chat_id=task.admin_chat_id,
                message_id=task.message_id
            )
            task.sent += 1
            sent += 1
        except Exception as e:
            task.failed += 1
            failed += 1
            if "forbidden" in str(e).lower() or "blocked" in str(e).lower():
                user.deleted = True
                user.save(update_fields=["deleted"])
        time.sleep(0.05)  # ~20 msg/sec safe rate
    task.save(update_fields=["sent", "failed"])
    return JsonResponse({
        "status": "ok",
        "task_id": task.id,
        "batch_sent": sent,
        "batch_failed": failed,
        "progress": f"{task.sent}/{task.total}",
        "percent": task.progress_percent(),
        "finished": False
    })

bot.set_webhook(url="https://"+HOST+"/webhook/")