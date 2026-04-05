import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")
django.setup()

from bot.models import PricingNode


print("🧹 Old models clearing...")
PricingNode.objects.filter(type="model").delete()


def add_question(model, text, order, answers, allow_skip=False):
    q = PricingNode.objects.create(
        parent=model,
        type="question",
        text=text,
        order=order,
        allow_skip=allow_skip
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

    # 1 MEMORY
    add_question(
        model,
        "📦 Xotira hajmini tanlang",
        1,
        [
            {"text": "64GB", "price": 0},
            {"text": "128GB", "price": 40},
            {"text": "256GB", "price": 90},
            {"text": "512GB", "price": 180},
            {"text": "1TB", "price": 300},
        ]
    )

    # 2 BATTERY
    add_question(
        model,
        "🔋 Batareya holati",
        2,
        [
            {"text": "90-100%", "price": 0},
            {"text": "85-89%", "price": -30},
            {"text": "80-84%", "price": -60},
            {"text": "75-79%", "price": -100},
            {"text": "75% dan past", "price": -150},
        ]
    )

    # 3 SCREEN
    add_question(
        model,
        "📱 Ekran holati",
        3,
        [
            {"text": "Ideal ✨", "price": 0},
            {"text": "Mayda chizilgan", "price": -25},
            {"text": "Chuqur chizilgan", "price": -70},
            {"text": "Yorilgan", "price": -200},
        ]
    )

    # 4 FACE ID
    add_question(
        model,
        "🔐 FaceID ishlaydimi?",
        4,
        [
            {"text": "Ha ishlaydi ✅", "price": 0},
            {"text": "Ba'zan ishlaydi ⚠️", "price": -40},
            {"text": "Umuman ishlamaydi ❌", "price": -120},
        ]
    )

    # 5 CAMERA
    add_question(
        model,
        "📷 Kamera holati",
        5,
        [
            {"text": "Ideal", "price": 0},
            {"text": "Fokus muammosi", "price": -40},
            {"text": "Ishlamaydi", "price": -150},
        ]
    )

    # 6 BACK
    add_question(
        model,
        "🔎 Orqa korpus holati",
        6,
        [
            {"text": "Ideal", "price": 0},
            {"text": "Chizilgan", "price": -20},
            {"text": "Yorilgan", "price": -120},
        ]
    )

    # 7 BOX
    add_question(
        model,
        "📦 Qutisi bormi?",
        7,
        [
            {"text": "Ha bor", "price": 20},
            {"text": "Yo‘q", "price": 0},
        ]
    )

    # 8 COUNTRY
    add_question(
        model,
        "🌍 Telefon qaysi region?",
        8,
        [
            {"text": "USA 🇺🇸", "price": 0},
            {"text": "Japan 🇯🇵", "price": 0},
            {"text": "Europe 🇪🇺", "price": 0},
            {"text": "Boshqa", "price": -20},
        ]
    )

    # 9 SIM LOCK
    add_question(
        model,
        "📶 SIM lock bormi?",
        9,
        [
            {"text": "Factory unlocked", "price": 0},
            {"text": "Carrier lock", "price": -80},
        ]
    )

    # 10 EXTRA
    add_question(
        model,
        "📝 Qo‘shimcha holat",
        10,
        [
            {"text": "Juda toza ✨", "price": 40},
            {"text": "Oddiy ishlatilgan", "price": 0},
            {"text": "Kuchli ishlatilgan", "price": -80},
        ],
        allow_skip=True
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