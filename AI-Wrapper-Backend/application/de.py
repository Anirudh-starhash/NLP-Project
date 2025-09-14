# this is decision engine

import pdfplumber
import re
import logging
from typing import Dict, Any
from . import celery
from application.database import db
from application.models import PDFFile, PDFChunk

import re
import spacy

nlp=spacy.load("en_core_web_sm") # small english dataset

'''
    We Performed Text Extraction using pdfplumber
    We performed Tokenization using simple regex for word count
    We peformed Document Complexity Analysis to find charcater count
    Heading Detection mechanism using regex patterns
    Rule Based NLP (Heuristic based Decision Making) for chunking strategy
    Resource Aware NLP ( For Embedding Model Selection)
'''

class DecisionEngine:
    def __init__(self):
        logging.info("Decision Engine initialized.")
        
    def analyze_pdf(self,pdf_path : str)->Dict[str,Any]:
        '''
            Analyzes the PDF and extracts key information.
        '''
        print("analyze_pdf is called with:", pdf_path)
        logging.info(f"Analyzing PDF at path: {pdf_path}")
        
        text = self.extract_text_from_pdf(pdf_path)
        
        if not text.strip():
            print("No text extracted from PDF.")
            logging.warning("No text extracted from PDF.")
            return {
                "status": "success",
                "chunking_strategy": "token_split", 
                "embedding_model": "huggingface_transformers"
            }
            
        num_chars=len(text)
        num_words=len(text.split())
        num_headings=self.detect_headings(text)
        
        print(f"Document Analysis - Chars: {num_chars}, Words: {num_words}, Headings: {num_headings}")
        logging.info(f"Document Analysis - Chars: {num_chars}, Words: {num_words}, Headings: {num_headings}")
        
        self.chunling_strategy = self.decide_chunking_strategy(num_chars, num_words, num_headings)
        self.embedding_model = self.decide_embedding_model(num_chars, num_words) 
        
        print(f"Decided Chunking Strategy: {self.chunling_strategy}, Embedding Model: {self.embedding_model}")
        return {
            "status": "success",
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
        
        
    def prepare_chunks(self,chunking_strategy:str,pdf_path:str, file_id:int)->list:
        '''
            Prepares chunks based on the chunking strategy.
        '''
        print(f"Preparing chunks using strategy: {chunking_strategy}")
        logging.info(f"Preparing chunks using strategy: {chunking_strategy}")
        
        text = self.extract_text_from_pdf(pdf_path)
        
        if chunking_strategy == "section_heading_split":
            chunks = self.section_heading_split(text)
        elif chunking_strategy == "recursive_character_split":
            chunks = self.recursive_character_split(text)
        else:
            chunks = self.token_split(text)
        
        
        for chunk in chunks:
            pdf_chunk = PDFChunk(
                file_id=file_id,
                content=chunk['content'],
                chunk_index=chunk['chunk_index'],
                start_char=chunk['start_char'],
                end_char=chunk['end_char']
            )
            db.session.add(pdf_chunk)
        db.session.commit()
        
        print(f"Prepared {len(chunks)} chunks.")
        logging.info(f"Prepared {len(chunks)} chunks.")
        
     
     
    '''
        1)  In Section Heading Split we use NLP techniques using reges
            for sentence detection
        2)  Detect headings with regex
        3)  Group sentences under headings into chunks
        4)  Return a list of dicts with content, chunk_index, 
            start_char, end_char
    '''   
    def section_heading_split(self, text: str) -> list:
        
        '''
            Splits text into chunks based on headings.
            Returns list of dicts with content, chunk_index, 
            start_char, end_char.
        '''
        
        chunks=[]
        #regex pattens for headings
        heading_pattern = re.compile(r'(^\d+(\.\d+)*\s.*)|(^Chapter\s\d+)', re.MULTILINE)
        # most chapters work with 1, 2.1 or Chapter X etc
        
        #Find all heading matches in the text
        matches=list(heading_pattern.finditer(text))
        
        if not matches:
            return self.recursive_character_split(text)
        
        #create chunks based on headings positions
        for idx , match in enumerate(matches):
            start_idx=match.start()
            end_idx=matches[idx+1].start() if idx+1 < len(matches) else len(text)
            chunk_text=text[start_idx:end_idx].strip()
            
            if chunk_text:
                chunks.append({
                    "content":chunk_text,
                    "chunk_index":idx,
                    "start_char":start_idx,
                    "end_char":end_idx
                })
        
        return chunks
    
    '''
        1)  In Recursive Character Split we use NLP techniques using reges
            for sentence detection for smart splits like if any threshold 
            exceeds
        2)  Split text recursively into <= max_chunk_size characters
        3) Prefer splitting at sentence boundaries (using NLTK/spaCy)
        4) Include overlap for context
       
    '''
    def recursive_character_split(self, text: str, max_chunk_size: int = 2000, overlap: int = 200) -> list:
        '''
            Splits text recursively into smaller chunks 
            based on character count.
            Tries to split at sentence boundaries using spaCy.
        '''
        
        chunks=[]
        doc=nlp(text)
        sentences=[sent.text for sent in doc.sents]
        
        current_chunk=""
        start_char=0
        idx=0
        
        for sent in sentences:
            if len(sent)+ len(current_chunk) + 1 < max_chunk_size:
                current_chunk+=sent+ " "
            else:
                end_char=start_char + len(current_chunk)
                chunks.append({
                    "content":current_chunk.strip(),
                    "chunk_index":idx,
                    "start_char":start_char,
                    "end_char":end_char
                })
                idx+=1
                
                # start new chunk with overlap
                overlap_text=current_chunk[-overlap:] if overlap > 0 else ""
                start_char=end_char - len(overlap_text)
                current_chunk=overlap_text + sent + " "

        
        # Add last chunk
        if current_chunk.strip():
            end_char = start_char + len(current_chunk)
            chunks.append({
                "content": current_chunk.strip(),
                "chunk_index": idx,
                "start_char": start_char,
                "end_char": end_char
            })
            
        return chunks
    
    '''
        1) For Token Split we use simple whitespace and 
           punctuation based tokenization
        2) Tokenize text into words/tokens
        3) Create chunks of max_tokens with optional overlap
        4) Join tokens back into string chunks
    '''
    def token_split(self, text: str, max_tokens: int = 500, overlap: int = 50) -> list:
        '''
            Splits text into chunks based on token count.
             Overlap helps retain context.
        '''
        
        chunks=[]
        doc=nlp(text)
        
        tokens=[token.text for token in doc]
        
        idx=0
        start_char=0
        
        i=0
        while i < len(tokens):
            chunk_tokens=tokens[i:i+max_tokens]
            chunk_text="".join(chunk_tokens)
            end_char=start_char + len(chunk_text)
            
           
            chunks.append({
                "content":chunk_text,
                "chunk_index":idx,
                "start_char":start_char,
                "end_char":end_char
            })
            idx+=1
            
            i+=max_tokens - overlap
            start_char=end_char - len("".join(chunk_tokens[-overlap:])) if overlap > 0 else end_char

        return chunks

if __name__ == "__main__":
    pdf_file = "sample_document.pdf"  # path to PDF file
    de = DecisionEngine()
    result = de.analyze_pdf(pdf_file)
    print("Decision:", result)