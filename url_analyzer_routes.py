from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from url_analyzer import analyze_url, find_urls_in_page, find_common_directory, crawl_domain_urls
import time
from db_utils import is_root_url_in_db, save_root_url_to_db, save_url_to_db
from web_adres import create_document_store, create_web_indexing_pipeline
import threading

# Blueprint oluştur
url_analyzer_bp = Blueprint('url_analyzer', __name__)

# Global değişkenler
indexing_status = {}
indexing_threads = {}

@url_analyzer_bp.route('/url_analyzer', methods=['GET', 'POST'])
def url_analyzer():
    """URL analiz sayfası"""
    # URL parametresi doğrudan URL'den alınabilir (GET isteği ile)
    url = request.args.get('url')
    
    # POST isteği varsa ve URL yoksa, formdan al
    if request.method == 'POST' and not url:
        url = request.form.get('url')
    
    # URL varsa analiz et
    if url:
        if not url.startswith(('http://', 'https://')):
            flash('Geçerli bir URL girilmedi. URL "http://" veya "https://" ile başlamalıdır.', 'error')
            return render_template('url_analyzer.html', title='URL Analizi')
        
        try:
            start_time = time.time()
            
            # URL'yi analiz et
            results = analyze_url(url)
            
            # İşlem süresini hesapla
            process_time = round(time.time() - start_time, 2)
            
            # Kök URL'leri kontrol et
            for root_url in results['root_urls']:
                # Kök URL daha önce indekslenmiş mi?
                if is_root_url_in_db(root_url):
                    flash(f'Bu kök URL ({root_url}) daha önce indekslenmiş.', 'warning')
            
            return render_template('url_analyzer.html', 
                                  title='URL Analizi', 
                                  results=results,
                                  process_time=process_time,
                                  success=True,
                                  hide_form=True)  # Girdi formunu gizle
            
        except Exception as e:
            flash(f'URL analizi sırasında bir hata oluştu: {str(e)}', 'error')
            return render_template('url_analyzer.html', 
                                  title='URL Analizi',
                                  success=False)
    
    # URL yoksa ve GET isteği ise, template'i göster
    return render_template('url_analyzer.html', title='URL Analizi')

@url_analyzer_bp.route('/index_all_urls', methods=['POST'])
def index_all_urls():
    """Tüm URL'leri indeksle"""
    urls = request.form.getlist('urls')
    root_url = request.form.get('root_url')
    
    if not urls or not root_url:
        flash('İndekslenecek URL veya kök URL bulunamadı.', 'error')
        return redirect(url_for('index'))
    
    # Kök URL daha önce indekslenmiş mi kontrol et
    if is_root_url_in_db(root_url):
        flash(f'Bu kök URL ({root_url}) daha önce indekslenmiş ve işlenmiş.', 'warning')
        return redirect(url_for('index'))
    
    # Benzersiz bir indeksleme ID'si oluştur
    index_id = str(int(time.time()))
    
    # Başlangıç durumu
    indexing_status[index_id] = {
        'total': len(urls),
        'processed': 0,
        'success': 0,
        'errors': 0,
        'completed': False,
        'messages': []
    }
    
    # Arkaplanda indeksleme işlemini başlat
    indexing_thread = threading.Thread(
        target=index_urls_background,
        args=(index_id, urls, root_url)
    )
    indexing_thread.daemon = True
    indexing_threads[index_id] = indexing_thread
    indexing_thread.start()
    
    # Kullanıcıyı indeksleme durum sayfasına yönlendir
    return redirect(url_for('url_analyzer.indexing_status_page', index_id=index_id))
    
@url_analyzer_bp.route('/indexing_status/<index_id>')
def indexing_status_page(index_id):
    """İndeksleme durumu sayfası"""
    if index_id not in indexing_status:
        flash('Belirtilen indeksleme işlemi bulunamadı.', 'error')
        return redirect(url_for('index'))
    
    return render_template('indexing_status.html', 
                          title='İndeksleme Durumu',
                          index_id=index_id,
                          status=indexing_status[index_id])

@url_analyzer_bp.route('/get_indexing_status/<index_id>')
def get_indexing_status(index_id):
    """İndeksleme durumunu JSON olarak döndür"""
    if index_id not in indexing_status:
        return jsonify({"error": "İndeksleme işlemi bulunamadı"}), 404
    
    return jsonify(indexing_status[index_id])

def index_urls_background(index_id, urls, root_url):
    """Arkaplanda URL'leri indeksle"""
    try:
        # Document store oluştur
        document_store = create_document_store()
        
        # Web indeksleme pipeline'ını oluştur
        indexing_pipeline = create_web_indexing_pipeline(document_store)
        
        # Önce kök URL'yi veritabanına kaydet
        save_root_url_to_db(root_url)
        indexing_status[index_id]['messages'].append(f"Kök URL '{root_url}' kaydedildi.")
        
        # Her URL'yi indeksle
        for i, url in enumerate(urls):
            try:
                # İndeksleme durumunu güncelle
                indexing_status[index_id]['processed'] = i + 1
                
                # URL'yi indeksle
                result = indexing_pipeline.run({
                    "fetcher": {
                        "urls": [url]
                    }
                })
                
                # İndeksleme başarılı ise URL'yi ChromaDB'ye kaydet
                documents_written = result.get("writer", {}).get("documents_written", 0)
                if documents_written > 0:
                    save_url_to_db(url)
                    indexing_status[index_id]['success'] += 1
                    indexing_status[index_id]['messages'].append(
                        f"✅ {url} başarıyla indekslendi ({documents_written} belge)."
                    )
                else:
                    indexing_status[index_id]['errors'] += 1
                    indexing_status[index_id]['messages'].append(
                        f"❌ {url} indekslenemedi: İçerik bulunamadı."
                    )
            except Exception as e:
                indexing_status[index_id]['errors'] += 1
                indexing_status[index_id]['messages'].append(
                    f"❌ {url} indekslenirken hata: {str(e)}"
                )
        
        indexing_status[index_id]['completed'] = True
        indexing_status[index_id]['messages'].append(
            f"✅ İndeksleme tamamlandı! {indexing_status[index_id]['success']} URL başarıyla indekslendi, "
            f"{indexing_status[index_id]['errors']} URL'de hata oluştu."
        )
        
    except Exception as e:
        indexing_status[index_id]['messages'].append(f"❌ İndeksleme işlemi sırasında genel hata: {str(e)}")
        indexing_status[index_id]['completed'] = True