import os
from flask import Blueprint, render_template, request, jsonify
from rag_system_oku_sorgu import create_document_store, run_user_query

# Chat Blueprint oluştur
chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat', methods=['GET'])
def chat():
    return render_template('chat.html', title='RAG Chat')

@chat_bp.route('/query', methods=['POST'])
def query():
    try:
        # Kullanıcı sorgusunu al
        user_query = request.json.get('query', '')
        
        if not user_query:
            return jsonify({'error': 'Sorgu boş olamaz'}), 400
        
        # Document store oluştur
        document_store = create_document_store()
        
        # Kullanıcı sorgusunu çalıştır
        result = run_user_query(document_store, user_query)
        
        # Yanıtı al
        if "answer" in result["router"]:
            answer = result["router"]["answer"]
        else:
            answer = "Bu soruya yanıt verebilmek için yeterli bilgi bulunamadı."
        
        return jsonify({'answer': answer})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500