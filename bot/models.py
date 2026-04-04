from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from mptt.admin import DraggableMPTTAdmin

class TgUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=15, default='-')

    is_bot = models.BooleanField(default=False)
    language_code = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Joined')

    step = models.IntegerField(default=0)

    deleted = models.BooleanField(default=False)

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name or ''}".strip()
        return (full_name[:30] + '...') if len(full_name) > 30 else full_name

from django.db import models

from django.db import models


class PhoneAd(models.Model):
    SELL_STATUS_CHOICES = (
        ('active', 'Active'),
        ('sold', 'Sold'),
        ('inactive', 'Inactive'),
    )

    user = models.ForeignKey('TgUser', on_delete=models.CASCADE, related_name='ads')

    # Telefon ma'lumotlari
    marka = models.CharField(max_length=255)  # 📱 telefon marka
    holati = models.CharField(max_length=255)  # 🛠 holati
    batareka_holati = models.CharField(max_length=255)  # 🔋 batareka holati
    xotira = models.CharField(max_length=255) # 🧠 Xotira
    rangi = models.CharField(max_length=50)  # 🎨 rangi
    komplekt = models.CharField(max_length=255)  # 📦 & 📑 bor yoki yo'q
    narx_usd_sum = models.CharField(max_length=50)  # 💰 dollarda sumda
    obmen = models.BooleanField(default=False)  # ♻️ obmen bor yo'qligi
    manzil = models.CharField(max_length=255)  # 🚩 manzil
    tel_raqam = models.CharField(max_length=20)  # 📞 telefon raqam

    # payment details
    payment_image = models.CharField(max_length=255, blank=True, null=True)  # Telegram file_id
    is_paid = models.BooleanField(default=False)

    # Status va vaqt
    status = models.CharField(max_length=10, choices=SELL_STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.marka} - ${self.narx_usd_sum}"


class PhoneAdImage(models.Model):
    ad = models.ForeignKey(PhoneAd, on_delete=models.CASCADE, related_name='images')
    file_id = models.CharField(max_length=255)  # Telegram file_id ni saqlash
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.ad.marka}"

class BroadcastTask(models.Model):
    admin_chat_id = models.BigIntegerField()
    message_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    total = models.IntegerField(default=0)       # total users to send
    sent = models.IntegerField(default=0)        # messages sent successfully
    failed = models.IntegerField(default=0)      # failed deliveries
    finished = models.BooleanField(default=False)

    finished_at = models.DateTimeField(null=True, blank=True)

    def progress_percent(self):
        if self.total == 0:
            return 0
        return round(self.sent / self.total * 100, 2)


class PricingNode(MPTTModel):
    NODE_TYPES = (
        ("model", "Model"),
        ("question", "Question"),
        ("answer", "Answer"),
    )
    parent = TreeForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE
    )
    type = models.CharField(max_length=10, choices=NODE_TYPES)
    text = models.CharField(max_length=255)
    price_change = models.IntegerField(default=0)
    order = models.IntegerField(default=0)
    # conditional question
    show_if_answer = TreeForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conditional_children"
    )
    allow_skip = models.BooleanField(default=False)
    final_text = models.TextField(blank=True)
    class MPTTMeta:
        order_insertion_by = ['order']
    def __str__(self):
        # nice display in admin tree
        if self.type == "answer":
            return f"{self.text} 💲{self.price_change}"
        return self.text

class PricingSession(models.Model):
    user = models.ForeignKey(TgUser, on_delete=models.CASCADE)
    model = models.ForeignKey(
        PricingNode,
        on_delete=models.CASCADE,
        related_name="model_sessions"
    )
    answers = models.ManyToManyField(
        PricingNode,
        blank=True,
        related_name="answer_sessions"
    )
    step = models.IntegerField(default=0)
    price_preview = models.IntegerField(default=0)