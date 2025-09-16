from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from application.database import db
from application.models import User,PDFFile,PDFChunk,SummarizedPdfContent, ChatMessage, QueryCache
import google.generativeai as genai
from application.tasks import *
from google.api_core import exceptions

import os
from dotenv import load_dotenv

import time
load_dotenv()
import fitz
import faiss
import numpy as np
THRESHOLD_DISTANCE = 0.6

MODEL_FALLBACK_LIST = [
    'models/gemini-2.5-pro',
    'models/gemini-2.0-flash',
    'models/gemini-2.0-flash-001', 
]

current_model_index=0

try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except KeyError:
    print("CRITICAL: GEMINI_API_KEY environment variable not set.")


    
def summarize_with_gemini(full_text: str) -> str:
    """
    Summarizes a long text using the Gemini 1.5 Pro API.
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
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
  
  
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')  

def generate_query_embedding(text):
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding

def search_similar_chunk(query_embedding, pdf_id):
    # Load user's FAISS index and associated chunks from DB
    index = faiss.read_index(f'/home/anirudh_pabbaraju/NLP-Project/AI-Wrapper-Backend/faiss/{pdf_id}.index')
    chunks = PDFChunk.query.filter_by(file_id=pdf_id).order_by(PDFChunk.id).all() # List of chunk objects with ids and content

    # print(chunks)
    # Perform search
    NUM_CHUNKS_TO_RETRIEVE = 3 # Or 5
    D, I = index.search(np.expand_dims(query_embedding, axis=0), k=NUM_CHUNKS_TO_RETRIEVE)
    nearest_idx = I[0][0]

    print(f"DEBUG: Nearest index: {nearest_idx}, Distance: {D[0][0]}")
    # if nearest_idx == -1 or D[0][0] > THRESHOLD_DISTANCE:
    #     return None

    retrieved_chunks = []
    for i in range(NUM_CHUNKS_TO_RETRIEVE):
        nearest_idx = I[0][i]
        distance = D[0][i]
        if nearest_idx != -1 and distance < THRESHOLD_DISTANCE:
             retrieved_chunks.append(chunks[nearest_idx])

    return retrieved_chunks

def check_cache(user_id: int, file_id: int, query_embedding: np.ndarray):
    
    cache_index_path = f"/home/anirudh_pabbaraju/NLP-Project/AI-Wrapper-Backend/faiss/cache_{file_id}.index"

    if not os.path.exists(cache_index_path):
        return None # No cache exists for this document yet

    # 2. Load the specific cache index and search it
    index = faiss.read_index(cache_index_path)
    D, I = index.search(np.expand_dims(query_embedding, axis=0), k=1)
    
    nearest_idx_in_cache = I[0][0]
    distance = D[0][0]

    CACHE_THRESHOLD = 0.95 # Use a very strict threshold for caching

    # 3. If a very similar question is found, get the corresponding answer
    if distance < (1 - CACHE_THRESHOLD): # For cosine similarity, distance is 1-similarity
        # Find all cached items for this file to map the index back to the ID
        cached_items = QueryCache.query.filter_by(file_id=file_id).order_by(QueryCache.id).all()
        if nearest_idx_in_cache < len(cached_items):
            return cached_items[nearest_idx_in_cache].answer_text
            
    return None

def add_to_cache(user_id: int, file_id: int, question: str, answer: str, embedding: np.ndarray):
    # 1. Save the new Q&A pair to the database, linked to the user and file
    
    new_cache_item = QueryCache(
        user_id=user_id,
        file_id=file_id,
        question_text=question,
        answer_text=answer,
        question_embedding=embedding.tolist()
    )
    
    db.session.add(new_cache_item)
    db.session.commit()

    # 2. Update the specific FAISS index for this document's cache
    cache_index_path = f"/home/anirudh_pabbaraju/NLP-Project/AI-Wrapper-Backend/faiss/cache_{file_id}.index"
    
    # Get all embeddings for this file's cache in the correct order
    all_cached_embeddings = [
        np.array(item.question_embedding) 
        for item in QueryCache.query.filter_by(file_id=file_id).order_by(QueryCache.id).all()
    ]
    
    # Rebuild and save the index
    embeddings_np = np.array(all_cached_embeddings)
    index = faiss.IndexFlatL2(embeddings_np.shape[1])
    index.add(embeddings_np)
    faiss.write_index(index, cache_index_path)

def generate_response_with_fallback(query, context):
    """
        Tries to generate a response using the model list.
        If a quota error occurs, it automatically falls back to the next model.
    """
    global current_model_index

    # --- 3. Loop through the available models ---
    while current_model_index < len(MODEL_FALLBACK_LIST):
        model_name = MODEL_FALLBACK_LIST[current_model_index]
        print(f"Attempting to use model: {model_name}...")

        try:
            # --- 4. Call the API ---
            model = genai.GenerativeModel(model_name)
            
            prompt = f"""
            You are an expert STEM tutor and assistant specializing in Physics, Chemistry, and Mathematics.
            Your task is to answer the user's query based on the provided context from a textbook.

            Synthesize the information from all the provided context passages to create a single, coherent, and comprehensive response.

            Follow these instructions:
            1.  **Be Accurate:** Stick to the information given in the context. Do not add external information.
            2.  **Handle Subjects Appropriately:**
                * For **Mathematics**, provide step-by-step explanations for proofs or problems. Use LaTeX for formulas.
                * For **Physics**, clearly explain concepts and principles, using real-world examples if the context supports them. Use LaTeX for equations.
                * For **Chemistry**, describe reactions and principles clearly. Use LaTeX for chemical formulas.
            3.  **Be Clear and Concise:** Structure your answer logically. Use headings or bullet points if it improves clarity.
            4.  **Handle Insufficient Context:** If the provided context is not sufficient to answer the query completely, state that you can only provide a partial answer based on the available text and specify what's missing.

            CONTEXT FROM TEXTBOOK:
            ---
            {context}
            ---

            USER'S QUERY:
            ---
            {query}
            ---

            ASSISTANT'S ANSWER:
            """
            
            response = model.generate_content(prompt)
            print(f"Successfully generated response with {model_name}.")
            return response.text

        except exceptions.ResourceExhausted as e:
            # --- 5. Handle Quota Error and try the next model ---
            print(f"Quota exceeded for {model_name}. Error: {e}")
            current_model_index += 1
            print("Switching to the next available model...")
            continue # Retry the loop with the next model

        except Exception as e:
            # For any other error, stop and report it.
            print(f"An unexpected error occurred with {model_name}: {e}")
            # You might want to return a user-friendly error message here
            return "Sorry, an unexpected error occurred while generating the response."

    # --- 6. If all models have failed ---
    print("All models have exceeded their quota. Please try again later.")
    return "All available models are temporarily overloaded. Please try again in a few minutes."








@chat_blueprint.route('/query_document', methods=['POST'])
@jwt_required()
def query_document():
    
    # print("Available models:")
    # for m in genai.list_models():
    #     # Check if the model supports the 'generateContent' method
    #     if 'generateContent' in m.supported_generation_methods:
    #         print(m.name)
            
    user_id = get_jwt_identity()
    data = request.get_json()

    query_text = data.get('query', '').strip()
    pdf_id=data['pdf_id']
    
    session_id = data.get('session_id') 
    
    
    query_embedding = generate_query_embedding(query_text)
    answer_text = check_cache(user_id, pdf_id, query_embedding)
    
    
    if answer_text:
        print(f"CACHE HIT for user:{user_id}, file:{pdf_id}")
    else:
        print(f"CACHE MISS for user:{user_id}, file:{pdf_id}")
        
        # --- 3. If Cache Miss, Run RAG Pipeline ---
        matched_chunks = search_similar_chunk(query_embedding, pdf_id)

        if not matched_chunks:
            answer_text = "I couldn't find any relevant information in the document to answer your question."
        else:
            combined_context = "\n\n---\n\n".join([chunk.content for chunk in matched_chunks])
            answer_text = generate_response_with_fallback(query_text, combined_context)
            
            add_to_cache(user_id, pdf_id, query_text, answer_text, query_embedding)

    user_message = ChatMessage(
        user_id=user_id,
        file_id=pdf_id,
        session_id=session_id,
        message=query_text,
        sender='user'
    )
    
    
    db.session.add(user_message)
    db.session.commit()
    if not query_text:
        return jsonify({"error": "Empty query"}), 400

    # Remove the command prefix
    if query_text.startswith('/summary'):
        query_text = query_text[len('/summary'):].strip()

    try:
        # 1. Generate query embedding using all-MiniLM-L6-v2
        embedding = generate_query_embedding(query_text)  # Defined below

        # 2. Perform similarity search using FAISS
        matched_chunks = search_similar_chunk(embedding, pdf_id)

        if not matched_chunks:
            return jsonify({"answer": "No relevant document found."}), 200

        combined_context = "\n\n---\n\n".join([chunk.content for chunk in matched_chunks])
        # 3. Pass to LLM for final answer formatting
        print(combined_context)
        answer_text = generate_response_with_fallback(query_text, combined_context)
        
        bot_response = ChatMessage(
            user_id=user_id,
            file_id=pdf_id,
            session_id=session_id,
            message=answer_text,
            sender='bot'
        )
        db.session.add(bot_response)
        db.session.commit()
        
        return jsonify({"answer": answer_text}), 200

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

