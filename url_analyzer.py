import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urldefrag
import re
import concurrent.futures
import os.path
from collections import defaultdict

def get_domain(url):
    """URL'nin domain kısmını döndürür."""
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"

def get_directory_path(url):
    """
    URL'nin dizin yolunu döndürür.
    Örneğin: https://doc.rust-lang.org/stable/book/css/chrome.css
    için https://doc.rust-lang.org/stable/book/ döndürür
    """
    # Önce URL'den # kısmını temizle
    url_without_fragment = urldefrag(url).url
    
    parsed_url = urlparse(url_without_fragment)
    
    # URL'nin path kısmını al
    path = parsed_url.path
    
    # Eğer path bir dosya ise, dizin kısmını al
    if '.' in os.path.basename(path):
        path = os.path.dirname(path)
    
    # Path'in sonuna / ekle (eğer yoksa)
    if not path.endswith('/'):
        path += '/'
    
    # Tam URL olarak döndür
    return f"{parsed_url.scheme}://{parsed_url.netloc}{path}"

def clean_url(url):
    """
    URL'den fragment kısmını (#...) temizler.
    
    Args:
        url: Temizlenecek URL
    
    Returns:
        str: Fragment temizlenmiş URL
    """
    return urldefrag(url).url

def get_path_depth(url):
    """
    URL'nin path derinliğini hesaplar.
    Örneğin: https://example.com/a/b/c.html -> 3
    
    Args:
        url: Derinliği hesaplanacak URL
    
    Returns:
        int: Path derinliği
    """
    parsed_url = urlparse(url)
    path = parsed_url.path.strip('/')
    if not path:
        return 0
    
    # Dosya adını path derinliğine dahil etme
    if '.' in os.path.basename(path) and '/' in path:
        path = os.path.dirname(path)
    
    # Path'i / karakterine göre bölerek derinliği bul
    parts = [p for p in path.split('/') if p]
    return len(parts)

def get_path_sort_key(url, root_url):
    """
    URL'yi path sırasına göre sıralama için bir anahtar döndürür.
    
    Args:
        url: Sıralanacak URL
        root_url: Kök URL
    
    Returns:
        tuple: Sıralama için anahtar değer
    """
    # URL'den root_url'yi çıkar
    if url.startswith(root_url):
        relative_path = url[len(root_url):]
    else:
        # Eğer root_url ile başlamıyorsa, normal URL'yi kullan
        relative_path = urlparse(url).path
    
    # Dosya adı ve uzantıyı ayır
    path_parts = relative_path.strip('/').split('/')
    
    # İndex dosyalarını öne al, diğerlerini alfabetik sırala
    is_index = 0
    if path_parts and path_parts[-1] in ['index.html', 'index.htm', '']:
        is_index = -1  # index dosyası ise daha öne sırala
    
    return (
        get_path_depth(url),  # Önce derinliğe göre sırala (daha az derinlik önce)
        path_parts[:-1] if path_parts else [],  # Sonra dizin yoluna göre sırala
        is_index,  # Sonra index dosyalarını öne al
        path_parts[-1] if path_parts else ''  # Son olarak dosya adına göre sırala
    )

def sort_urls_by_path(urls, root_url):
    """
    URL'leri path yapısına göre sıralar. Kök URL'ye yakın olanlar önce gelir.
    İndex dosyaları (index.html gibi) her dizinde ilk sırada olur.
    
    Args:
        urls: Sıralanacak URL listesi
        root_url: Kök URL
        
    Returns:
        list: Path yapısına göre sıralanmış URL listesi
    """
    # URL'lerin geçerli olduğundan emin ol
    valid_urls = [u for u in urls if u]
    
    # URL'leri path yapısına göre sırala
    return sorted(valid_urls, key=lambda u: get_path_sort_key(u, root_url))

