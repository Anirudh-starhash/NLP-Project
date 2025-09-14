from .database import db
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import datetime

class User(db.Model):
    __tablename__='user'
    user_id=db.Column(db.Integer,primary_key=True,autoincrement=True)
    user_fname=db.Column(db.String(128),nullable=False)
    user_lname=db.Column(db.String(128))
    user_email=db.Column(db.String(128))
    password=db.Column(db.String(128))
    type=db.Column(db.String(128))
    profile_pic = db.Column(db.String(128))

   
    pdf_files = db.relationship('PDFFile', back_populates='user', lazy=True)
class PDFFile(db.Model):
    __tablename__ = 'pdf_file'
    
    file_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    filename = db.Column(db.String(256), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))  
    status = db.Column(db.String(50), default='uploaded')
    chunking_strategy = db.Column(db.String(50))  
    embedding_model = db.Column(db.String(100)) 
    
    user = db.relationship('User', back_populates='pdf_files')
    
    chunks = db.relationship(
        'PDFChunk', 
        back_populates='pdf_file', 
        lazy=True, 
        cascade="all, delete-orphan"
    )

class PDFChunk(db.Model):
    __tablename__ = 'pdf_chunks'
    id = db.Column(db.Integer, primary_key=True)
    
    file_id = db.Column(
        db.Integer,
        db.ForeignKey('pdf_file.file_id', ondelete='CASCADE'),
        nullable=False
    )
   
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)          
    chunk_index = db.Column(db.Integer, nullable=True)    
    start_char = db.Column(db.Integer, nullable=True)     
    end_char = db.Column(db.Integer, nullable=True)    
    embedding_data = db.Column(db.PickleType, nullable=True)
    
   
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
      
    
    pdf_file = db.relationship('PDFFile', back_populates='chunks')
    
    
    embeddings=db.relationship(
        'Embedding', 
        back_populates='pdf_chunk', 
        lazy=True, 
        cascade="all, delete-orphan"
    )   

class Embedding(db.Model):
    __tablename__ = 'embeddings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    file_id=db.Column(
        db.Integer,
        db.ForeignKey('pdf_file.file_id', ondelete='CASCADE'),
        nullable=False
    )
    
    chunk_id = db.Column(
        db.Integer, 
        db.ForeignKey('pdf_chunks.id', ondelete='CASCADE'), 
        nullable=False
    )
    
    vector = db.Column(db.PickleType, nullable=False)  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    pdf_chunk = db.relationship('PDFChunk', back_populates='embeddings')