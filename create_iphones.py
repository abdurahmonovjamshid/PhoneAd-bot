import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")
django.setup()

from bot.models import PricingNode


print("🧹 Old models clearing...")
PricingNode.objects.filter(type="model").delete()


def add_question(model, text, order, answers):
    q = PricingNode.objects.create(
        parent=model,
        type="question",
        text=text,
        order=order
    )

    for i, ans in enumerate(answers, start=1):
        PricingNode.objects.create(
            parent=q,
            type="answer",
            text=ans["text"],
            price_change=ans["price"],
            order=i
        )


def create_model(name, price, order):

    print(f"📱 Creating {name}")

    model = PricingNode.objects.create(
        type="model",
        text=name,
        price_change=price,
        order=order
    )

    # ⭐ CONDITION
    add_question(
        model,
        "⭐ Holati",
        1,
        [
            {"text": "5️⃣ Ideal (yangi kabi)", "price": 0},
            {"text": "4️⃣ Juda yaxshi", "price": -40},
            {"text": "3️⃣ O‘rtacha", "price": -90},
            {"text": "2️⃣ Charchagan", "price": -160},
            {"text": "1️⃣ Juda yomon", "price": -250},
        ]
    )

    # 💾 MEMORY
    add_question(
        model,
        "💾 Xotira",
        2,
        [
            {"text": "64GB", "price": 0},
            {"text": "128GB", "price": 50},
            {"text": "256GB", "price": 120},
            {"text": "512GB", "price": 220},
            {"text": "1TB", "price": 350},
        ]
    )

    # 🔋 BATTERY
    add_question(
        model,
        "🔋 Batareya",
        3,
        [
            {"text": "90-100%", "price": 0},
            {"text": "85-89%", "price": -30},
            {"text": "80-84%", "price": -70},
            {"text": "75-79%", "price": -120},
            {"text": "75% dan past", "price": -180},
        ]
    )

    # 🌍 REGION
    add_question(
        model,
        "🌍 Region",
        4,
        [
            {"text": "🇺🇸 USA", "price": 0},
            {"text": "🇪🇺 Europe", "price": 0},
            {"text": "🇯🇵 Japan", "price": -20},
            {"text": "🌏 Boshqa", "price": -40},
        ]
    )

    # 📦 BOX
    add_question(
        model,
        "📦 Karobkasi",
        5,
        [
            {"text": "Bor", "price": 25},
            {"text": "Yo‘q", "price": 0},
        ]
    )


models = [
    ("iPhone X",150),
    ("iPhone XR",180),
    ("iPhone XS",200),
    ("iPhone XS Max",230),
    ("iPhone 11",260),
    ("iPhone 11 Pro",320),
    ("iPhone 11 Pro Max",360),
    ("iPhone 12",340),
    ("iPhone 12 Pro",420),
    ("iPhone 12 Pro Max",470),
    ("iPhone 13",450),
    ("iPhone 13 Pro",560),
    ("iPhone 13 Pro Max",620),
    ("iPhone 14",580),
    ("iPhone 14 Plus",620),
    ("iPhone 14 Pro",700),
    ("iPhone 14 Pro Max",760),
    ("iPhone 15",720),
    ("iPhone 15 Plus",760),
    ("iPhone 15 Pro",880),
    ("iPhone 15 Pro Max",960),
    ("iPhone 16",820),
    ("iPhone 16 Pro",950),
    ("iPhone 16 Pro Max",1050),
    ("iPhone 17",900),
    ("iPhone 17 Pro",1100),
    ("iPhone 17 Pro Max",1200),
]


for i, m in enumerate(models, start=1):
    create_model(m[0], m[1], i)


print("✅ All iPhone models created successfully")