def find_common_directory(urls, original_url):
    """
    Verilen URL listesinde en çok tekrar eden dizin yolunu bulur.
    Dizinleri en spesifik olandan (en derin) en genele doğru analiz eder.
    Kullanıcının verdiği orijinal URL ile aynı domain'de olmalıdır.
    
    Args:
        urls: URL listesi
        original_url: Kullanıcının verdiği orijinal URL
    
    Returns:
        str: Tespit edilen en yaygın kök dizin
    """
    if not urls:
        return get_directory_path(original_url)
    
    # Orijinal URL'nin domain'ini al
    original_domain = get_domain(original_url)
    
    # Orijinal URL ile aynı domain'deki URL'leri filtrele
    same_domain_urls = [url for url in urls if get_domain(url) == original_domain]
    
    if not same_domain_urls:
        return get_directory_path(original_url)
    
    # Her URL'nin dizin yolunu çıkar
    directory_paths = [get_directory_path(url) for url in same_domain_urls]
    
    # Dizin yollarının sıklığını hesapla
    dir_count = defaultdict(int)
    for path in directory_paths:
        dir_count[path] += 1
    
    # En yaygın dizin yolunu bul
    common_dirs = sorted(dir_count.items(), key=lambda x: x[1], reverse=True)
    
    if not common_dirs:
        return get_directory_path(original_url)
    
    return common_dirs[0][0]

