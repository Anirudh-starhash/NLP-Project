# this is decision engine

import pdfplumber
import re
import logging
from typing import Dict, Any
from . import celery

@celery.task(bind=True)
class DecisionEngine:
    def __init__(self):
        logging.info("Decision Engine initialized.")
        
    def analyze_pdf(self,pdf_path : str)->Dict[str,Any]:
        '''
            Analyzes the PDF and extracts key information.
        '''
        logging.info(f"Analyzing PDF at path: {pdf_path}")
        
        text = self.extract_text_from_pdf(pdf_path)
        
        if not text.strip():
            logging.warning("No text extracted from PDF.")
            return {
                "chunking_strategy": "token_split", 
                "embedding_model": "huggingface_transformers"
            }
            
        num_chars=len(text)
        num_words=len(text.split())
        num_headings=self.detect_headings(text)
        
        logging.info(f"Document Analysis - Chars: {num_chars}, Words: {num_words}, Headings: {num_headings}")
        
        self.chunling_strategy = self.decide_chunking_strategy(num_chars, num_words, num_headings)
        self.embedding_model = self.decide_embedding_model(num_chars, num_words) 
        
        return {
            "chunking_strategy": self.chunling_strategy, 
            "embedding_model": self.embedding_model
        }
        
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        '''
            Extracts text from the PDF using pdfplumber.
        '''
        full_text=""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
                        
                logging.info("PDF text extraction completed.")
        except Exception as e:
            logging.error(f"Error extracting text from PDF: {str(e)}")
            return ""
        
        return full_text
    
    
    def detect_headings(self, text: str) -> int:
        '''
            Detect headings by regex patterns used in academic or formal documents.
        '''
        
        pattern = r"(^|\n)(\d+\.\s+.*|[A-Z\s]{4,}|Chapter\s+\d+)"
        headings = re.findall(pattern, text)
        logging.info(f"Detected {len(headings)} headings.")
        return len(headings)
    
    
    def decide_chunking_strategy(self, num_chars: int, num_words: int, num_headings: int) -> str:
        
        if num_headings >= 5:
            logging.info("Choosing 'section_heading_split'.")
            return "section_heading_split"
        
        elif num_chars > 100000 or num_words > 20000:
            logging.info("Choosing 'recursive_character_split'.")
            return "recursive_character_split"
        
        else:
            logging.info("Choosing 'token_split'.")
            return "token_split"
        
    def decide_embedding_model(self, num_chars: int, num_words: int) -> str:
       
        if num_chars > 150000 or num_words > 30000:
            logging.info("Choosing 'gemini_api'.")
            return "gemini_api"
        else:
            logging.info("Choosing 'huggingface_transformers'.")
            return "huggingface_transformers"
        
        
if __name__ == "__main__":
    pdf_file = "sample_document.pdf"  # path to PDF file
    de = DecisionEngine()
    result = de.analyze_pdf(pdf_file)
    print("Decision:", result)