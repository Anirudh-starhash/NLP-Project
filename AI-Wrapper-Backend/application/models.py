from .database import db
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import datetime

# User Class
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
    
    summaries = db.relationship('SummarizedPdfContent', back_populates='user', lazy=True, cascade="all, delete-orphan")
    question_bank = db.relationship('QuestionBank', back_populates='user', lazy=True, cascade="all, delete-orphan")
    chat_messages = db.relationship('ChatMessage', back_populates='user', lazy=True, cascade="all, delete-orphan")
    query_caches = db.relationship('QueryCache', back_populates='user', lazy=True, cascade="all, delete-orphan")
# PDFFile Class
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

    summary = db.relationship('SummarizedPdfContent', back_populates='pdf_file', uselist=False, cascade="all, delete-orphan")
    questions = db.relationship('QuestionBank', back_populates='pdf_file', lazy=True, cascade="all, delete-orphan")
    chat_messages = db.relationship('ChatMessage', back_populates='pdf_file', lazy=True, cascade="all, delete-orphan")
    query_caches = db.relationship('QueryCache', back_populates='pdf_file', lazy=True, cascade="all, delete-orphan")
    
#PDFChunk Class
class PDFChunk(db.Model):
    __tablename__ = 'pdf_chunks'
    id = db.Column(db.Integer, primary_key=True)
    
    file_id = db.Column(
        db.Integer,
        db.ForeignKey('pdf_file.file_id', ondelete='CASCADE'),
        nullable=False
    )
   

    content = db.Column(db.Text, nullable=False)          
    chunk_index = db.Column(db.Integer, nullable=True)  
    chunk_summary=db.Column(db.String,nullable=True)     
    embedding_data = db.Column(db.PickleType, nullable=True)
    
   
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
      
    
    pdf_file = db.relationship('PDFFile', back_populates='chunks')
    
    
    embeddings=db.relationship(
        'Embedding', 
        back_populates='pdf_chunk', 
        lazy=True, 
        cascade="all, delete-orphan"
    )   


# Embedding Class
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
  
  
  
# Summrized PDF Content  
class SummarizedPdfContent(db.Model):
    __tablename__ = 'summarized_pdf_content'

    id = db.Column(db.Integer, primary_key=True)
    summary_text = db.Column(db.Text, nullable=False)
    original_pdf_id = db.Column(db.Integer, db.ForeignKey('pdf_file.file_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pdf_file = db.relationship('PDFFile', back_populates="summary")
    user = db.relationship('User', back_populates="summaries")

    def __repr__(self):
        return f'<SummarizedPdfContent {self.id} for PDF {self.original_pdf_id}>'

    


#Question Bank Class
class QuestionBank(db.Model):
    __tablename__ = 'question_bank'

    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)  # e.g., 'mcq', 'msq', 'numeric', 'integer'
    options = db.Column(db.Text, nullable=True)  # JSON-encoded list of options for MCQ/MSQ types
    correct_answer = db.Column(db.Text, nullable=True)  # JSON or plain text depending on question type
    file_id = db.Column(db.Integer, db.ForeignKey('pdf_file.file_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pdf_file = db.relationship('PDFFile', back_populates="questions")
    user = db.relationship('User', back_populates="question_bank")

    def __repr__(self):
        return f'<Question {self.id} for PDF {self.file_id}>'


import uuid

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
   
   
    session_id = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('pdf_file.file_id'), nullable=True)
    
    message = db.Column(db.Text, nullable=False)
    sender = db.Column(db.String(10), nullable=False) # 'user' or 'bot'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='chat_messages')
    pdf_file = db.relationship('PDFFile', back_populates='chat_messages')
    


class QueryCache(db.Model):
    __tablename__ = 'query_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False, unique=True)
    answer_text = db.Column(db.Text, nullable=False)
    question_embedding = db.Column(db.PickleType, nullable=False)
    
    user = db.relationship('User', back_populates='query_caches')
    pdf_file = db.relationship('PDFFile', back_populates='query_caches')