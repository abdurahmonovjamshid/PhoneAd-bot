from django.contrib import admin

from .models import TgUser, PhoneAdImage, PhoneAd


@admin.register(TgUser)
class TgUserAdmin(admin.ModelAdmin):

    list_display = ('__str__', 'phone', 'created_at')

class PhoneAdImageInline(admin.TabularInline):
    model = PhoneAdImage
    extra = 0
    readonly_fields = ('file_id',)
    can_delete = True


@admin.register(PhoneAd)
class PhoneAdAdmin(admin.ModelAdmin):
    list_display = ('marka', 'narx_usd', 'user', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'obmen')
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
                'narx_usd',
                'obmen',
                'manzil',
                'tel_raqam',
                'status',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PhoneAdImage)
class PhoneAdImageAdmin(admin.ModelAdmin):
    list_display = ('ad', 'file_id', 'created_at')
    search_fields = ('ad__marka', 'file_id')
    readonly_fields = ('created_at',)
