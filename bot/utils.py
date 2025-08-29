from django.utils.timezone import now
from telebot import types

from bot.models import PhoneAd, TgUser

def get_stats():
    today = now().date()

    # Users
    total_users = TgUser.objects.count()
    deleted_users = TgUser.objects.filter(deleted=True).count()
    active_users = total_users - deleted_users
    today_users = TgUser.objects.filter(created_at__date=today).count()

    # Ads
    total_ads = PhoneAd.objects.count()
    published_ads = PhoneAd.objects.filter(is_published=True).count()
    today_ads = PhoneAd.objects.filter(created_at__date=today).count()

    stats_text = (
        f"📊 <b>Statistics</b>\n\n"
        f"👤 Users:\n"
        f" ├ Total: {total_users}\n"
        f" ├ Active: {active_users}\n"
        f" ├ Deleted: {deleted_users}\n"
        f" └ Joined today: {today_users}\n\n"
        f"📱 Phone Ads:\n"
        f" ├ Total: {total_ads}\n"
        f" ├ Published: {published_ads}\n"
        f" └ Created today: {today_ads}\n"
    )

    return stats_text

def make_caption(ad):
    caption = (
            f"#Продается\n"
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
    return caption
