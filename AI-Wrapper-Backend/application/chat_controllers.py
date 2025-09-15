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


try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except KeyError:
    print("CRITICAL: GEMINI_API_KEY environment variable not set.")


    
def summarize_with_gemini(full_text: str) -> str:
    """
    Summarizes a long text using the Gemini 1.5 Pro API.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        prompt = f"Please provide a concise, well-structured summary of the following document:\n\n---\n\n{full_text}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"An error occurred during Gemini API call: {e}")
        raise e

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

    
    pdf_record = PDFFile.query.filter_by(file_id=file_id, user_id=current_user_id).first()
    if not pdf_record:
        return jsonify({"error": "PDF not found or you do not have permission to access it"}), 404
    
    summary_record = SummarizedPdfContent.query.filter_by(original_pdf_id=file_id, user_id=current_user_id).first()
    if summary_record:
        return jsonify({
            "message": "Summary already generated",
            "file_id": file_id,
            "summary": summary_record.summary_text
        }), 200

    try:
        full_text = ""
        with fitz.open(pdf_record.filepath) as doc:
            for page in doc:
                full_text += page.get_text()
                
        if not full_text.strip():
            return jsonify({"error": "Could not extract any text from the PDF."}), 400

        
        print(full_text)
        final_summary = summarize_with_gemini(full_text)
        
       
        new_summary = SummarizedPdfContent(
            user_id=current_user_id,
            original_pdf_id=file_id,
            summary_text=final_summary
        )
        
        db.session.add(new_summary)
        db.session.commit()
        
        return jsonify({
            "message": "Summary generated successfully.",
            "file_id": file_id,
            "summary": final_summary
        }), 200
    
    except Exception as e:
        print(f"Error during summarization: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500