"""Cloudinary integration service for media and static asset management."""
import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    CLOUDINARY_AVAILABLE = True
except ImportError:
    cloudinary = None
    CLOUDINARY_AVAILABLE = False


class CloudinaryService:
    """Service to upload and manage media assets on Cloudinary CDN with local fallback."""
    
    _initialized = False

    @classmethod
    def _init_cloudinary(cls):
        """Configure Cloudinary credentials from environment/app config."""
        if not CLOUDINARY_AVAILABLE or cloudinary is None:
            return False

        if cls._initialized:
            return cls.is_configured()

        # Check for CLOUDINARY_URL or explicit keys
        cloudinary_url = os.environ.get('CLOUDINARY_URL')
        cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
        api_key = os.environ.get('CLOUDINARY_API_KEY')
        api_secret = os.environ.get('CLOUDINARY_API_SECRET')

        if cloudinary_url:
            cloudinary.config()
            cls._initialized = True
        elif cloud_name and api_key and api_secret:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True
            )
            cls._initialized = True
        
        return cls.is_configured()

    @classmethod
    def is_configured(cls):
        """Check if Cloudinary has active credentials."""
        if not CLOUDINARY_AVAILABLE or cloudinary is None:
            return False
        config = cloudinary.config()
        return bool(config.cloud_name and (config.api_key or os.environ.get('CLOUDINARY_URL')))

    @classmethod
    def upload_file(cls, file_storage, folder='restaurant', public_id=None):
        """
        Upload a file (from request.files) to Cloudinary.
        If Cloudinary is not configured, gracefully falls back to local static uploads.
        
        :param file_storage: FileStorage object from Flask form submission
        :param folder: Cloudinary folder prefix (e.g. 'menu', 'categories', 'restaurant')
        :param public_id: Optional custom public identifier
        :return: Public HTTPS URL string of the uploaded asset
        """
        if not file_storage or not getattr(file_storage, 'filename', None):
            return None

        cls._init_cloudinary()

        # If Cloudinary is configured, upload to CDN
        if cls.is_configured() and cloudinary is not None:
            try:
                upload_params = {
                    'folder': f'royal_feast/{folder}',
                    'resource_type': 'image',
                    'quality': 'auto',
                    'fetch_format': 'auto',
                }
                if public_id:
                    upload_params['public_id'] = public_id

                result = cloudinary.uploader.upload(file_storage, **upload_params)
                return result.get('secure_url')
            except Exception as e:
                # Log error and fall back to local storage
                print(f"[Cloudinary Warning] Upload failed: {e}. Falling back to local storage.")

        # Fallback: Save to local static uploads folder
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        unique_name = f"{uuid.uuid4().hex[:12]}_{secure_filename(file_storage.filename)}"
        destination = os.path.join(upload_folder, unique_name)
        
        # Rewind file pointer if it was read
        file_storage.seek(0)
        file_storage.save(destination)
        
        return f'/static/uploads/{unique_name}'

    @classmethod
    def upload_bytes(cls, byte_stream, filename='qrcode.png', folder='qr_codes'):
        """
        Upload an in-memory byte buffer (like generated QR codes) to Cloudinary.
        Falls back to local file if Cloudinary is not configured.
        """
        cls._init_cloudinary()

        if cls.is_configured() and cloudinary is not None:
            try:
                byte_stream.seek(0)
                result = cloudinary.uploader.upload(
                    byte_stream,
                    folder=f'royal_feast/{folder}',
                    resource_type='image',
                    public_id=f"qr_{uuid.uuid4().hex[:8]}",
                    format='png'
                )
                return result.get('secure_url')
            except Exception as e:
                print(f"[Cloudinary Warning] QR upload failed: {e}")

        # Local fallback
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
        os.makedirs(upload_folder, exist_ok=True)
        unique_name = f"qr_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(upload_folder, unique_name)
        
        byte_stream.seek(0)
        with open(filepath, 'wb') as f:
            f.write(byte_stream.getvalue() if hasattr(byte_stream, 'getvalue') else byte_stream.read())
            
        return f'/static/uploads/{unique_name}'
