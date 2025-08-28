import re

import telebot
from django.utils.timezone import now
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from conf.settings import HOST, TELEGRAM_BOT_TOKEN, ADMINS, CHANNEL_ID
import json
import traceback
from django.http import HttpResponse
from telebot import TeleBot, types
from .models import TgUser, PhoneAd, PhoneAdImage, BroadcastTask
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import time

from .utils import get_stats

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

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📢 E'lon joylash", "📜 Mening e'lonlarim")
    markup.add("📞 Admin bilan bog‘lanish")
    return markup


def step_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⬅️ Orqaga qaytish", "❌ Bekor qilish")
    return markup


def ask_question(chat_id, step):
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


@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.send_message(message.chat.id, f"Salom, {message.from_user.full_name}!😊", reply_markup=main_menu())


@bot.message_handler(func=lambda m: m.text == "📢 E'lon joylash")
def start_ad_process(message):
    tg_user = TgUser.objects.get(telegram_id=message.from_user.id)
    tg_user.step = 1
    tg_user.save()

    # Create empty ad
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

    ask_question(message.chat.id, 1)

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
            ask_question(message.chat.id, tg_user.step)
        else:
            bot.send_message(message.chat.id, "⏪ Boshlanishga qaytdingiz", reply_markup=main_menu())
            tg_user.step = 0
            tg_user.save()

@bot.message_handler(func=lambda m: m.forward_from_chat is not None, content_types=['text','photo'])
def handle_forwarded_post(message):
    channelid = message.forward_from_chat.id
    original_msg_id = message.forward_from_message_id

    # Only allow specific admins
    if str(message.from_user.id) not in ADMINS or str(channelid) != CHANNEL_ID[0]:
        bot.reply_to(message, "❌ Sizda ruxsat yo'q.")
        return

    # Handle text messages
    if message.text:
        old_text = message.text
        if "#Продается" in old_text:
            new_text = old_text.replace("#Продается", "#sotildi")
            bot.edit_message_text(new_text, chat_id=channelid, message_id=original_msg_id)
            bot.reply_to(message, "✅ Post tahrir qilindi: #sotildi")
        else:
            bot.reply_to(message, "ℹ️ Bu postda #Продается yo'q.")

    # Handle media with caption
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
    if tg_user.step != 1:
        bot.send_message(message.chat.id, "📌 Iltimos, hozir rasm emas, so‘ralgan ma'lumotni yuboring.")
        return

    ad = PhoneAd.objects.filter(user=tg_user, status='active').latest('created_at')
    file_id = message.photo[-1].file_id
    PhoneAdImage.objects.create(ad=ad, file_id=file_id)

    image_count = ad.images.count()
    if image_count >= 4:
        bot.send_message(message.chat.id, f"✅ {image_count} ta rasm qabul qilindi.")
        tg_user.step = 2
        tg_user.save()
        ask_question(message.chat.id, 2)
    else:
        bot.send_message(message.chat.id, f"📷 {image_count} ta rasm qo‘shildi. Yana rasm yuboring.")

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
    kanal_status = "✅" if ad.status == "active" else "❌"
    caption = (
        f"📱 <b>{ad.marka}</b>\n"
        f"💰 Narx: {ad.narx_usd_sum}\n"
        f"🎨 Rang: {ad.rangi}\n"
        f"📦 Komplekt: {ad.komplekt}\n"
        f"🚩 Manzil: {ad.manzil}\n"
        f"📞 Tel: {ad.tel_raqam}\n"
        f"📡 Kanalga joylangan: {kanal_status}"
    )

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

