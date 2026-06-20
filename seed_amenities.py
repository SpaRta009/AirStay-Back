# ─────────────────────────────────────────────────────────────────
# Script à exécuter une fois après la migration, pour pré-remplir
# les amenities "standard" (les icônes correspondent aux clés déjà
# présentes dans le composant <Icon /> de PropertyPage.tsx).
#
# Usage:
#   python manage.py shell < seed_amenities.py
# ─────────────────────────────────────────────────────────────────
from backEnd.models import Amenity  # ⚠️ remplace 'yourapp' par le nom réel de ton app

STANDARD_AMENITIES = [
    ("Wifi", "wifi"),
    ("55\" HDTV", "tv"),
    ("Full kitchen", "kitchen"),
    ("Washer & Dryer", "wash"),
    ("Air conditioning", "ac"),
    ("Free parking", "park"),
    ("Private pool", "pool"),
    ("Gym", "gym"),
]

for name, icon in STANDARD_AMENITIES:
    Amenity.objects.get_or_create(name=name, defaults={"icon": icon, "is_custom": False})

print(f"{Amenity.objects.count()} amenities en base.")