from . import celery
from application.models import PDFFile, PDFChunk, SummarizedPdfContent, QuestionBank
from application.database import db
import logging
from application.de import DecisionEngine
from celery import chain
import json
import math




from . import create_app

import os
import time


from dotenv import load_dotenv

load_dotenv()
import google.generativeai as genai




@celery.task(bind=True)
def preprocess_pdf(self, file_id):
    '''
       Celery task to preprocess a PDF File
       By Extracting text and converting to markdown
    '''
    
    pdf_file = None
    try:
        logging.info(f"Preprocess PDF called with file_id={file_id}")
        pdf_file = db.session.get(PDFFile, file_id)
        if not pdf_file:
            logging.error(f"PDF file with ID {file_id} not found.")
            return {"status": "error", "message": "File not found"}
        
        pdf_file.status = 'processing'
        db.session.commit()
        
        de=DecisionEngine()
        analysis=de.analyze_pdf(pdf_file.filepath)
        if analysis['status'] == 'error':
            pdf_file.status = 'failed'
            db.session.commit()
            logging.error(f"Analysis failed for file ID {file_id}: {analysis['message']}")
            return {"status": "error", "message": analysis['message']}
        
        
        pdf_file.chunking_strategy = analysis['chunking_strategy']
        pdf_file.embedding_model = analysis['embedding_model']
        print(analysis['chunking_strategy'])
        print(analysis['embedding_model'])
        pdf_file.status = 'processed'
        db.session.commit()
            
        print(f"Pre Processsing Completed for file ID {file_id}.")
        print(f"Creating Chunks for the File id {file_id}")
        
        
        print(f"Generating Chunks for pdf file ID {file_id} has been queued.")
        
    

        pdf_chunks=de.prepare_chunks(pdf_file.chunking_strategy,pdf_file.filepath,file_id)
        
        
        
        pdf_file.status = 'chunks_ready'
        db.session.commit()
        
        
        
        de.prepare_embeddings(pdf_file.embedding_model,pdf_file.filepath,file_id,pdf_chunks)
        
        pdf_file.status = 'embeddings_ready'
        db.session.commit()
        
        logging.info(f"Preprocessing completed for file ID {file_id}.")
        
        return {
            "status":"success",
            "message":"Chunks and Embeddings created successfully",    
        }
        
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error during preprocessing for file ID {file_id}: {str(e)}")
        
        if pdf_file:
            pdf_file.status = 'failed'
            db.session.commit()
        
        raise


