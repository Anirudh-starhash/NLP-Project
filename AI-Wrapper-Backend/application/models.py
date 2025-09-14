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
    
    user = db.relationship('User', backref=db.backref('pdf_files', lazy=True))

from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from application.database import db

class PDFFile(db.Model):
    __tablename__ = 'pdf_files'
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    chunking_strategy = Column(String(100), nullable=True)
    embedding_model = Column(String(100), nullable=True)
    status = Column(String(50), default='uploaded')

    # Relationship to chunks
    chunks = relationship('PDFChunk', back_populates='pdf_file', cascade='all, delete-orphan')


class PDFChunk(db.Model):
    __tablename__ = 'pdf_chunks'
    id = Column(Integer, primary_key=True)
    
    file_id = Column(Integer, ForeignKey('pdf_files.id', ondelete='CASCADE'), nullable=False)
    pdf_file = relationship('PDFFile', back_populates='chunks')
    
    content = Column(Text, nullable=False)          
    chunk_index = Column(Integer, nullable=True)    
    start_char = Column(Integer, nullable=True)     
    end_char = Column(Integer, nullable=True)       

   
