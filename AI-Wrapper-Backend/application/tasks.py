from . import celery
from application.models import PDFFile, PDFChunk as PDFC
from application.database import db
import logging
from application.de import DecisionEngine


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
        
        generate_chunks.delay(file_id)
        
        print(f"Generating Chunks for pdf file ID {file_id} has been queued.")
        
        print(f"Now Creating Embeddings for the File id {file_id}")
        generate_embeddings.delay(file_id)
        print
        
        logging.info(f"Preprocessing completed for file ID {file_id}.")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error during preprocessing for file ID {file_id}: {str(e)}")
        
        if pdf_file:
            pdf_file.status = 'failed'
            db.session.commit()
        
        raise
    
@celery.task(bind=True)
def generate_chunks(self, file_id:int):
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
        
        return {
            "status":"success",
            "message":"Chunks created successfully",    
        }
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error during preprocessing for file ID {file_id}: {str(e)}")
        
        if pdf_file:
            pdf_file.status = 'failed'
            db.session.commit()
        
        raise
    
    
@celery.task(bind=True)
def generate_embeddings(self, file_id:int):
    pdf_file = None
    try:
        logging.info(f"Generating Embeddings of PDF called with file_id={file_id}")
        pdf_file = db.session.get(PDFFile, file_id)
        if not pdf_file:
            logging.error(f"PDF file with ID {file_id} not found.")
            return {"status": "error", "message": "File not found"}
        
        pdf_file.status = 'preparing_embeddings'
        db.session.commit()
        
        pdf_chunks=db.session.query(PDFC).filter_by(file_id=file_id).all()
        de=DecisionEngine()
        de.prepare_embeddings(pdf_file.embedding_strategy,pdf_file.filepath,file_id,pdf_chunks)
        
        pdf_file.status = 'embeddings_ready'
        db.session.commit()
        
        return {
            "status":"success",
            "message":"Embeddings created successfully",    
        }
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error during preprocessing for file ID {file_id}: {str(e)}")
        
        if pdf_file:
            pdf_file.status = 'failed'
            db.session.commit()
        
        raise