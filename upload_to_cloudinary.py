"""Script to upload static media assets to Cloudinary and update database URLs."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

import cloudinary
import cloudinary.uploader
from app import create_app
from app.extensions import db
from app.models.restaurant import Restaurant
from app.models.category import Category
from app.models.menu_item import MenuItem
from app.services.qr_service import QRService

cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
api_key = os.environ.get('CLOUDINARY_API_KEY')
api_secret = os.environ.get('CLOUDINARY_API_SECRET')

if not cloud_name or not api_key or not api_secret:
    print("[ERROR] Cloudinary credentials missing in .env!")
    sys.exit(1)

cloudinary.config(
    cloud_name=cloud_name,
    api_key=api_key,
    api_secret=api_secret,
    secure=True
)

app = create_app('development')

with app.app_context():
    print(f"[*] Connected to Cloudinary Cloud: {cloud_name}")
    print("[*] Uploading static branding assets to Cloudinary...")

    # 1. Upload Restaurant Logo
    logo_path = os.path.join(app.root_path, 'static', 'img', 'restaurant-logo.png')
    logo_url = None
    if os.path.exists(logo_path):
        res = cloudinary.uploader.upload(
            logo_path,
            folder='royal_feast/branding',
            public_id='restaurant_logo',
            overwrite=True,
            resource_type='image'
        )
        logo_url = res.get('secure_url')
        print(f" -> Logo uploaded: {logo_url}")

    # 2. Upload Master Restaurant QR Code with embedded logo
    app_base_url = os.environ.get('APP_BASE_URL') or 'https://hotel-order-management-zdnb.onrender.com/'
    qr_buffer = QRService.generate_qr(app_base_url, logo_path=logo_path)
    res_qr = cloudinary.uploader.upload(
        qr_buffer,
        folder='royal_feast/branding',
        public_id='master_restaurant_qr',
        overwrite=True,
        resource_type='image',
        format='png'
    )
    qr_url = res_qr.get('secure_url')
    print(f" -> Master QR uploaded: {qr_url}")

    # 3. Update Restaurant record
    restaurant = Restaurant.query.first()
    if restaurant:
        if logo_url:
            restaurant.logo = logo_url
        if not restaurant.cover_image or 'unsplash' in restaurant.cover_image:
            # Upload a high-res cover banner
            try:
                cover_res = cloudinary.uploader.upload(
                    "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1600&q=85",
                    folder='royal_feast/branding',
                    public_id='cover_banner',
                    overwrite=True
                )
                restaurant.cover_image = cover_res.get('secure_url')
                print(f" -> Cover banner uploaded: {restaurant.cover_image}")
            except Exception as e:
                print(f" [!] Cover upload warning: {e}")
        db.session.commit()
        print("[OK] Restaurant profile updated with Cloudinary CDN assets.")

    # 4. Upload Category Images
    categories = Category.query.all()
    print(f"[*] Uploading {len(categories)} category images to Cloudinary...")
    for cat in categories:
        if cat.image and not ('res.cloudinary.com' in cat.image):
            try:
                slug = cat.name.lower().replace(' ', '_').replace('&', 'and')[:30]
                cat_res = cloudinary.uploader.upload(
                    cat.image,
                    folder='royal_feast/categories',
                    public_id=f"cat_{slug}",
                    overwrite=True
                )
                cat.image = cat_res.get('secure_url')
                print(f" -> Category '{cat.name}' uploaded to Cloudinary: {cat.image}")
            except Exception as e:
                print(f" [!] Category upload error for {cat.name}: {e}")
    db.session.commit()

    # 5. Upload Menu Item Images
    items = MenuItem.query.all()
    print(f"[*] Uploading {len(items)} menu item images to Cloudinary...")
    for item in items:
        if item.image and not ('res.cloudinary.com' in item.image):
            try:
                item_slug = "".join(c if c.isalnum() else '_' for c in item.name.lower())[:30]
                item_res = cloudinary.uploader.upload(
                    item.image,
                    folder='royal_feast/menu',
                    public_id=f"menu_{item_slug}",
                    overwrite=True
                )
                item.image = item_res.get('secure_url')
                print(f" -> Item '{item.name}' uploaded to Cloudinary: {item.image}")
            except Exception as e:
                print(f" [!] Menu upload error for {item.name}: {e}")
    db.session.commit()

    print("[SUCCESS] All static media and catalog assets uploaded to Cloudinary CDN and Neon DB updated!")

