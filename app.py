from flask import Flask, render_template
import os
from upload import upload_bp, ensure_upload_dir
from pdf_indexer import pdf_indexer_bp
from chat import chat_bp

app = Flask(__name__, 
            static_folder='app/static',
            template_folder='app/templates')

# Configure the upload folder - Dosya boyutu sınırını artır
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit

# Session için secret key ekle
app.secret_key = 'rag-haystack-chroma-secret-key'  

# Register the blueprints
app.register_blueprint(upload_bp)
app.register_blueprint(pdf_indexer_bp)
app.register_blueprint(chat_bp)

# Ensure upload directory exists
ensure_upload_dir()

@app.route('/')
def index():
    return render_template('index.html', title='Flask App with Jinja')

@app.route('/about')
def about():
    return render_template('about.html', title='About')

if __name__ == '__main__':
    app.run(debug=True)