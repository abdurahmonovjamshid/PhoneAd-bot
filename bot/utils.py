from django.utils.timezone import now
from django.db.models import Count
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
