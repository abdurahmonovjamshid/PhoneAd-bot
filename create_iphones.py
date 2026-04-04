import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")
django.setup()
from bot.models import PricingNode

# Clear old iPhone models (optional)
PricingNode.objects.filter(type="model").delete()

# =========================
# iPhone 15 Pro Max
# =========================
iphone_15_pro_max = PricingNode.objects.create(
    type="model",
    text="iPhone 15 Pro Max",
    price_change=1000,  # Base price
    order=1
)

# -------------------------
# Memory question
# -------------------------
memory_q = PricingNode.objects.create(
    parent=iphone_15_pro_max,
    type="question",
    text="Choose memory size",
    order=1
)

PricingNode.objects.create(parent=memory_q, type="answer", text="128GB", price_change=0, order=1)
PricingNode.objects.create(parent=memory_q, type="answer", text="256GB", price_change=100, order=2)
PricingNode.objects.create(parent=memory_q, type="answer", text="512GB", price_change=250, order=3)
PricingNode.objects.create(parent=memory_q, type="answer", text="1TB", price_change=400, order=4)

# -------------------------
# Color question
# -------------------------
color_q = PricingNode.objects.create(
    parent=iphone_15_pro_max,
    type="question",
    text="Select color",
    order=2
)

PricingNode.objects.create(parent=color_q, type="answer", text="Silver", price_change=0, order=1)
PricingNode.objects.create(parent=color_q, type="answer", text="Graphite", price_change=0, order=2)
PricingNode.objects.create(parent=color_q, type="answer", text="Gold", price_change=20, order=3)
PricingNode.objects.create(parent=color_q, type="answer", text="Blue", price_change=10, order=4)

# -------------------------
# Battery health question
# -------------------------
battery_q = PricingNode.objects.create(
    parent=iphone_15_pro_max,
    type="question",
    text="Battery health",
    order=3
)

PricingNode.objects.create(parent=battery_q, type="answer", text="Above 90%", price_change=0, order=1)
PricingNode.objects.create(parent=battery_q, type="answer", text="Below 90%", price_change=-50, order=2)

# -------------------------
# Box and accessories
# -------------------------
box_q = PricingNode.objects.create(
    parent=iphone_15_pro_max,
    type="question",
    text="Does the phone come with box?",
    order=4
)

PricingNode.objects.create(parent=box_q, type="answer", text="Yes", price_change=20, order=1)
PricingNode.objects.create(parent=box_q, type="answer", text="No", price_change=0, order=2)

# -------------------------
# Country of purchase
# -------------------------
country_q = PricingNode.objects.create(
    parent=iphone_15_pro_max,
    type="question",
    text="Country of purchase",
    order=5
)

PricingNode.objects.create(parent=country_q, type="answer", text="USA", price_change=0, order=1)
PricingNode.objects.create(parent=country_q, type="answer", text="Other", price_change=-10, order=2)

# -------------------------
# Additional info
# -------------------------
info_q = PricingNode.objects.create(
    parent=iphone_15_pro_max,
    type="question",
    text="Any extra info to mention?",
    order=6,
    allow_skip=True
)

PricingNode.objects.create(parent=info_q, type="answer", text="No scratches, perfect condition", price_change=50, order=1)
PricingNode.objects.create(parent=info_q, type="answer", text="Some scratches", price_change=-20, order=2)
PricingNode.objects.create(parent=info_q, type="answer", text="Minor screen crack", price_change=-100, order=3)
PricingNode.objects.create(parent=info_q, type="answer", text="Other defects", price_change=-150, order=4)

# =========================
# iPhone 15
# =========================
iphone_15 = PricingNode.objects.create(
    type="model",
    text="iPhone 15",
    price_change=800,
    order=2
)

# Reuse the same question types for simplicity
for parent_model in [iphone_15]:
    mem_q = PricingNode.objects.create(parent=parent_model, type="question", text="Choose memory size", order=1)
    PricingNode.objects.create(parent=mem_q, type="answer", text="128GB", price_change=0, order=1)
    PricingNode.objects.create(parent=mem_q, type="answer", text="256GB", price_change=100, order=2)
    PricingNode.objects.create(parent=mem_q, type="answer", text="512GB", price_change=250, order=3)

    col_q = PricingNode.objects.create(parent=parent_model, type="question", text="Select color", order=2)
    PricingNode.objects.create(parent=col_q, type="answer", text="Pink", price_change=0, order=1)
    PricingNode.objects.create(parent=col_q, type="answer", text="Green", price_change=0, order=2)
    PricingNode.objects.create(parent=col_q, type="answer", text="Blue", price_change=10, order=3)
    PricingNode.objects.create(parent=col_q, type="answer", text="Black", price_change=0, order=4)

    battery_q = PricingNode.objects.create(parent=parent_model, type="question", text="Battery health", order=3)
    PricingNode.objects.create(parent=battery_q, type="answer", text="Above 90%", price_change=0, order=1)
    PricingNode.objects.create(parent=battery_q, type="answer", text="Below 90%", price_change=-50, order=2)

    box_q = PricingNode.objects.create(parent=parent_model, type="question", text="Does the phone come with box?", order=4)
    PricingNode.objects.create(parent=box_q, type="answer", text="Yes", price_change=20, order=1)
    PricingNode.objects.create(parent=box_q, type="answer", text="No", price_change=0, order=2)

    country_q = PricingNode.objects.create(parent=parent_model, type="question", text="Country of purchase", order=5)
    PricingNode.objects.create(parent=country_q, type="answer", text="USA", price_change=0, order=1)
    PricingNode.objects.create(parent=country_q, type="answer", text="Other", price_change=-10, order=2)