def find_urls_in_page(url, limit=50):
    """
    Verilen URL'deki sayfada bulunan linkleri çeker.
    
    Args:
        url: Çözümlenecek sayfa URL'si
        limit: Maksimum link sayısı (varsayılan: 50)
    
    Returns:
        list: Bulunan URL'lerin listesi
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = set()  # Tekrar eden URL'leri engellemek için set kullan
        
        # Tüm <a> etiketlerindeki linkleri topla
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if href and not href.startswith('#') and not href.startswith('javascript:'):
                full_url = urljoin(url, href)  # Göreceli URL'leri mutlak URL'lere dönüştür
                
                # URL'den fragment kısmını (#...) temizle
                full_url = clean_url(full_url)
                
                # Aynı domain içindeki linkler ve HTTP(S) linklerini filtrele
                if full_url.startswith(('http://', 'https://')):
                    links.add(full_url)
        
        # Ekstra URL'ler için sayfadaki diğer potansiyel URL'leri de kontrol et
        for link_elem in soup.find_all(['link', 'script', 'img', 'iframe']):
            if link_elem.has_attr('src'):
                src = link_elem['src']
                full_url = urljoin(url, src)
                full_url = clean_url(full_url)  # Fragment'i temizle
                if full_url.startswith(('http://', 'https://')):
                    links.add(full_url)
            elif link_elem.has_attr('href'):
                href = link_elem['href']
                full_url = urljoin(url, href)
                full_url = clean_url(full_url)  # Fragment'i temizle
                if full_url.startswith(('http://', 'https://')):
                    links.add(full_url)
        
        # Set'i listeye çevir ve limit uygula
        return list(links)[:limit]
    
    except Exception as e:
        print(f"URL çözümleme hatası: {str(e)}")
        return []

def is_html_url(url):
    """
    URL'nin bir HTML sayfası olup olmadığını kontrol eder.
    
    Args:
        url: Kontrol edilecek URL
    
    Returns:
        bool: URL bir HTML sayfası ise True, değilse False
    """
    # URL'nin path kısmını al
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    
    # Uzantı kontrolü
    if path.endswith(('.html', '.htm')):
        return True
    
    # Uzantısı olmayan ve / ile biten veya hiç path olmayan URL'leri de HTML kabul et
    if path == "" or path.endswith('/'):
        return True
    
    # Yaygın olmayan HTML dosya formatlarını dışarıda tut
    non_html_extensions = ('.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.svg', 
                           '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar',
                           '.mp3', '.mp4', '.avi', '.mov', '.json', '.xml', '.txt')
    
    if any(path.endswith(ext) for ext in non_html_extensions):
        return False
    
    # Eğer uzantı yoksa veya tanınmayan bir uzantı ise, HEAD isteği göndererek content type'ı kontrol et
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.head(url, headers=headers, timeout=5)
        
        # Content-Type kontrol et
        content_type = response.headers.get('Content-Type', '').lower()
        return 'text/html' in content_type
    except:
        # Herhangi bir hata durumunda, varsayılan olarak HTML kabul etme
        return False

def crawl_domain_urls(root_url, max_urls=200, max_depth=5, html_only=True):
    """
    Kök URL altındaki bütün URL'leri bulur.
    
    Args:
        root_url: Kök URL
        max_urls: Maksimum URL sayısı (varsayılan: 200)
        max_depth: Maksimum derinlik seviyesi (varsayılan: 5)
        html_only: Sadece HTML sayfalarını dahil et
    
    Returns:
        list: Bulunan URL'lerin listesi
    """
    visited = set()
    to_visit = [root_url]
    all_urls = []
    current_depth = 0
    url_without_fragments = set()  # Fragment temizlenmiş URL'leri tutmak için
    
    while to_visit and len(all_urls) < max_urls and current_depth < max_depth:
        current_depth += 1
        current_level = to_visit.copy()
        to_visit = []
        
        print(f"Tarama Derinliği {current_depth}: {len(current_level)} URL inceleniyor...")
        
        # Paralel olarak URL'leri çözümle
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_url = {executor.submit(find_urls_in_page, url, 50): url for url in current_level if url not in visited}
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                visited.add(url)
                
                # URL'yi all_urls'e eklerken HTML filtreleme yap
                # Ayrıca URL'nin fragment temizlenmiş halinin daha önce eklenip eklenmediğini kontrol et
                clean_current_url = clean_url(url)
                if (url.startswith(root_url) and 
                    (not html_only or is_html_url(url)) and 
                    clean_current_url not in url_without_fragments):
                    
                    all_urls.append(clean_current_url)
                    url_without_fragments.add(clean_current_url)
                
                try:
                    new_urls = future.result()
                    # Sadece aynı kök URL'deki URL'leri ekle
                    for new_url in new_urls:
                        new_url_clean = clean_url(new_url)  # Fragment'i temizle
                        if (new_url_clean.startswith(root_url) and 
                            new_url_clean not in visited and 
                            new_url_clean not in to_visit and
                            new_url_clean not in url_without_fragments):
                            # Eğer html_only aktif ise ve URL bir HTML değilse, ziyaret edilecek listeye ekleme
                            if not html_only or is_html_url(new_url_clean):
                                to_visit.append(new_url_clean)
                except Exception as e:
                    print(f"URL işleme hatası: {str(e)}")
        
        print(f"Derinlik {current_depth}: {len(all_urls)} HTML URL bulundu, {len(to_visit)} URL ziyaret edilecek")
        
        if not to_visit:
            break
    
    print(f"Toplam {len(all_urls)} benzersiz URL bulundu (max_urls={max_urls}, mevcut_derinlik={current_depth})")
    
    # URL'leri path yapısına göre sırala
    sorted_urls = sort_urls_by_path(all_urls, root_url)
    
    return sorted_urls

def analyze_url(url):
    """
    Verilen URL'yi analiz eder, sayfa içindeki linkleri bulur,
    kök URL'yi tespit eder ve kök URL altındaki sayfaları tarar.
    
    Args:
        url: Analiz edilecek URL
    
    Returns:
        dict: Analiz sonuçları
    """
    # URL'den fragment kısmını temizle
    url = clean_url(url)
    
    result = {
        'original_url': url,
        'page_urls': [],
        'root_urls': [],
        'crawled_urls': [],
        'html_urls': []  # Sadece HTML URL'leri ayrıca sakla
    }
    
    # 1. Sayfadaki 20 URL'yi al
    page_urls = find_urls_in_page(url, limit=20)
    result['page_urls'] = page_urls
    
    print(f"Bulunan URL sayısı: {len(page_urls)}")  # Debug için
    
    # 2. Kök URL'yi tespit et - sadece kullanıcının verdiği URL'nin olduğu domain'de
    root_url = find_common_directory(page_urls, url)
    result['root_urls'] = [root_url]
    
    print(f"Tespit edilen kök URL: {root_url}")
    
    # 3. Kök URL altındaki sayfaları tara - sadece HTML sayfalarını dahil et
    # URL sayısı ve derinlik sınırını artırarak daha fazla URL bul
    crawled_urls = crawl_domain_urls(root_url, max_urls=200, max_depth=5, html_only=True)
    result['crawled_urls'] = crawled_urls
    
    # HTML URL'leri ayrı bir liste olarak da sakla ve path yapısına göre sırala
    html_urls = [url for url in crawled_urls if is_html_url(url)]
    result['html_urls'] = sort_urls_by_path(html_urls, root_url)
    
    return result