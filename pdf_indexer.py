import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import time
from pathlib import Path

# rag_system.py dosyasından gerekli fonksiyonları import et
from rag_system import create_document_store, create_indexing_pipeline

# Blueprint oluştur
pdf_indexer_bp = Blueprint('pdf_indexer', __name__)

@pdf_indexer_bp.route('/pdf_embedding', methods=['GET', 'POST'])
def pdf_embedding():
    if request.method == 'GET':
        # Yüklenen dosya yolunu al
        file_path = request.args.get('file_path')
        
        if not file_path or not os.path.exists(file_path):
            flash('Geçerli bir dosya yolu belirtilmedi.', 'error')
            return redirect(url_for('upload.upload'))
            
        # Dosya yolunu session'da sakla ve form sayfasını göster
        session['file_path'] = file_path
        filename = os.path.basename(file_path)
        
        return render_template('pdf_embedding.html', 
                           file_path=file_path,
                           filename=filename,
                           title='PDF İndeksleme - Hazır')
    else:
        # POST metodu ile işlemi başlat
        file_path = session.get('file_path')
        
        if not file_path or not os.path.exists(file_path):
            flash('Geçerli bir dosya yolu belirtilmedi.', 'error')
            return redirect(url_for('upload.upload'))
        
        try:
            # İşlemi başlat
            start_time = time.time()
            
            # Document store oluştur
            document_store = create_document_store()
            
            # İndeksleme pipeline'ını oluştur
            indexing_pipeline = create_indexing_pipeline(document_store)
            
            # PDF dosyasını işle
            file_paths = [file_path]
            result = indexing_pipeline.run({"converter": {"sources": file_paths}})
            
            # İşlem süresini hesapla
            end_time = time.time()
            processing_time = round(end_time - start_time, 2)
            
            # Eğer writer component sonuçları içeriyorsa, belge sayısını al
            if "writer" in result and "documents_written" in result["writer"]:
                document_count = result["writer"]["documents_written"]
            else:
                # Aksi takdirde, splitter'dan çıkan doküman sayısını al
                document_count = len(result.get("splitter", {}).get("documents", []))
            
            # Başarı mesajı göster
            return render_template('pdf_embedding.html', 
                               success=True, 
                               message=f'Dosya başarıyla indekslendi!',
                               processing_time=processing_time,
                               document_count=document_count,
                               filename=os.path.basename(file_path),
                               title='PDF İndeksleme - Tamamlandı')
            
        except Exception as e:
            # Hata durumunda kullanıcıya bilgi ver
            return render_template('pdf_embedding.html', 
                               success=False, 
                               message=f'İndeksleme sırasında bir hata oluştu: {str(e)}',
                               title='PDF İndeksleme - Hata')