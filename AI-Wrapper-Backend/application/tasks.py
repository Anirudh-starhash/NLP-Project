from . import celery
from application.models import PDFFile
from application.database import db
import logging
import subprocess
import tempfile
import os



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
       
        markdown=extract_markdown_from_pdf(pdf_file.filepath)
        
        if not markdown:
            logging.error(f"Markdown extraction failed for {file_id}")
            pdf_file.status = 'failed'
            db.session.commit()
            return {"status": "error", "message": "Markdown extraction failed"}

        # store the markdown content in db
        pdf_file.markdown_content = markdown
        pdf_file.status = 'completed'
        db.session.commit()
        
        
        logging.info(f"Preprocessing completed for file ID {file_id}.")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error during preprocessing for file ID {file_id}: {str(e)}")
        
        if pdf_file:
            pdf_file.status = 'failed'
            db.session.commit()
        
        raise
    
def extract_markdown_from_pdf(filepath):
    
    '''
        Extracts a text from a PDF and converts it to markdown format.
    '''
    try:
       
        pass
           
    
    except Exception as e:
        logging.error(f"Error extracting markdown from {filepath}: {str(e)}")
        return None
    