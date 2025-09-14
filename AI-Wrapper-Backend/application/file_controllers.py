from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity,unset_jwt_cookies
from werkzeug.security import generate_password_hash, check_password_hash
from application.models import PDFFile, User, PDFChunk, Embedding
from application.database import db
from datetime import timedelta,datetime
from flask import Flask
from flask_caching import Cache
from celery import shared_task
from fpdf import *
from flask_mail import Mail, Message
import base64

import logging
from flask import current_app
import traceback
from werkzeug.utils import secure_filename
import os
import uuid

file_blueprint = Blueprint("pdf_file", __name__)
@file_blueprint.route("/upload_pdf", methods=['POST'])
@jwt_required()
def upload_pdf():
    
    try:
        user_identity = get_jwt_identity()
        user = User.query.filter_by(user_id=user_identity).first()

        if not user:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        logging.error(f"Error fetching user: {str(e)}")
        return jsonify({"error": "Failed to fetch user"}), 500
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and file.mimetype == 'application/pdf':
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        filename = unique_id + "_" + filename
        upload_folder = current_app.config['UPLOAD_FOLDER']
        filepath = os.path.join(upload_folder, filename)
        
        os.makedirs(upload_folder, exist_ok=True)
        file.save(filepath)

        try:
            pdf_file = PDFFile(filename=filename, filepath=filepath,user_id=user.user_id)
            db.session.add(pdf_file)
            db.session.commit()
            
            # before sending a response to frontend 
            
            #preprocess the pdf to extract text and save it to the database
            from application.tasks import preprocess_pdf
            preprocess_pdf.delay(pdf_file.file_id)
            
            return jsonify({"message": "File uploaded successfully", "file_id": pdf_file.file_id}), 200
        except Exception as e:
            db.session.rollback()
            logging.error("Exception occurred", exc_info=True)
            return jsonify({"error": "Failed to save file", "details": str(e)}), 500
    else:
        return jsonify({"error": "Invalid file type, please upload PDF"}), 400
    
    

@file_blueprint.route("/get_pdfs", methods=['GET'])
@jwt_required()
def get_pdfs():
    try:
        user_identity = get_jwt_identity()
        user = User.query.filter_by(user_id=user_identity).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get all PDFs uploaded by this user
        pdfs = PDFFile.query.filter_by(user_id=user.user_id).all()
        print(pdfs)
        
        pdf_list = []
        for pdf in pdfs:
            pdf_list.append({
                "file_id": pdf.file_id,
                "filename": pdf.filename,
                "filepath": pdf.filepath,
                "upload_time": pdf.upload_time.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify({"pdfs": pdf_list}), 200
    except Exception as e:
        logging.error(f"Error fetching PDFs: {str(e)}")
        return jsonify({"error": "Failed to fetch PDFs"}), 500
    
    


    
@file_blueprint.route("/delete_pdf/<int:file_id>", methods=['GET'])
@jwt_required()
def delete_pdf(file_id):
    try:
        user_identity = get_jwt_identity()
        user = User.query.filter_by(user_id=user_identity).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        pdf_file = PDFFile.query.filter_by(file_id=file_id, user_id=user.user_id).first()
        if not pdf_file:
            return jsonify({"error": "PDF file not found"}), 404

        
        file_path = os.path.join(os.path.dirname(current_app.root_path), pdf_file.filepath)

        # Delete the file from the filesystem
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info(f"File {file_path} removed from filesystem.")
        else:            logging.warning(f"File {file_path} not found in filesystem.")

        # Delete the record from the database
        db.session.delete(pdf_file)
        db.session.commit()

        return jsonify({"message": "PDF file deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting PDF: {str(e)}")
        return jsonify({"error": "Failed to delete PDF"}), 500
    
    
@file_blueprint.route("/get_chunks/<int:file_id>", methods=['GET'])
@jwt_required()
def get_chunks(file_id):
    try:
        user_identity = get_jwt_identity()
        user = User.query.filter_by(user_id=user_identity).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        chunks=PDFChunk.query.filter_by(file_id=file_id).all()
        if not chunks:
            return jsonify({"error": "No chunks found for this PDF file"}), 404

        
        

        chunk_list = [
            {
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "embedding_data": chunk.embedding_data
            }
            for chunk in chunks
        ]

        return jsonify({"chunks": chunk_list}), 200
    except Exception as e:
        logging.error(f"Error fetching chunks: {str(e)}")
        return jsonify({"error": "Failed to fetch chunks"}), 500
    
    
@file_blueprint.route("/get_embeddings/<int:embedding_id>",methods=['GET'])
@jwt_required()
def get_embedding(embedding_id):
    
        """
            Fetches a single embedding vector directly from the database.
            This is the recommended and most efficient method.
        """
        try:
            current_user_id = get_jwt_identity()
            logging.info(f"User {current_user_id} requesting embedding ID: {embedding_id}")

            # 1. Fetch the embedding record from the database
            embedding = db.session.get(Embedding, embedding_id)

            if not embedding:
                logging.warning(f"Embedding with ID {embedding_id} not found.")
                return jsonify({"error": "Embedding not found"}), 404

            ''' 
                Verify the file associated with this 
                embedding belongs to the current user.
            '''
            
            pdf_file = db.session.get(PDFFile, embedding.file_id)
            if not pdf_file or pdf_file.user_id != current_user_id:
                logging.error(f"User {current_user_id} FORBIDDEN to access embedding {embedding_id}")
                return jsonify({"error": "Access forbidden"}), 403

            ''' 3. Return the vector stored in the database record '''
            logging.info(f"Successfully retrieved embedding {embedding_id} from database.")
            return jsonify({
                'id': embedding.id,
                'file_id': embedding.file_id,
                'chunk_id': embedding.chunk_id,
                'vector': embedding.vector  # The vector is already here!
            })

        except Exception as e:
            logging.error(f"Error fetching embedding {embedding_id}: {str(e)}")
            return jsonify({"error": "An internal error occurred"}), 500

        