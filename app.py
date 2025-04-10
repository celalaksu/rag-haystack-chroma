from flask import Flask, render_template
import os
from upload import upload_bp, ensure_upload_dir

app = Flask(__name__, 
            static_folder='app/static',
            template_folder='app/templates')

# Configure the upload folder
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Register the upload blueprint
app.register_blueprint(upload_bp)

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