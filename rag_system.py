import os
import sys
from pathlib import Path
from dotenv import load_dotenv


# Haystack ve ChromaDB importları
from haystack_integrations.document_stores.chroma import ChromaDocumentStore
from haystack.components.converters import PyPDFToDocument
from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.writers import DocumentWriter
from haystack import Pipeline


from haystack_integrations.components.retrievers.chroma import ChromaEmbeddingRetriever
from haystack_integrations.components.generators.google_ai import GoogleAIGeminiGenerator

# prompt temlate için
from haystack.dataclasses import ChatMessage
from haystack.components.routers import ConditionalRouter

# prompt pipeline için
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack.components.builders import ChatPromptBuilder
from haystack_integrations.components.generators.google_ai.chat.gemini import GoogleAIGeminiChatGenerator
from haystack.components.websearch import SerperDevWebSearch

# .env dosyasından API anahtarlarını yükle
load_dotenv()
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GEMINI_API_KEY:
    print("Hata: .env dosyasında GOOGLE_API_KEY bulunamadı!")
    sys.exit(1)

# Gemini modelini yapılandır
#genai.set_api_key(GEMINI_API_KEY)


# Dosya yolu sabitleri
# UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
# DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db', 'chroma_data')

# ChromaDB belge deposu oluşturma
def create_document_store():
    """ChromaDB belge deposu oluşturur."""
    # Belge deposu yoksa oluştur
    # os.makedirs(DB_DIR, exist_ok=True)
    
    try:
        document_store = ChromaDocumentStore(
            persist_path="db", 
            collection_name="pdf_documents"
            )
        print("Mevcut koleksiyon açıldı: pdf_documents")
    except Exception as e:
        print(f"Mevcut koleksiyon açılamadı, yeni oluşturuluyor: {e}")
        # Farklı bir koleksiyon adı kullan
        document_store = ChromaDocumentStore(
            persist_path="db", 
            collection_name="pdf_documents"  # Yeni koleksiyon oluştur
        )
        print(f"Yeni koleksiyon oluşturuldu: {document_store._collection_name}")
    return document_store

# RAG için Haystack pipeline oluşturma
def create_indexing_pipeline(document_store):
    """RAG sistemi için Haystack pipeline'ını oluşturur."""
    
    # Pipeline oluştur
    indexing_pipeline = Pipeline()
    indexing_pipeline.add_component(instance=PyPDFToDocument(), name="converter")
    indexing_pipeline.add_component(instance=DocumentCleaner(), name="cleaner")
    indexing_pipeline.add_component(instance=DocumentSplitter(split_by="sentence", split_length=5, split_overlap=1), name="splitter")
    indexing_pipeline.add_component(instance=SentenceTransformersDocumentEmbedder(model="sentence-transformers/all-mpnet-base-v2"), name="embedder")
    indexing_pipeline.add_component(instance=DocumentWriter(document_store = document_store), name="writer")
    
    indexing_pipeline.connect("converter.documents", "cleaner")
    #indexing_pipeline.connect("converter", "cleaner")
    indexing_pipeline.connect("cleaner", "splitter")
    indexing_pipeline.connect("splitter", "embedder")
    indexing_pipeline.connect("embedder", "writer")
    
    return indexing_pipeline

    
def process_pdf_pipeline(pipeline):
    #file_paths = ["uploads" / Path(name) for name in os.listdir("uploads")]    
    #pipeline.run({"converter": {"sources": file_paths}})
    
    
    
    pipeline.run({"converter": {"sources": ['uploads/Linux_Dagitimlarinin_Anatomisi.pdf']}})

# Belge deposuna PDF dosyasını ekleme
def index_process_pdf_file(document_store):
    """
    RAG sistemini oluşturur ve test eder.
    """
    print("RAG sistemini başlatıyorum...")

    
    # RAG pipeline'ını oluştur
    rag_pipeline = create_indexing_pipeline(document_store)
    print("RAG pipeline'ı oluşturuldu.")

    # PDF dosyasıni işle ve belge deposuna ekle
    process_pdf_pipeline(rag_pipeline)


########
#### SYSTEM PROMPT PIPELINE 
########

# prompt oluştur - system prompt
def create_system_promt():
    prompt_template = """
    {% if web_documents %}
        You were asked to answer the following query given the documents retrieved from documentation but the context was not enough.
        Answer the question based on the given context.
        If you have enough context to answer this question, return your answer with the used links.

        Here is the user question: {{ query }}
        Context:
        {% for document in web_documents %}
        URL: {{document.meta.link}}
        TEXT: {{document.content}}
        ---
        {% endfor %}
    {% else %}
        Answer the following query based on the documents retrieved from documentation.

        Documents:
        {% for document in documents %}
        {{document.content}}
        {% endfor %}

        Query: {{query}}

        If you have enough context to answer this question, just return your answer
        If you don't have enough context to answer, say 'NO_ANSWER'.
    {% endif %}
    """
    prompt = [ChatMessage.from_user(prompt_template)]
    
    return prompt

def create_route():
    main_routes = [
        {
            "condition": "{{'NO_ANSWER' in replies[0].text.replace('\n', '')}}",
            "output" :"{{query}}",
            "output_name": "go_web",
            "output_type": str,
        },
        {
            "condition": "{{'NO_ANSWER' not in replies[0].text.replace('\n', '')}}",
            "output": "{{replies[0].text}}",
            "output_name": "answer",
            "output_type": str,
        },
    ]
    
    return main_routes

def create_prompt_pipeline(document_store, prompt, main_routes):
    advanced_rag = Pipeline(max_runs_per_component=5)
    advanced_rag.add_component("embedder", SentenceTransformersTextEmbedder(model="sentence-transformers/all-mpnet-base-v2"))
    advanced_rag.add_component("retriever", ChromaEmbeddingRetriever(document_store=document_store, top_k=3))
    advanced_rag.add_component("prompt_builder", ChatPromptBuilder(template=prompt))
    # advanced_rag.add_component("llm", OllamaChatGenerator(model="gemma3:1b", url = "http://localhost:11434"))
    advanced_rag.add_component("llm", GoogleAIGeminiChatGenerator(model="gemini-2.0-flash"))
    advanced_rag.add_component("web_search", SerperDevWebSearch())
    advanced_rag.add_component("router", ConditionalRouter(main_routes))
    
    advanced_rag.connect("embedder", "retriever")
    advanced_rag.connect("retriever", "prompt_builder.documents")
    advanced_rag.connect("prompt_builder", "llm")
    advanced_rag.connect("llm.replies", "router.replies")
    advanced_rag.connect("router.go_web", "web_search.query")
    advanced_rag.connect("web_search.documents", "prompt_builder.web_documents")
    
    return advanced_rag


def run_user_query(document_store, user_query):
    system_prompt = create_system_promt()
    main_routes = create_route()
    advanced_rag = create_prompt_pipeline(document_store, system_prompt, main_routes)
    result = advanced_rag.run({"embedder":{"text":user_query}, "prompt_builder":{"query":user_query}, "router":{"query":user_query}})
    return result


if __name__ == "__main__":
    
    # Document store oluştur
    document_store = create_document_store()
    
    # pdf dosyasını chromaya indexle    
    # index_process_pdf_file(document_store)    
    
    # Kullanıcı sorgusunu çalıştır
    user_query = "Proses yönetimi nedir?"
    result = run_user_query(document_store, user_query)
    print(result["router"]["answer"])
