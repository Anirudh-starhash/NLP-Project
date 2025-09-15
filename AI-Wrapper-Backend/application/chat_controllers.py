from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from application.database import db
from application.models import User,PDFFile,PDFChunk,SummarizedPdfContent
import google.generativeai as genai
from application.tasks import *

import os
from dotenv import load_dotenv

import time
load_dotenv()
import fitz



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
    
    
    if not os.path.exists(pdf_record.file_path): # Check if the file actually exists
         return jsonify({"error": "PDF file not found on server."}), 404

    
    try:
        full_text=""
        
        with fitz.open(pdf_record.file_path) as doc:
            for page in doc:
                full_text+=page.get_text()
                
        if not full_text.strip():
             return jsonify({"error": "Could not extract any text from the PDF."}), 400
         
        summarizer=pipeline("summarization",model="sshleifer/distilbart-cnn-12-6")
        
        #summary result
        summary_result=summarizer(full_text,max_length=250,min_length=40,do_sample=False)
        final_summary=summary_result[0]['summary_text']
        
        summary=SummarizedPdfContent(
            user_id=current_user_id,
            original_pdf_id=file_id,
            summary_text=final_summary
        )
        db.session.add(summary)
        db.session.commit()
        
    
        return jsonify({
            "message": "Summary generated successfully.",
            "file_id": file_id,
            "summary": final_summary
        }), 200
    
    
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred during summarization: {str(e)}"}), 500

