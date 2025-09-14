from . import celery
from application.models import PDFFile, PDFChunk as PDFC
from application.database import db
import logging
from application.de import DecisionEngine
from celery import chain

from . import create_app

import os
from dotenv import load_dotenv

import time
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
        
        generate_chunks_Embeddings.delay(file_id)
        
        print(f"Generating Chunks for pdf file ID {file_id} has been queued.")
        
       
        
        logging.info(f"Preprocessing completed for file ID {file_id}.")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error during preprocessing for file ID {file_id}: {str(e)}")
        
        if pdf_file:
            pdf_file.status = 'failed'
            db.session.commit()
        
        raise
    
@celery.task(bind=True)
def generate_chunks_Embeddings(self, file_id:int):
    pdf_file = None
    try:
        logging.info(f"Generating Chunks of PDF called with file_id={file_id}")
        pdf_file = db.session.get(PDFFile, file_id)
        if not pdf_file:
            logging.error(f"PDF file with ID {file_id} not found.")
            return {"status": "error", "message": "File not found"}
        
        pdf_file.status = 'preparing_chunks'
        db.session.commit()
        
        de=DecisionEngine()
        de.prepare_chunks(pdf_file.chunking_strategy,pdf_file.filepath,file_id)
        
        pdf_file.status = 'chunks_ready'
        db.session.commit()
        
        pdf_chunks=db.session.query(PDFC).filter_by(file_id=file_id).all()
        print(pdf_chunks)
        de.prepare_embeddings(pdf_file.embedding_model,pdf_file.filepath,file_id,pdf_chunks)
        
        pdf_file.status = 'embeddings_ready'
        db.session.commit()
        
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
    

@celery.task(bind=True)
def summarize_document_chunks(file_id):
    """
    A Celery task to generate summaries for all chunks of a specific PDF file.
    """
    # Tasks run outside the normal Flask request context, so we create one
    app = create_app()
    with app.app_context():
        # --- All your original logic now lives inside the task ---
        
        pdf_record = PDFFile.query.get(file_id)
        if not pdf_record:
            print(f"Task failed: PDF with file_id {file_id} not found.")
            return

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("Task failed: GOOGLE_API_KEY not configured.")
            return
            
        genai.configure(api_key=api_key)
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            
            for chunk in pdf_record.chunks:
                if chunk.chunk_summary:
                    continue

                prompt = f"""
                You are analyzing a small text chunk that was extracted from a larger document. This chunk may be incomplete or start and end abruptly. Your task is to do the following:

                1.  Read the text chunk and identify its primary subject or topic.
                2.  Create a single, complete, and meaningful sentence that describes this topic.
                3.  If the text is too fragmented to be understood, respond with "Fragment is too incoherent to summarize."

                Text Chunk:
                ---
                {chunk.content}
                ---

                One-sentence Summary:
                """
                
                response = model.generate_content(prompt)
                chunk.chunk_summary = response.text
                time.sleep(4.1) # Respect the rate limit
            
            db.session.commit()
            print(f"Successfully summarized all chunks for file_id: {file_id}")

        except Exception as e:
            db.session.rollback()
            print(f"An error occurred during summarization for file_id {file_id}: {e}")
