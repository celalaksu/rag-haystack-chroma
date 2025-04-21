# Advanced RAG with Haystack and Chroma

Advanced Retrieval-Augmented Generation (RAG) sistemi, Haystack framework'ü ve ChromaDB vektör veritabanı kullanılarak geliştirilmiş bir bilgi erişim ve soru-cevap uygulaması.

## Proje Hakkında

Bu proje, farklı kaynaklardan (PDF dokümanlar, web siteleri) içerikleri alarak vektör veritabanında depolayan ve kullanıcı sorguları için bu içeriklerden ilgili bilgileri alarak, yapay zeka modeli (Google Gemini) ile entegre edip doğru ve bağlamsal cevaplar üreten bir RAG (Retrieval-Augmented Generation) sistemi oluşturmaktadır.

Sistem aşağıdaki temel işlevleri sağlar:

- **PDF İndeksleme**: Kullanıcılar PDF dosyalarını yükleyebilir ve bu dosyalar otomatik olarak işlenip vektör veritabanında indekslenir
- **Web İçeriği İndeksleme**: Kullanıcılar web sayfalarını tek tek ekleyebilir veya bir kök URL altındaki tüm sayfaları otomatik olarak tarayıp indeksleyebilir
- **Soru-Cevap Arayüzü**: İndekslenen bilgiler üzerinde sorgu yapabilme ve bağlamsal cevaplar alabilme imkanı
- **Çoklu Dil Desteği**: Kullanıcı sorgularını çevirerek farklı dillerde soru sorma ve cevap alma imkanı

## Teknolojiler

Proje aşağıdaki temel teknolojileri kullanmaktadır:

- **Flask**: Web uygulaması çerçevesi
- **Haystack AI**: RAG sistemini oluşturmak için kullanılan açık kaynak framework
- **ChromaDB**: Vektör veritabanı (belge gömmeleri için)
- **Google Gemini**: LLM modeli (soru cevaplama için)
- **Sentence Transformers**: Metin gömme işlemleri için kullanılan kütüphane
- **PyPDF2**: PDF dosyalarını işlemek için
- **BeautifulSoup ve Trafilatura**: Web sayfalarını işlemek için

## Proje Yapısı

```
rag-haystack-chroma/
├── app/                           # Web uygulaması frontend dosyaları
│   ├── static/                    # Statik dosyalar (CSS, JS)
│   └── templates/                 # HTML şablonları
├── db/                            # ChromaDB veritabanı dosyaları
├── uploads/                       # Yüklenen PDF dosyaları
├── app.py                         # Ana Flask uygulaması
├── chat.py                        # Sohbet işlevselliği
├── db_utils.py                    # Veritabanı yardımcı fonksiyonları
├── pdf_indexer.py                 # PDF indeksleme işlemleri
├── rag_system.py                  # RAG sistem temel fonksiyonları
├── rag_system_oku_sorgu.py        # Sorgu işleme için RAG sistemi
├── upload.py                      # Dosya yükleme işlemleri
├── url_analyzer.py                # URL analiz eden yardımcı fonksiyonlar
├── url_analyzer_routes.py         # URL analiz işleme rotaları
├── web_adres.py                   # Web sayfası indeksleme işlemleri
├── requirements.txt               # Proje bağımlılıkları
└── .env                           # Ortam değişkenleri (API anahtarları)
```

## Kurulum

### Gereksinimler

- Python 3.8 veya üzeri
- pip (Python paket yöneticisi)
- Gerekli API anahtarları (Google Gemini, SerperDev, DeepL)

### Adımlar

1. **Depoyu Klonlayın**
   ```bash
   git clone https://github.com/your-username/rag-haystack-chroma.git
   cd rag-haystack-chroma
   ```

2. **Sanal Ortam Oluşturun ve Aktifleştirin**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Gereksinimleri Yükleyin**
   ```bash
   pip install -r requirements.txt
   ```

4. **.env Dosyasını Yapılandırın**
   
   Projenin kök dizininde `.env` dosyası oluşturun ve aşağıdaki API anahtarlarını ekleyin:
   ```
   GOOGLE_API_KEY="your_google_api_key"
   SERPERDEV_API_KEY="your_serperdev_api_key"
   DEEPL_API_KEY="your_deepl_api_key"
   ```

5. **Uploads ve DB Klasörlerini Oluşturun**
   ```bash
   mkdir -p uploads db
   ```

6. **Uygulamayı Çalıştırın**
   ```bash
   flask run
   ```

   Uygulama varsayılan olarak http://127.0.0.1:5000/ adresinde çalışacaktır.

7. **Uygulamayı Kendiniz İçin Özelleştirin**

    Bu uygulama Rust Programlama Dili için hazırlanmıştır.
    Özelleştirmek için;
    ```rag_system_oku_sorgu.py``` dosyasındaki
    ```def create_system_promt():``` fonksiyonunda bulunan promtu kendiniz için değiştirin.
