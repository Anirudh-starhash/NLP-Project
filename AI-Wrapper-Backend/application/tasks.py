from . import celery
from application.models import PDFFile
from application.database import db
import logging

@celery.task(bind=True)
def preprocess_pdf(self, file_id):
    try:
        logging.info(f"Preprocess PDF called with file_id={file_id}")
        pdf_file = PDFFile.query.get(file_id)
        if not pdf_file:
            logging.error(f"PDF file with ID {file_id} not found.")
            return {"status": "error", "message": "File not found"}
        
       
        markdown=extract_markdown_from_pdf(pdf_file.filepath)
        
        if not markdown:
            logging.error(f"Markdown extraction failed for {file_id}")
            return {"status": "error", "message": "Markdown extraction failed"}

        
        logging.info(f"Preprocessing completed for file ID {file_id}.")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error during preprocessing for file ID {file_id}: {str(e)}")
        
        
def extract_markdown_from_pdf(filepath):
    
    try:
        with open(filepath, 'r') as file:
            content = file.read()
            
        markdown_content = f"# Extracted Content\n\n{content}"
        return markdown_content
    
    except Exception as e:
        logging.error(f"Error extracting markdown from {filepath}: {str(e)}")
        return None
    