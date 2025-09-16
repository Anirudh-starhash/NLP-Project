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
import faiss
import numpy as np
THRESHOLD_DISTANCE = 0.6


try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except KeyError:
    print("CRITICAL: GEMINI_API_KEY environment variable not set.")


    
def summarize_with_gemini(full_text: str) -> str:
    """
    Summarizes a long text using the Gemini 1.5 Pro API.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        #prompt = f"Please provide a concise, well-structured summary of the following document:\n\n---\n\n{full_text}"
        prompt = f"""
        You are an expert at summarizing long documents. Please read the following document carefully and generate a detailed summary.

        Requirements:
        1. The summary should be around 500 to 1000 words.
        2. Present the summary in well-structured bullet points or numbered lists.
        3. Highlight key sections, findings, and important details.
        4. Ensure the summary is coherent and easy to understand.

        Here is the document:

        ---
        {full_text}
        """
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
    


@chat_blueprint.route('/query_document', methods=['POST'])
@jwt_required()
def query_document():
    user_id = get_jwt_identity()
    data = request.get_json()

    query_text = data.get('query', '').strip()
    pdf_id=data['pdf_id']
    if not query_text:
        return jsonify({"error": "Empty query"}), 400

    # Remove the command prefix
    if query_text.startswith('/summary'):
        query_text = query_text[len('/summary'):].strip()

    try:
        # 1. Generate query embedding using all-MiniLM-L6-v2
        embedding = generate_query_embedding(query_text)  # Defined below

        # 2. Perform similarity search using FAISS
        matched_chunk = search_similar_chunk(embedding,pdf_id)

        if not matched_chunk:
            return jsonify({"answer": "No relevant document found."}), 200

        # 3. Pass to LLM for final answer formatting
        answer_text = generate_llm_response(query_text, matched_chunk.content)

        return jsonify({"answer": answer_text}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

def generate_query_embedding(text):
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding

def search_similar_chunk(query_embedding, pdf_id):
    # Load user's FAISS index and associated chunks from DB
    index = faiss.read_index(f'/path/to/index_{user_id}.index')
    chunks = PDFChunk.query.filter_by(file_id=pdf_id).all() # List of chunk objects with ids and content

    # Perform search
    D, I = index.search(np.expand_dims(query_embedding, axis=0), k=1)
    nearest_idx = I[0][0]

    if nearest_idx == -1 or D[0][0] > THRESHOLD_DISTANCE:
        return None

    return chunks[nearest_idx]


def generate_llm_response(query, chunk_content):
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        prompt = f"""
        You are an expert assistant. Based on the document chunk below, answer the following query clearly and informatively.

        Document:
        ---
        {chunk_content}

        Query:
        ---
        {query}

        Answer:
        """

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"An error occurred during Gemini API call: {e}")
        raise e
