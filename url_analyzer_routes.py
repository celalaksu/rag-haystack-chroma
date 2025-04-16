from flask import Blueprint, render_template, request, jsonify, flash
from url_analyzer import analyze_url, find_urls_in_page, find_common_directory, crawl_domain_urls
import time

# Blueprint oluştur
url_analyzer_bp = Blueprint('url_analyzer', __name__)

@url_analyzer_bp.route('/url_analyzer', methods=['GET', 'POST'])
def url_analyzer():
    """URL analiz sayfası"""
    if request.method == 'POST':
        url = request.form.get('url')
        
        if not url or not url.startswith(('http://', 'https://')):
            flash('Geçerli bir URL girilmedi. URL "http://" veya "https://" ile başlamalıdır.', 'error')
            return render_template('url_analyzer.html', title='URL Analizi')
        
        try:
            start_time = time.time()
            
            # URL'yi analiz et
            results = analyze_url(url)
            
            # İşlem süresini hesapla
            process_time = round(time.time() - start_time, 2)
            
            return render_template('url_analyzer.html', 
                                  title='URL Analizi', 
                                  results=results,
                                  process_time=process_time,
                                  success=True)
            
        except Exception as e:
            flash(f'URL analizi sırasında bir hata oluştu: {str(e)}', 'error')
            return render_template('url_analyzer.html', 
                                  title='URL Analizi',
                                  success=False)
    
    # GET isteği için template göster
    return render_template('url_analyzer.html', title='URL Analizi')