@bot.message_handler(content_types=['text'])
def handle_steps(message):
    tg_user = TgUser.objects.get(telegram_id=message.from_user.id)

    # Skip cancel/back here
    if message.text in ["❌ Bekor qilish", "⬅️ Orqaga qaytish"]:
        return

    try:
        ad = PhoneAd.objects.filter(user=tg_user, status='active').latest('created_at')
    except PhoneAd.DoesNotExist:
        ad = None

    if tg_user.step == 2:
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

        # Normalize input (remove commas, extra spaces)
        text_clean = text.replace(",", "").replace(" ", "")

        currency = None
        amount = None

        # Detect USD
        if text_clean.endswith("$") or text_clean.endswith("usd"):
            currency = "USD"
            text_clean = text_clean.replace("$", "").replace("usd", "")
        # Detect UZS
        elif text_clean.endswith("so'm") or text_clean.endswith("som") or text_clean.endswith("uzs"):
            currency = "UZS"
            text_clean = text_clean.replace("so'm", "").replace("som", "").replace("uzs", "")
        else:
            # If only numbers, default to USD
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
        pattern = r"^\+998\d{9}$"  # +998 va keyin 9 ta raqam
        if not re.match(pattern, phone):
            bot.send_message(
                message.chat.id,
                "❌ Telefon raqamini to‘g‘ri kiriting. Masalan: +998901234567"
            )
            return
        ad.tel_raqam = phone
        ad.save()
        tg_user.step = 0
        tg_user.save()
        # Foydalanuvchiga oldindan ko‘rish matni
        caption = (
            f"📱 <b>{ad.marka}</b>\n"
            f"🛠 Holati: {ad.holati}\n"
            f"🔋 Batareka: {ad.batareka_holati}\n"
            f"💾 Xotira: {ad.xotira}\n"
            f"🎨 Rang: {ad.rangi}\n"
            f"📦 Komplekt: {ad.komplekt}\n"
            f"💰 Narx: {ad.narx_usd_sum}\n"
            f"♻️ Obmen: {'Bor' if ad.obmen else 'Yo‘q'}\n"
            f"🚩 Manzil: {ad.manzil}\n"
            f"📞 Tel: {ad.tel_raqam}\n"
            f"{'👤 @' + ad.user.username if ad.user.username else ''}"
            + ("\n\n" if ad.user.username else "\n")
                + (
                "Telefon adminga tegishli emas 🚩\n"
                "Zaklat bilan savdo qilmang🫱🏻‍🫲🏽\n"
                "@IS_telefonsavdo_bot"
                )
        )
        photos = list(ad.images.all())
        if photos:
            media = []
            for i, img in enumerate(photos):
                if i == 0:
                    media.append(types.InputMediaPhoto(media=img.file_id, caption=caption, parse_mode='HTML'))
                else:
                    media.append(types.InputMediaPhoto(media=img.file_id))
            bot.send_media_group(message.chat.id, media)
        else:
            bot.send_message(message.chat.id, caption, parse_mode='HTML')
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ Adminga yuborish", callback_data=f"ad_user_send:{ad.id}"),
            types.InlineKeyboardButton("🗑 O‘chirib yuborish", callback_data=f"ad_user_delete:{ad.id}")
        )
        bot.send_message(message.chat.id, "E'lon ma'lumotlarini tasdiqlang:", reply_markup=kb)
        return

    tg_user.save()
    if tg_user.step != 0:
        ask_question(message.chat.id, tg_user.step)


@bot.callback_query_handler(func=lambda c: c.data.startswith("ad_user_send:"))
def cb_user_send_to_admin(call):
    ad_id = int(call.data.split(":")[1])
    try:
        ad = PhoneAd.objects.get(id=ad_id)
    except PhoneAd.DoesNotExist:
        bot.answer_callback_query(call.id, "E'lon topilmadi.")
        return

    caption = (
        f"🆕 Yangi e'lon (tasdiqlash kerak)\n\n"
        f"📱 <b>{ad.marka}</b>\n"
        f"🛠 Holati: {ad.holati}\n"
        f"🔋 Batareka: {ad.batareka_holati}\n"
        f"💾 Xotira: {ad.xotira}\n"
        f"🎨 Rang: {ad.rangi}\n"
        f"📦 Komplekt: {ad.komplekt}\n"
        f"💰 Narx: {ad.narx_usd_sum}\n"
        f"♻️ Obmen: {'Bor' if ad.obmen else 'Yo‘q'}\n"
        f"🚩 Manzil: {ad.manzil}\n"
        f"📞 Tel: {ad.tel_raqam}\n"
        f"{'👤 @' + ad.user.username if ad.user.username else ''}"
            + ("\n\n" if ad.user.username else "\n")
                + (
                "Telefon adminga tegishli emas 🚩\n"
                "Zaklat bilan savdo qilmang🫱🏻‍🫲🏽\n"
                "@IS_telefonsavdo_bot"
                )
    )

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
            bot.send_media_group(admin_chat_id, media)
        else:
            bot.send_message(admin_chat_id, caption, parse_mode='HTML')
        bot.send_message(admin_chat_id, "E'lonni boshqarish:", reply_markup=admin_kb)

    bot.answer_callback_query(call.id, "Adminga yuborildi ✅")
    # Istasangiz, foydalanuvchidagi tugmalarni olib tashlashingiz mumkin:
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

    # ✅ Prevent duplicates
    if ad.is_published:
        bot.answer_callback_query(call.id, "⚠️ Bu e'lon allaqachon kanalga joylangan.")
        return

    # Owner notification
    bot.send_message(
        chat_id=ad.user.telegram_id,
        text=f"`{ad.marka} {ad.narx_usd_sum}` E'loningiz tasdiqlandi!",
        parse_mode="Markdown"
    )

    # Kanal uchun caption
    caption = (
        f"#Продается\n"
        f"📱 <b>{ad.marka}</b>\n"
        f"🛠 Holati: {ad.holati}\n"
        f"💰 Narx: {ad.narx_usd_sum}\n"
        f"🔋 Batareka: {ad.batareka_holati}\n"
        f"💾 Xotira: {ad.xotira}\n"
        f"🎨 Rang: {ad.rangi}\n"
        f"📦 {ad.komplekt}\n"
        f"🚩 {ad.manzil}\n"
        f"♻️ Obmen: {'Bor' if ad.obmen else 'Yo‘q'}\n"
        f"📞 Tel: {ad.tel_raqam}\n"
        f"{'👤 @' + ad.user.username if ad.user.username else ''}"
            + ("\n\n" if ad.user.username else "\n")
                + (
                "Telefon adminga tegishli emas 🚩\n"
                "Zaklat bilan savdo qilmang🫱🏻‍🫲🏽\n"
                "@IS_telefonsavdo_bot"
                )
    )

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

    # Mark as published ✅
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

