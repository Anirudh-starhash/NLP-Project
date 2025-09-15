from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from application.database import db
from application.models import User,PDFFile,PDFChunk
import google.generativeai as genai
from application.tasks import *

import os
from dotenv import load_dotenv

import time
load_dotenv()



chat_blueprint = Blueprint("chat", __name__)
@chat_blueprint.route("/prepare_document",methods=['POST'])
@jwt_required()
def prepare_document():
    
    """
        Generates summaries for each chunk of a document 
        and a final summary for the entire document.
    """
    
    current_user_id = get_jwt_identity()
    data = request.get_json()
    if not data or 'file_id' not in data:
        return jsonify({"error": "Missing file_id in request"}), 400

    file_id = data['file_id']

    # 2. Fetch the PDF record and its chunks, ensuring it belongs to the user
    pdf_record = PDFFile.query.filter_by(file_id=file_id, user_id=current_user_id).first()
    if not pdf_record:
        return jsonify({"error": "PDF not found or you do not have permission to access it"}), 404
    
    
    summarize_document_chunks.delay(file_id)
    question_generation.delay(file_id)

    # 3. Immediately respond to the user
    # A 202 "Accepted" status code is perfect for this.
    
    return jsonify({
        "message": "Document summarization and question generation has started. This may take a few minutes."
    }), 202
