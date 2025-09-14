from . import celery
from application.models import PDFFile
from application.database import db
import logging


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
        print(f"Pre Processsing Completed for file ID {file_id}.")
        
        
        logging.info(f"Preprocessing completed for file ID {file_id}.")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error during preprocessing for file ID {file_id}: {str(e)}")
        
        if pdf_file:
            pdf_file.status = 'failed'
            db.session.commit()
        
        raise
    