# Command handler for "📜 Mening e'lonlarim"
@bot.message_handler(func=lambda m: m.text == "📜 Mening e'lonlarim")
def my_ads(message):
    tg_user = TgUser.objects.get(user_id=message.from_user.id)
    ads = PhoneAd.objects.filter(user=tg_user).order_by('-created_at')

    if not ads.exists():
        bot.send_message(message.chat.id, "📭 Sizda hali e'lonlar yo'q.")
        return

    if ads.count() <= 3:
        # Directly send all ads
        for ad in ads:
            send_ad_details(message.chat.id, ad)
    else:
        # Send paginated list
        markup = InlineKeyboardMarkup(row_width=5)
        buttons = [
            InlineKeyboardButton(str(i+1), callback_data=f"myad_{ad.id}")
            for i, ad in enumerate(ads)
        ]
        markup.add(*buttons)
        bot.send_message(message.chat.id, "📜 E'lonlaringiz ro'yxati:", reply_markup=markup)


# Callback query handler for pagination buttons
@bot.callback_query_handler(func=lambda c: c.data.startswith("myad_"))
def show_ad_detail(call):
    ad_id = int(call.data.split("_")[1])
    ad = PhoneAd.objects.get(id=ad_id)
    send_ad_details(call.message.chat.id, ad)
    bot.answer_callback_query(call.id)


# Helper function to send ad with photos
def send_ad_details(chat_id, ad: PhoneAd):
    # Collect status info
    kanal_status = "✅" if ad.status == "active" else "❌"
    caption = (
        f"📱 <b>{ad.marka}</b>\n"
        f"💰 Narx: {ad.narx_usd_sum}\n"
        f"🎨 Rang: {ad.rangi}\n"
        f"📦 Komplekt: {ad.komplekt}\n"
        f"🚩 Manzil: {ad.manzil}\n"
        f"📞 Tel: {ad.tel_raqam}\n"
        f"📡 Kanalga joylangan: {kanal_status}"
    )
    images = ad.images.all()
    if images.exists():
        if len(images) == 1:
            bot.send_photo(chat_id, images[0].file_id, caption=caption, parse_mode="HTML")
        else:
            media_group = [
                telebot.types.InputMediaPhoto(img.file_id, caption=caption if i == 0 else None, parse_mode="HTML")
                for i, img in enumerate(images)
            ]
            bot.send_media_group(chat_id, media_group)
    else:
        bot.send_message(chat_id, caption, parse_mode="HTML")

BATCH_SIZE = 100  # adjust based on cron interval

@csrf_exempt
def run_broadcast(request):
    task = BroadcastTask.objects.filter(finished=False).order_by("created_at").first()
    if not task:
        return JsonResponse({"status": "idle", "message": "No active tasks"})

    # initialize total if not set
    if task.total == 0:
        task.total = TgUser.objects.count()
        task.save(update_fields=["total"])

    # find users after last progress
    users = TgUser.objects.filter(id__gt=task.sent + task.failed).order_by("id")[:BATCH_SIZE]

    # if no users left → finish task
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