## Kullanım

### PDF İndeksleme

1. Ana sayfadan "PDF Yükle" butonuna tıklayın veya doğrudan `/upload` adresine gidin
2. Yüklemek istediğiniz PDF dosyasını seçin ve "Dosyayı Yükle" butonuna tıklayın
3. Dosya yüklendikten sonra "PDF Dosyasını İndeksle" butonuna tıklayarak indeksleme işlemini başlatın
4. İşlem tamamlandıktan sonra, indekslenen içerik üzerinde sorgu yapabilirsiniz

### Web Sitesi İndeksleme

#### Tek Sayfa Ekleme
1. Ana sayfadan "Web Kaynağı Ekle" butonuna tıklayın veya `/web_adres_ekle` adresine gidin
2. İndekslemek istediğiniz web sayfasının URL'sini girin
3. "Kaynağı Ekle" butonuna tıklayarak sayfayı analiz edin

#### URL Analizi ve Toplu İndeksleme
1. Bir URL girdiğinizde sistem otomatik olarak URL'yi analiz edecektir
2. Kök URL tespit edilir ve bu URL altındaki tüm HTML sayfalar listelenir
3. İndekslemek istediğiniz sayfaları seçin ve "Seçilen Sayfaları RAG Sistemine Ekle" butonuna tıklayın
4. İndeksleme işlemi arka planda çalışacak ve durum bilgileri size gösterilecektir

### RAG Sohbet

1. Ana sayfadan "Sohbet" butonuna tıklayın veya `/chat` adresine gidin
2. Sorunuzu yazın ve "Gönder" butonuna tıklayın
3. Sistem, indekslenen içeriklerden ilgili bilgileri bulup cevap üretecektir
4. Türkçe sorular otomatik olarak çevrilerek işlenir, cevaplar da doğru dilde sunulur

## Mimari

Bu RAG sistemi temel olarak şu adımlarla çalışır:

1. **İndeksleme Aşaması**:
   - Dokümanlar (PDF veya web içeriği) yüklenir
   - Dokümanlar daha küçük parçalara bölünür
   - Her parça için vektör gömmeleri oluşturulur (Sentence Transformers kullanılarak)
   - Gömmeler ve dokuman içerikleri ChromaDB'de saklanır

2. **Sorgu Aşaması**:
   - Kullanıcı sorusu alınır (gerekirse çevrilir)
   - Soru için vektör gömmesi oluşturulur
   - En benzer doküman parçaları ChromaDB'den getirilir
   - Doküman parçaları ve soruyla bir prompt oluşturulur
   - Google Gemini modeli, prompt'u işleyerek cevap üretir
   - Yetersiz içerik durumunda, web araması yapılır (SerperDev)
   - Cevap kullanıcıya sunulur

## Öne Çıkan Özellikler

- **Otomatik Web Tarama**: Bir ana URL'den başlayarak ilgili tüm sayfaları otomatik tarar
- **İçerik Filtreleme**: HTML olmayan içerikleri (CSS, JS vb.) otomatik filtreler
- **Arka Plan İşleme**: Büyük içerikleri arka planda işleyerek kullanıcı deneyimini kesintisiz tutar
- **İlerleme İzleme**: Uzun süren işlemlerde gerçek zamanlı ilerleme gösterir
- **Çeviri Entegrasyonu**: Farklı dillerdeki sorguları ve cevapları destekler
- **Dinamik Yanıt Geliştirme**: Yetersiz içerik durumunda web araması yaparak bilgileri zenginleştirir

## API Anahtarları

Sistem şu API anahtarlarını gerektirir:

- **Google Gemini API**: Metin üretimi için
- **SerperDev API**: Web aramaları için
- **DeepL API**: Çeviriler için (opsiyonel)

Bu anahtarları `.env` dosyasında yapılandırmanız gerekmektedir.

## Notlar

- ChromaDB veritabanı dosyaları büyük olabileceği için git deposuna dahil edilmemiştir (`db/` klasörü `.gitignore` dosyasında belirtilmiştir)
- Yüklenen PDF dosyaları da benzer şekilde git deposuna dahil edilmemiştir (`uploads/` klasörü)
- Dokümanlar, sorular ve cevapların dil özelliklerine göre yapılandırma yapmak için `rag_system_oku_sorgu.py` dosyasındaki prompt şablonunu düzenleyebilirsiniz

## Lisans

Bu proje açık kaynak olarak sunulmuştur. Detaylı lisans bilgileri için lütfen iletişime geçin.

## İletişim

Proje hakkında sorularınız için:
- E-posta: celalaksu@gmail.com
- GitHub: https://github.com/celalaksu
- Linkedin: https://www.linkedin.com/in/cllaksu/
- YouTube : https://www.youtube.com/@eemcs