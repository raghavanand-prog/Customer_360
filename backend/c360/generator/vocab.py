"""Committed local vocabulary for the synthetic data generator.

No network calls, no third-party "faker" dependency: every list here is
inlined so that generation is fully reproducible and offline (§5.1).
"""
from __future__ import annotations

FIRST_NAMES = [
    "Raghav", "Priya", "Arjun", "Neha", "Aditya", "Ananya", "Rohit", "Kavya",
    "Vikram", "Meera", "Sanjay", "Divya", "Karan", "Pooja", "Rahul", "Sneha",
    "Amit", "Nisha", "Vivek", "Anjali", "Suresh", "Deepa", "Manish", "Ritu",
    "Arun", "Shreya", "Nikhil", "Swati", "Gaurav", "Isha", "Varun", "Aarti",
    "Siddharth", "Pallavi", "Kunal", "Simran", "Abhishek", "Tanvi", "Rajesh",
    "Kritika", "Harsh", "Radhika", "Naveen", "Aishwarya", "Vishal", "Bhavna",
    "Akash", "Preeti", "Manoj", "Shalini",
]

LAST_NAMES = [
    "Sharma", "Anand", "Rao", "Gupta", "Iyer", "Kumar", "Reddy", "Singh",
    "Patel", "Nair", "Menon", "Joshi", "Verma", "Mehta", "Das", "Bose",
    "Chatterjee", "Pillai", "Agarwal", "Malhotra", "Kapoor", "Bhat", "Shetty",
    "Desai", "Chauhan", "Rana", "Saxena", "Sinha", "Trivedi", "Yadav",
]

DIMINUTIVES = {
    "raghav": {"raghu"}, "arjun": {"raju"}, "vikram": {"vicky"},
    "priya": {"pri"}, "rajesh": {"raju"}, "abhishek": {"abhi"},
    "aditya": {"adi"}, "nikhil": {"nikki"}, "shreya": {"shrey"},
}

CITY_WEIGHTS = [
    ("Bengaluru", "Karnataka", 0.16), ("Mumbai", "Maharashtra", 0.14),
    ("Pune", "Maharashtra", 0.10), ("Chennai", "Tamil Nadu", 0.10),
    ("Hyderabad", "Telangana", 0.10), ("Delhi", "Delhi", 0.12),
    ("Kolkata", "West Bengal", 0.07), ("Ahmedabad", "Gujarat", 0.06),
    ("Jaipur", "Rajasthan", 0.05), ("Kochi", "Kerala", 0.05),
    ("Chandigarh", "Chandigarh", 0.05),
]

# Deliberately seeded country-name variants for a single logical country.
COUNTRY_VARIANTS = ["India", "INDIA", "india ", "IN", "Bharat"]
CANONICAL_COUNTRY = "IN"

EMAIL_DOMAINS = [
    ("example.com", 0.55), ("example.net", 0.25), ("mail.example", 0.15),
    ("corp.example", 0.05),
]

GENERIC_EMAIL_LOCALS = [
    "info", "admin", "support", "noreply", "no-reply", "sales", "contact",
    "help", "billing", "hello", "office",
]

CATEGORY_NAMES = [
    "Audio", "Kitchen", "Fitness", "Mobile Accessories", "Home Decor",
    "Footwear", "Apparel", "Beauty", "Books", "Toys", "Stationery", "Bags",
]

PRODUCT_NOUNS = {
    "Audio": ["Wireless Earbuds", "Over-Ear Headphones", "Bluetooth Speaker",
              "Soundbar", "Neckband Earphones"],
    "Kitchen": ["Steel Cookware Set", "Non-Stick Pan", "Electric Kettle",
                "Mixer Grinder", "Air Fryer"],
    "Fitness": ["Yoga Mat", "Resistance Bands", "Dumbbell Set",
                "Fitness Tracker", "Skipping Rope"],
    "Mobile Accessories": ["Phone Case", "Screen Protector", "Power Bank",
                            "USB-C Cable", "Car Mount"],
    "Home Decor": ["Wall Clock", "Table Lamp", "Photo Frame Set",
                   "Wall Art Canvas", "Scented Candle Set"],
    "Footwear": ["Running Shoes", "Casual Sneakers", "Sandals",
                 "Formal Shoes", "Flip Flops"],
    "Apparel": ["Cotton T-Shirt", "Denim Jacket", "Track Pants",
                "Formal Shirt", "Hoodie"],
    "Beauty": ["Face Wash", "Moisturiser", "Lipstick", "Sunscreen",
               "Hair Serum"],
    "Books": ["Novel", "Cookbook", "Self-Help Book", "Comic Collection",
              "Biography"],
    "Toys": ["Building Blocks", "Remote Control Car", "Puzzle Set",
             "Soft Toy", "Board Game"],
    "Stationery": ["Notebook Set", "Fountain Pen", "Sketch Kit",
                   "Desk Organiser", "Sticky Notes Pack"],
    "Bags": ["Backpack", "Laptop Sleeve", "Tote Bag", "Duffel Bag",
             "Wallet"],
}

BRANDS = ["Acme", "HomeCo", "Zenith", "Northline", "Bluewave", "Craftly",
          "Urbanix", "Solace", "Vertex", "Pinehall"]

TICKET_SUBJECTS = {
    "delivery": ["Order not delivered", "Delivery delayed",
                 "Wrong address delivery"],
    "refund": ["Refund not processed", "Requesting refund for return"],
    "product_quality": ["Item arrived damaged", "Product defect"],
    "payment": ["Payment failed but amount deducted", "Duplicate charge"],
    "account": ["Unable to log in", "Update account details"],
    "other": ["General enquiry", "Feedback on service"],
}

CAMPAIGN_NAMES = [
    "Festive Season Sale", "New Arrivals", "Weekend Flash Sale",
    "Category Spotlight: Audio", "Loyalty Member Exclusive",
    "Cart Reminder", "Winback Offer", "Monsoon Essentials",
]
