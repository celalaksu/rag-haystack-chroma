from flask import Blueprint, render_template, request, current_app
import os
import datetime
from werkzeug.utils import secure_filename
from db_utils import calculate_file_hash, is_hash_in_db, save_hash_to_db

# Create Blueprint for upload functionality
upload_bp = Blueprint('upload', __name__)

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

# Function to check if file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Configure upload directory
def get_upload_folder():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

# Create uploads directory if it doesn't exist
def ensure_upload_dir():
    os.makedirs(get_upload_folder(), exist_ok=True)

# Function to generate a unique filename if the file already exists
def generate_unique_filename(filename):
    name, ext = os.path.splitext(filename)
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{name}_{timestamp}{ext}"

@upload_bp.route('/upload', methods=['GET'])
def upload():
    return render_template('upload.html', title='Dosya Yükle')

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return render_template('upload.html', message='Dosya seçilmedi', success=False, title='Dosya Yükle')
    
    file = request.files['file']
    
    if file.filename == '':
        return render_template('upload.html', message='Dosya seçilmedi', success=False, title='Dosya Yükle')
    
    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        filename = original_filename
        upload_folder = get_upload_folder()
        file_path = os.path.join(upload_folder, filename)
        
        # If file with the same name exists, generate a unique filename
        if os.path.exists(file_path):
            filename = generate_unique_filename(original_filename)
            file_path = os.path.join(upload_folder, filename)
        
        # Önce dosyayı geçici olarak kaydet, hash hesapla ve kontrol et
        temp_file_path = os.path.join(upload_folder, f"temp_{filename}")
        file.save(temp_file_path)
        
        # Dosyanın hash değerini hesapla
        file_hash = calculate_file_hash(temp_file_path)
        
        # Hash değeri veritabanında var mı kontrol et
        if is_hash_in_db(file_hash):
            # Geçici dosyayı sil
            os.remove(temp_file_path)
            return render_template('upload.html',
                               message='Bu dosya içeriği zaten yüklenmiş. Aynı içeriğe sahip dosya tekrar yüklenemez.',
                               success=False,
                               title='Dosya Yükle')
        
        # Dosyayı gerçek adıyla kaydet
        os.rename(temp_file_path, file_path)
        
        # Hash değerini veritabanına kaydet
        save_hash_to_db(file_path, file_hash, filename)
        
        description = request.form.get('description', '')
        
        # If filename was changed, inform user
        if filename != original_filename:
            message = f'Aynı isimli dosya zaten mevcut. Dosyanız farklı bir isimle kaydedildi: {filename}'
        else:
            message = f'Dosya başarıyla yüklendi: {filename}'
            
        return render_template('upload.html', 
                           message=message, 
                           success=True,
                           title='Dosya Yükle')
    else:
        return render_template('upload.html',
                           message='Sadece PDF ve DOCX dosyaları yükleyebilirsiniz.',
                           success=False,
                           title='Dosya Yükle')