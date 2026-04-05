from django.contrib import admin
from import_export.widgets import ForeignKeyWidget
from mptt.admin import DraggableMPTTAdmin
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from .models import TgUser, PhoneAd, PhoneAdImage, BroadcastTask, PricingNode, PricingSession

# Inline for children nodes (optional)
class PricingNodeInline(admin.TabularInline):
    model = PricingNode
    fk_name = "parent"
    extra = 1


class PricingNodeResource(resources.ModelResource):
    parent = fields.Field(
        column_name='parent',
        attribute='parent',
        widget=ForeignKeyWidget(PricingNode, 'id')  # resolves parent by ID
    )
    show_if_answer = fields.Field(
        column_name='show_if_answer',
        attribute='show_if_answer',
        widget=ForeignKeyWidget(PricingNode, 'id')
    )
    class Meta:
        model = PricingNode
        import_id_fields = ('id',)
        fields = (
            'id', 'parent', 'type', 'text', 'label', 'icon',
            'price_change', 'order', 'show_if_answer', 'allow_skip', 'final_text'
        )

# Admin
@admin.register(PricingNode)
class PricingNodeAdmin(ImportExportModelAdmin, DraggableMPTTAdmin):
    inlines = [PricingNodeInline]
    resource_class = PricingNodeResource
    list_display = ('tree_actions', 'indented_title', 'type', 'label', 'icon', 'price_change')
    list_display_links = ('indented_title',)
    search_fields = ('text', 'label')
    list_filter = ('type',)
@admin.register(PricingSession)
class PricingSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "model",
        "step",
        "price_preview",
    )
    filter_horizontal = ("answers",)

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
    list_filter = ("deleted","step")

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