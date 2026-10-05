"""Database seeding script with realistic restaurant data."""
from app import create_app
from app.extensions import db
from app.models.role import Role
from app.models.user import User
from app.models.restaurant import Restaurant
from app.models.token import Token
from app.models.category import Category
from app.models.menu_item import MenuItem

app = create_app()

def seed_database():
    with app.app_context():
        print("Creating all database tables...")
        db.create_all()

        # 1. Create Roles
        roles_data = [
            ('super_admin', 'Full system access and configurations'),
            ('admin', 'Restaurant manager and billing operator'),
            ('kitchen', 'Kitchen staff for food preparation'),
            ('waiter', 'Serving staff for food delivery to tokens'),
            ('customer', 'Dining customer'),
        ]
        roles = {}
        for role_name, description in roles_data:
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                role = Role(name=role_name, description=description)
                db.session.add(role)
                db.session.flush()
            roles[role_name] = role

        # 2. Create Default Users
        users_data = [
            ('admin', 'admin@royalfeast.com', 'admin123', 'Rajesh Sharma (Admin)', roles['admin']),
            ('kitchen', 'kitchen@royalfeast.com', 'kitchen123', 'Chef Sanjeev Kumar', roles['kitchen']),
            ('waiter', 'waiter@royalfeast.com', 'waiter123', 'Rohan Verma (Captain)', roles['waiter']),
            ('waiter2', 'waiter2@royalfeast.com', 'waiter123', 'Amit Patel', roles['waiter']),
        ]
        for username, email, password, full_name, role in users_data:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    role_id=role.id,
                    is_active=True
                )
                user.set_password(password)
                db.session.add(user)
                print(f"Created user: {username} ({role.name})")

        # 3. Create Restaurant
        restaurant = Restaurant.query.first()
        if not restaurant:
            restaurant = Restaurant(
                name="The Royal Feast Bistro",
                description="Experience artisanal gastronomy, royal Mughlai delicacies, wood-fired gourmet pizzas, and signature refreshing craft mocktails.",
                phone="+91 98765 43210",
                email="contact@royalfeast.com",
                address="42 Gourmet Boulevard, Connaught Place, New Delhi",
                gst_number="07AAAAA0000A1Z5",
                cuisine_type="North Indian, Continental, Pan-Asian & Gourmet Desserts",
                opening_time="11:00",
                closing_time="23:30",
                is_open=True,
                tax_percent=5.0,
                service_charge_percent=5.0,
                logo="/static/img/restaurant-logo.png",
                cover_image="https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1200&q=80"
            )
            db.session.add(restaurant)
            print("Created restaurant profile.")

        # 4. Create 40 Dine-in / Order Tokens
        existing_tokens = Token.query.count()
        if existing_tokens < 40:
            for num in range(1, 41):
                if not Token.query.filter_by(token_number=num).first():
                    tok = Token(token_number=num, is_enabled=True, status='available')
                    db.session.add(tok)
            print("Generated 40 order tokens (1 to 40).")

        # 5. Create Categories
        categories_data = [
            ("Starters & Appetizers", "Crispy, savory delights to kickstart your feast", 1, "https://images.unsplash.com/photo-1541544741938-0af808871cc0?w=600&q=80"),
            ("Tandoori & Kebabs", "Slow-smoked in traditional clay ovens with fragrant spices", 2, "https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?w=600&q=80"),
            ("Main Course", "Rich gravies, paneer specialties and slow-simmered curries", 3, "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600&q=80"),
            ("Biryani & Rice", "Long-grain aged basmati layered with herbs and aromatic saffron", 4, "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&q=80"),
            ("Artisanal Breads", "Fluffy tandoori naans, stuffed kulchas and parathas", 5, "https://images.unsplash.com/photo-1626074353765-517a681e40be?w=600&q=80"),
            ("Gourmet Pizzas & Burgers", "Hand-stretched crusts and juicy handcrafted patties", 6, "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600&q=80"),
            ("Desserts & Sweets", "Decadent handcrafted desserts to end on a sweet note", 7, "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=600&q=80"),
            ("Beverages & Mocktails", "Chilled artisanal sodas, fresh shakes, and coolers", 8, "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=600&q=80")
        ]

        categories_map = {}
        for cat_name, desc, order_num, img in categories_data:
            cat = Category.query.filter_by(name=cat_name).first()
            if not cat:
                cat = Category(name=cat_name, description=desc, display_order=order_num, image=img, is_active=True)
                db.session.add(cat)
                db.session.flush()
            categories_map[cat_name] = cat
        print("Created categories.")

        # 6. Create Menu Items
        menu_items_data = [
            # Starters
            {
                "category": "Starters & Appetizers",
                "name": "Crispy Corn & Water Chestnut Salt 'n Pepper",
                "description": "Tender American corn and crunchy water chestnuts tossed with crushed black pepper, scallions, and roasted garlic.",
                "price": 280,
                "discount_price": 249,
                "is_veg": True,
                "is_popular": True,
                "is_featured": True,
                "is_spicy": False,
                "prep_time": 12,
                "rating": 4.8,
                "image": "https://images.unsplash.com/photo-1541544741938-0af808871cc0?w=600&q=80"
            },
            {
                "category": "Starters & Appetizers",
                "name": "Dahi Ke Sholay (Curd Croquettes)",
                "description": "Golden crispy bread rolls stuffed with spiced hung curd, bell peppers, fresh mint, and pomegranate pearls.",
                "price": 310,
                "discount_price": 285,
                "is_veg": True,
                "is_popular": True,
                "is_featured": False,
                "is_spicy": False,
                "prep_time": 15,
                "rating": 4.9,
                "image": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&q=80"
            },
            {
                "category": "Starters & Appetizers",
                "name": "Chili Garlic Prawns",
                "description": "Succulent prawns seared with burnt garlic, fiery bird's eye chilies, cilantro, and lemon butter glaze.",
                "price": 490,
                "discount_price": None,
                "is_veg": False,
                "is_popular": True,
                "is_featured": True,
                "is_spicy": True,
                "prep_time": 16,
                "rating": 4.7,
                "image": "https://images.unsplash.com/photo-1559742811-822873691df8?w=600&q=80"
            },
            # Kebabs
            {
                "category": "Tandoori & Kebabs",
                "name": "Bhatti Da Murgh Tikka",
                "description": "Boneless chicken thighs marinated overnight in smoky Kashmiri red chillies, mustard oil, and malt vinegar.",
                "price": 420,
                "discount_price": 380,
                "is_veg": False,
                "is_popular": True,
                "is_featured": True,
                "is_spicy": True,
                "prep_time": 18,
                "rating": 4.9,
                "image": "https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?w=600&q=80"
            },
            {
                "category": "Tandoori & Kebabs",
                "name": "Paneer Tikka Angara",
                "description": "Cubes of farm-fresh cottage cheese infused with smoked ajwain, curd marinade, charred capsicum, and onion bulbs.",
                "price": 360,
                "discount_price": 320,
                "is_veg": True,
                "is_popular": True,
                "is_featured": False,
                "is_spicy": True,
                "prep_time": 15,
                "rating": 4.8,
                "image": "https://images.unsplash.com/photo-1567188040759-fb8a883dc6d8?w=600&q=80"
            },
            {
                "category": "Tandoori & Kebabs",
                "name": "Galouti Kebab Sliders",
                "description": "Mouth-melting minced lamb kebabs scented with rose water and 32 potli spices, served on mini saffron parathas.",
                "price": 520,
                "discount_price": 475,
                "is_veg": False,
                "is_popular": False,
                "is_featured": True,
                "is_spicy": False,
                "prep_time": 20,
                "rating": 4.9,
                "image": "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?w=600&q=80"
            },
            # Main Course
            {
                "category": "Main Course",
                "name": "Dal Makhani 24-Hour Dum",
                "description": "Black lentils slow-simmered on low clay coal flame with butter, rich cream, and plum tomatoes for 24 hours.",
                "price": 340,
                "discount_price": 299,
                "is_veg": True,
                "is_popular": True,
                "is_featured": True,
                "is_spicy": False,
                "prep_time": 10,
                "rating": 5.0,
                "image": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600&q=80"
            },
            {
                "category": "Main Course",
                "name": "Old Delhi Butter Chicken",
                "description": "Char-grilled shredded chicken steeped in velvet satin tomato gravy with dried fenugreek leaves and golden butter.",
                "price": 460,
                "discount_price": 410,
                "is_veg": False,
                "is_popular": True,
                "is_featured": True,
                "is_spicy": False,
                "prep_time": 15,
                "rating": 4.9,
                "image": "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?w=600&q=80"
            },
            {
                "category": "Main Course",
                "name": "Paneer Lababdar",
                "description": "Creamy cottage cheese simmered in spiced onion-cashew-tomato masala with grated cottage cheese garnish.",
                "price": 380,
                "discount_price": 345,
                "is_veg": True,
                "is_popular": True,
                "is_featured": False,
                "is_spicy": False,
                "prep_time": 15,
                "rating": 4.7,
                "image": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=600&q=80"
            },
            # Biryani
            {
                "category": "Biryani & Rice",
                "name": "Royal Dum Gosht Biryani",
                "description": "Fragrant long-grain aged Basmati rice layered with prime cuts of tender goat meat, brown onions, mint, and pure saffron.",
                "price": 540,
                "discount_price": 490,
                "is_veg": False,
                "is_popular": True,
                "is_featured": True,
                "is_spicy": True,
                "prep_time": 20,
                "rating": 4.9,
                "image": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&q=80"
            },
            {
                "category": "Biryani & Rice",
                "name": "Hyderabadi Subz Dum Biryani",
                "description": "Fresh baby vegetables, paneer cubes, and mint cooked in sealed handi with fragrant rice and kewra water.",
                "price": 350,
                "discount_price": 310,
                "is_veg": True,
                "is_popular": True,
                "is_featured": False,
                "is_spicy": True,
                "prep_time": 18,
                "rating": 4.7,
                "image": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=600&q=80"
            },
            # Breads
            {
                "category": "Artisanal Breads",
                "name": "Chur Chur Naan Platter",
                "description": "Flaky, multi-layered tandoori bread crushed with desi ghee, served with spiced chole and onion relish.",
                "price": 180,
                "discount_price": 155,
                "is_veg": True,
                "is_popular": True,
                "is_featured": False,
                "is_spicy": False,
                "prep_time": 10,
                "rating": 4.8,
                "image": "https://images.unsplash.com/photo-1626074353765-517a681e40be?w=600&q=80"
            },
            {
                "category": "Artisanal Breads",
                "name": "Garlic Butter Truffle Naan",
                "description": "Clay oven baked flatbread brushed with garlic butter and finished with a hint of white truffle oil.",
                "price": 120,
                "discount_price": None,
                "is_veg": True,
                "is_popular": True,
                "is_featured": True,
                "is_spicy": False,
                "prep_time": 8,
                "rating": 4.9,
                "image": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&q=80"
            },
            # Pizzas & Burgers
            {
                "category": "Gourmet Pizzas & Burgers",
                "name": "Wood-Fired Truffle Funghi Pizza",
                "description": "San Marzano sauce, fresh Fior di Latte mozzarella, wild portobello mushrooms, thyme, and truffle drizzle.",
                "price": 520,
                "discount_price": 460,
                "is_veg": True,
                "is_popular": True,
                "is_featured": True,
                "is_spicy": False,
                "prep_time": 18,
                "rating": 4.9,
                "image": "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600&q=80"
            },
            {
                "category": "Gourmet Pizzas & Burgers",
                "name": "Smoked Peri-Peri Chicken Burger",
                "description": "Crispy panko-crusted chicken fillet tossed in African peri-peri glaze, house slaw, and cheddar in toasted brioche bun.",
                "price": 380,
                "discount_price": 340,
                "is_veg": False,
                "is_popular": True,
                "is_featured": False,
                "is_spicy": True,
                "prep_time": 15,
                "rating": 4.8,
                "image": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&q=80"
            },
            # Desserts
            {
                "category": "Desserts & Sweets",
                "name": "Molten Chocolate Lava Cake with Gelato",
                "description": "Warm Belgian dark chocolate cake with a gooey flowing center, paired with Madagascar vanilla bean gelato.",
                "price": 290,
                "discount_price": 250,
                "is_veg": True,
                "is_popular": True,
                "is_featured": True,
                "is_spicy": False,
                "prep_time": 12,
                "rating": 4.9,
                "image": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=600&q=80"
            },
            {
                "category": "Desserts & Sweets",
                "name": "Saffron Pistachio Kesar Phirni",
                "description": "Creamy ground rice pudding slow-reduced with whole milk, saffron strands, and roasted Iranian pistachios.",
                "price": 220,
                "discount_price": 190,
                "is_veg": True,
                "is_popular": False,
                "is_featured": False,
                "is_spicy": False,
                "prep_time": 8,
                "rating": 4.7,
                "image": "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=600&q=80"
            },
            # Beverages
            {
                "category": "Beverages & Mocktails",
                "name": "Passion Fruit Mint Sparkler",
                "description": "Tropical passion fruit puree, hand-muddled garden mint, sparkling water, lime, and crushed ice.",
                "price": 190,
                "discount_price": 160,
                "is_veg": True,
                "is_popular": True,
                "is_featured": True,
                "is_spicy": False,
                "prep_time": 5,
                "rating": 4.8,
                "image": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=600&q=80"
            },
            {
                "category": "Beverages & Mocktails",
                "name": "Signature Cold Brew Hazelnut Frappe",
                "description": "16-hour steeped Arabica cold brew blended with roasted hazelnut cream and topped with cocoa dusting.",
                "price": 240,
                "discount_price": 210,
                "is_veg": True,
                "is_popular": True,
                "is_featured": False,
                "is_spicy": False,
                "prep_time": 5,
                "rating": 4.9,
                "image": "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=600&q=80"
            }
        ]

        for item_data in menu_items_data:
            cat = categories_map.get(item_data["category"])
            if not cat:
                continue
            item = MenuItem.query.filter_by(name=item_data["name"]).first()
            if not item:
                item = MenuItem(
                    name=item_data["name"],
                    description=item_data["description"],
                    price=item_data["price"],
                    discount_price=item_data["discount_price"],
                    category_id=cat.id,
                    image=item_data["image"],
                    is_veg=item_data["is_veg"],
                    is_available=True,
                    is_popular=item_data["is_popular"],
                    is_featured=item_data["is_featured"],
                    is_spicy=item_data["is_spicy"],
                    preparation_time=item_data["prep_time"],
                    rating=item_data["rating"]
                )
                db.session.add(item)

        db.session.commit()
        print("Database seeded successfully with initial data!")

if __name__ == '__main__':
    seed_database()
