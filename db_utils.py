import os
import hashlib
import chromadb
from chromadb.config import Settings
import datetime

# Veritabanı ayarları ve oluşturma
DB_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db')

# ChromaDB istemcisini başlat
def get_chroma_client():
    os.makedirs(DB_DIRECTORY, exist_ok=True)
    client = chromadb.PersistentClient(path=DB_DIRECTORY)
    return client

# Dosya hash koleksiyonu oluştur veya var olanı getir
def get_file_hash_collection():
    client = get_chroma_client()
    try:
        # Koleksiyonu getir, yoksa oluştur
        collection = client.get_or_create_collection(
            name="file_hashes",
            metadata={"description": "Uploaded files hash values"}
        )
        return collection
    except Exception as e:
        print(f"Collection error: {e}")
        return None

# URL koleksiyonu oluştur veya var olanı getir
def get_url_collection():
    client = get_chroma_client()
    try:
        # URL'ler için koleksiyonu getir, yoksa oluştur
        collection = client.get_or_create_collection(
            name="url_collection",
            metadata={"description": "Indexed web URLs"}
        )
        return collection
    except Exception as e:
        print(f"URL Collection error: {e}")
        return None

# Dosya hash değerini hesapla
def calculate_file_hash(file_path):
    """
    Verilen dosyanın SHA-256 hash değerini hesaplar
    """
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Dosyayı küçük parçalara bölerek hash hesapla (büyük dosyalar için)
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

# URL için hash değeri hesapla
def calculate_url_hash(url):
    """
    Verilen URL'nin MD5 hash değerini hesaplar
    """
    return hashlib.md5(url.encode('utf-8')).hexdigest()

# Hash değerini veritabanına kaydet
def save_hash_to_db(file_path, file_hash, filename):
    """
    Dosya hash değerini veritabanına kaydeder
    """
    collection = get_file_hash_collection()
    if collection:
        collection.add(
            ids=[file_hash],
            metadatas=[{
                "filename": filename,
                "path": file_path,
                "upload_date": os.path.getmtime(file_path)
            }],
            documents=[f"File: {filename}, Hash: {file_hash}"]
        )
        return True
    return False

# URL değerini veritabanına kaydet
def save_url_to_db(url):
    """
    URL'yi ChromaDB koleksiyonuna kaydeder
    """
    url_hash = calculate_url_hash(url)
    collection = get_url_collection()
    if collection:
        try:
            # URL'yi URL koleksiyonuna ekle
            collection.add(
                ids=[url_hash],
                metadatas=[{
                    "url": url,
                    "indexed_date": datetime.datetime.now().isoformat()
                }],
                documents=[f"URL: {url}"]
            )
            return True
        except Exception as e:
            print(f"URL kaydetme hatası: {e}")
            return False
    return False

# Dosya hash değerinin veritabanında olup olmadığını kontrol et
def is_hash_in_db(file_hash):
    """
    Dosya hash değeri veritabanında var mı kontrol eder
    """
    collection = get_file_hash_collection()
    if collection:
        results = collection.get(
            ids=[file_hash],
            include=["metadatas"]
        )
        # Eğer sonuç varsa (hash veritabanında varsa) True döner
        return len(results['ids']) > 0
    return False

# URL'nin veritabanında olup olmadığını kontrol et
def is_url_in_db(url):
    """
    URL veritabanında var mı kontrol eder
    """
    url_hash = calculate_url_hash(url)
    collection = get_url_collection()
    if collection:
        try:
            results = collection.get(
                ids=[url_hash],
                include=["metadatas"]
            )
            # Eğer sonuç varsa (URL veritabanında varsa) True döner
            return len(results['ids']) > 0
        except Exception as e:
            print(f"URL kontrol hatası: {e}")
            return False
    return False