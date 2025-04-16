from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import os
from werkzeug.urls import url_parse

# Haystack importları
from haystack_integrations.document_stores.chroma import ChromaDocumentStore
from haystack import Pipeline
from haystack.components.converters import HTMLToDocument
from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.writers import DocumentWriter
from haystack.components.fetchers import LinkContentFetcher

# Veritabanı işlemleri için - ChromaDB fonksiyonları
from db_utils import calculate_url_hash, is_url_in_db, save_url_to_db

# Blueprint oluştur
web_adres_bp = Blueprint('web_adres', __name__)

# URL geçerliliğini kontrol et
def is_valid_url(url):
    # Basit URL doğrulama
    parsed_url = url_parse(url)
    return bool(parsed_url.scheme and parsed_url.netloc)

# Document store oluştur
def create_document_store():
    try:
        document_store = ChromaDocumentStore(
            persist_path="db", 
            collection_name="pdf_documents"  # PDF'ler ve web içeriği aynı koleksiyonda
        )
        print("Mevcut koleksiyon açıldı: pdf_documents")
    except Exception as e:
        print(f"Mevcut koleksiyon açılamadı, yeni oluşturuluyor: {e}")
        document_store = ChromaDocumentStore(
            persist_path="db", 
            collection_name="pdf_documents"
        )
    return document_store

# Web sayfası indeksleme pipeline'ı
def create_web_indexing_pipeline(document_store):
    indexing_pipeline = Pipeline()
    indexing_pipeline.add_component(instance=LinkContentFetcher(), name="fetcher")
    indexing_pipeline.add_component(instance=HTMLToDocument(), name="converter")
    indexing_pipeline.add_component(instance=DocumentCleaner(), name="cleaner")
    indexing_pipeline.add_component(instance=DocumentSplitter(split_by="sentence", split_length=5, split_overlap=1), name="splitter")
    indexing_pipeline.add_component(instance=SentenceTransformersDocumentEmbedder(model="sentence-transformers/all-mpnet-base-v2"), name="embedder")
    indexing_pipeline.add_component(instance=DocumentWriter(document_store=document_store), name="writer")
    
    indexing_pipeline.connect("fetcher.streams", "converter.sources")
    indexing_pipeline.connect("converter.documents", "cleaner")
    indexing_pipeline.connect("cleaner", "splitter")
    indexing_pipeline.connect("splitter", "embedder")
    indexing_pipeline.connect("embedder", "writer")
    
    return indexing_pipeline

# Flask route'ları
@web_adres_bp.route('/web_adres_ekle', methods=['GET', 'POST'])
def web_adres_ekle():
    if request.method == 'POST':
        url = request.form.get('url')
        
        # URL doğrulama
        if not url or not is_valid_url(url):
            flash('Geçerli bir URL girilmedi.', 'error')
            return render_template('web_adres_ekle.html', success=False, message='Geçerli bir URL girilmedi.', title='Web Kaynağı Ekle')
        
        # URL daha önce eklenmiş mi kontrol et - ChromaDB kullanarak
        if is_url_in_db(url):
            flash('Bu URL zaten sisteme eklenmiş.', 'error')
            return render_template('web_adres_ekle.html', success=False, message='Bu URL zaten sisteme eklenmiş.', title='Web Kaynağı Ekle')
        
        try:
            # Document store oluştur
            document_store = create_document_store()
            
            # Web indeksleme pipeline'ını oluştur
            indexing_pipeline = create_web_indexing_pipeline(document_store)
            
            # URL'yi indeksle
            result = indexing_pipeline.run({
                "fetcher": {
                    "urls": [url]
                }
            })
            
            # İndeksleme başarılı ise URL'yi ChromaDB'ye kaydet
            if result.get("writer", {}).get("documents_written", 0) > 0:
                save_url_to_db(url)
                document_count = result["writer"]["documents_written"]
                flash(f'Web sayfası başarıyla indekslendi! {document_count} belge oluşturuldu.', 'success')
                return render_template('web_adres_ekle.html', 
                                      success=True, 
                                      message=f'Web sayfası başarıyla indekslendi! {document_count} belge oluşturuldu.', 
                                      title='Web Kaynağı Ekle')
            else:
                flash('Web sayfası indekslenirken bir sorun oluştu. İçerik bulunamadı.', 'error')
                return render_template('web_adres_ekle.html', 
                                      success=False, 
                                      message='Web sayfası indekslenirken bir sorun oluştu. İçerik bulunamadı.', 
                                      title='Web Kaynağı Ekle')
                
        except Exception as e:
            flash(f'Web sayfası indekslenirken bir hata oluştu: {str(e)}', 'error')
            return render_template('web_adres_ekle.html', 
                                  success=False, 
                                  message=f'Web sayfası indekslenirken bir hata oluştu: {str(e)}', 
                                  title='Web Kaynağı Ekle')
    
    # GET isteği için template'i göster
    return render_template('web_adres_ekle.html', title='Web Kaynağı Ekle')