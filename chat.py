import os
from flask import Blueprint, render_template, request, jsonify
from rag_system_oku_sorgu import create_document_store, run_user_query

from deepl_haystack import DeepLTextTranslator
from dotenv import load_dotenv
import sys
import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.codehilite import CodeHiliteExtension

# using docling converter to convert llm answer to markdown
# from docling_haystack.converter import DoclingConverter, ExportType

load_dotenv()
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
if not DEEPL_API_KEY:
    print("Hata: .env dosyasında DEEPL_API_KEY bulunamadı!")
    sys.exit(1)

# Chat Blueprint oluştur
chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat', methods=['GET'])
def chat():
    return render_template('chat.html', title='RAG Chat')

@chat_bp.route('/query', methods=['POST'])
def query():
    try:
        # Kullanıcı sorgusunu al - ensure request.json is not None
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON verisi bulunamadı!'}), 400
            
        user_query_tr = data.get('query', '')
        
        if not user_query_tr:
            return jsonify({'error': 'Sorgu boş olamaz!'}), 400
        
        translator = DeepLTextTranslator(target_lang="EN-US")
        
        user_query_en = translator.run(user_query_tr)
        user_query = user_query_en["translation"]
        print("====================================")
        print("====================================")

        print(f"Kullanıcı sorgusu: {user_query_tr}")
        print(f"çeviiri : {user_query_en}")
        
        print(f"Kullanıcı sorgusu: {user_query}")
        # Document store oluştur
        document_store = create_document_store()
        
        # Kullanıcı sorgusunu çalıştır
        result = run_user_query(document_store, user_query)
        
        # Yanıtı al
        if "answer" in result["router"]:
            answer = result["router"]["answer"]
            # Convert markdown text to HTML with extensions for code blocks
            answer_html = markdown.markdown(
                answer, 
                extensions=[
                    FencedCodeExtension(),
                    CodeHiliteExtension(use_pygments=True)
                ]
            )
            # Return both raw markdown and HTML versions
            return jsonify({'answer': answer, 'answer_html': answer_html})
        else:
            answer = "Bu soruya yanıt verebilmek için yeterli bilgi bulunamadı."
            return jsonify({'answer': answer, 'answer_html': answer})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500