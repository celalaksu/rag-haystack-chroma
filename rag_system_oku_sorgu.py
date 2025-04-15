import os
import sys
from dotenv import load_dotenv

# Haystack ve ChromaDB importları
from haystack_integrations.document_stores.chroma import ChromaDocumentStore

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

# ChromaDB belge deposu oluşturma
def create_document_store():
        
    document_store_r = ChromaDocumentStore(
        persist_path="db", 
        collection_name="pdf_documents",  # Mevcut koleksiyonu yeniden oluşturma
    )

    return document_store_r

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
    
    user_query = "Interrupt nedir? Kısaca açıklar mısın?"
    result = run_user_query(document_store, user_query)
    print(result["router"]["answer"])