"""Canned data used by the eval fakes — mirrors Sheets/*.csv."""

SERVICES = [
    {
        "service_id": "SVC001",
        "title": "Full Groom",
        "description": "Bath, brush, haircut, nails, ears.",
        "base_price": 50.0,
        "duration_min": 90,
        "breed_modifier_json": {"Poodle": 1.15, "Husky": 1.2, "Shih Tzu": 1.1},
        "weight_brackets_json": [
            {"min": 0, "max": 9.9, "mult": 1.0},
            {"min": 10, "max": 24.9, "mult": 1.2},
            {"min": 25, "max": 200, "mult": 1.4},
        ],
        "upsells_json": ["UPS001", "UPS002", "UPS003"],
    },
    {
        "service_id": "SVC002",
        "title": "Bath & Brush",
        "description": "Shampoo, blow-dry, brush out.",
        "base_price": 30.0,
        "duration_min": 60,
        "breed_modifier_json": {"Husky": 1.25, "German Shepherd": 1.15},
        "weight_brackets_json": [
            {"min": 0, "max": 9.9, "mult": 1.0},
            {"min": 10, "max": 24.9, "mult": 1.15},
            {"min": 25, "max": 200, "mult": 1.3},
        ],
        "upsells_json": ["UPS001", "UPS003"],
    },
    {
        "service_id": "SVC003",
        "title": "Nail Trim",
        "description": "Clip and file nails.",
        "base_price": 10.0,
        "duration_min": 15,
        "breed_modifier_json": {},
        "weight_brackets_json": [{"min": 0, "max": 200, "mult": 1.0}],
        "upsells_json": [],
    },
    {
        "service_id": "SVC004",
        "title": "De-shedding (Add-on)",
        "description": "Undercoat rake and de-shed treatment.",
        "base_price": 15.0,
        "duration_min": 20,
        "breed_modifier_json": {"Husky": 1.3, "German Shepherd": 1.2},
        "weight_brackets_json": [
            {"min": 0, "max": 9.9, "mult": 1.0},
            {"min": 10, "max": 24.9, "mult": 1.1},
            {"min": 25, "max": 200, "mult": 1.2},
        ],
        "upsells_json": [],
    },
]


BRAND_CONFIG = {
    "brand_id": "1234567890",
    "brand_name": "Paws & Relax",
    "welcome_copy": "Hey there! I can help you with quotes and bookings for dog grooming.",
    "hours": "Mon-Sat 9:00-18:00",
    "location": "DHA Phase 6, Karachi",
    "timezone": "Asia/Karachi",
    "upsells_json": [
        {"id": "UPS001", "title": "Teeth Brushing", "price": 7},
        {"id": "UPS002", "title": "Ear Cleaning", "price": 5},
        {"id": "UPS003", "title": "Paw Balm", "price": 4},
    ],
    "objection_snippets_json": {
        "price": "We keep pricing transparent and match to coat/weight so you pay a fair rate.",
        "time": "We can hold a slot for you and adjust if needed—no fee for 24h changes.",
        "anxious": "We do slow, gentle handling and can skip the dryer if your pup prefers.",
    },
}
