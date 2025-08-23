from django.contrib import admin
from django.utils.html import format_html
from .models import TgUser, PhoneAd, PhoneAdImage, BroadcastTask


@admin.register(BroadcastTask)
class BroadcastTaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "admin_chat_id",
        "message_id",
        "created_at",
        "sent",
        "failed",
        "total",
        "progress_percent",
        "finished",
        "finished_at",
    )
    list_filter = ("finished", "created_at")
    search_fields = ("id", "admin_chat_id")
    readonly_fields = ("created_at", "finished_at", "sent", "failed", "total")

    def progress_percent(self, obj):
        return f"{obj.progress_percent()} %"
    progress_percent.short_description = "Progress"

# --- Inline for PhoneAdImage (inside PhoneAd) ---
class PhoneAdImageInline(admin.TabularInline):
    model = PhoneAdImage
    extra = 0
    readonly_fields = ('preview', 'file_id', 'created_at')
    can_delete = True

    def preview(self, obj):
        # Replace with real <img src=...> if you store URLs instead of Telegram file_ids
        return format_html('<span style="color: gray;">{}</span>', obj.file_id)

    preview.short_description = "Preview"


# --- Inline for PhoneAd (inside TgUser) ---
class PhoneAdInline(admin.TabularInline):
    model = PhoneAd
    extra = 0
    fields = ('marka', 'status', 'narx_usd_sum', 'created_at')
    readonly_fields = ('created_at',)


# --- TgUser Admin ---
@admin.register(TgUser)
class TgUserAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'phone', 'ads_count', 'created_at')
    inlines = [PhoneAdInline]

    def ads_count(self, obj):
        return obj.ads.count()
    ads_count.short_description = "Phone Ads"


# --- PhoneAd Admin ---
@admin.register(PhoneAd)
class PhoneAdAdmin(admin.ModelAdmin):
    list_display = ('marka', 'narx_usd_sum', 'user', 'status', 'obmen', 'created_at', 'is_published')
    list_filter = ('status', 'obmen', 'created_at', 'rangi', 'holati', 'is_published')
    search_fields = ('marka', 'user__first_name', 'user__username', 'manzil', 'tel_raqam')
    inlines = [PhoneAdImageInline]
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': (
                'user',
                'marka',
                'holati',
                'batareka_holati',
                'rangi',
                'komplekt',
                'narx_usd_sum',
                'obmen',
                'manzil',
                'tel_raqam',
                'status',
                'is_published',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )