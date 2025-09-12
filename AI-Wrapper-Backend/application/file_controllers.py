from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity,unset_jwt_cookies
from werkzeug.security import generate_password_hash, check_password_hash
from application.models import PDFFile, User
from application.database import db
from datetime import timedelta,datetime
from flask import current_app as app,Flask
from flask_caching import Cache
from celery import shared_task
from fpdf import *
from flask_mail import Mail, Message
import base64
'''
   from celery.contrib.abortable import AbortableTask
   from celery.result import AsyncResult
'''
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
        app.logger.error(f"Error fetching user: {str(e)}")
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
        upload_folder = app.config['UPLOAD_FOLDER']
        filepath = os.path.join(upload_folder, filename)
        
        os.makedirs(upload_folder, exist_ok=True)
        file.save(filepath)

        try:
            pdf_file = PDFFile(filename=filename, filepath=filepath,user_id=user.user_id)
            db.session.add(pdf_file)
            db.session.commit()
            return jsonify({"message": "File uploaded successfully", "file_id": pdf_file.file_id}), 200
        except Exception as e:
            db.session.rollback()
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
        app.logger.error(f"Error fetching PDFs: {str(e)}")
        return jsonify({"error": "Failed to fetch PDFs"}), 500