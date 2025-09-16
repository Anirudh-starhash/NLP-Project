# this is decision engine

import pdfplumber
import re
import logging
from typing import Dict, Any
from . import celery
from application.database import db
from application.models import PDFFile, PDFChunk, Embedding

import re
import spacy
import os
import numpy as np
import faiss
import time


from sentence_transformers import SentenceTransformer

import google.generativeai as genai


nlp=spacy.load("en_core_web_sm") # small english dataset

'''
    We Performed Text Extraction using pdfplumber
    We performed Tokenization using simple regex for word count
    We peformed Document Complexity Analysis to find charcater count
    Heading Detection mechanism using regex patterns
    Rule Based NLP (Heuristic based Decision Making) for chunking strategy
    Resource Aware NLP ( For Embedding Model Selection)
'''

import hashlib
from application.models import PDFChunk

def compute_pdf_hash(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


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
        
        self.chunking_strategy = self.decide_chunking_strategy(num_chars, num_words, num_headings)
        self.embedding_model = self.decide_embedding_model(num_chars, num_words) 
        
        print(f"Decided Chunking Strategy: {self.chunking_strategy}, Embedding Model: {self.embedding_model}")
        return {
            "status": "success",
            "chunking_strategy": self.chunking_strategy, 
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
                end_char=chunk['end_char'],
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
    
    
    def prepare_embeddings(self,embedding_model:str,pdf_path:str,file_id:int, pdf_chunks: list):
        '''
            Prepares embeddings based on the embedding model.
        '''
        print(f"Preparing embeddings using model: {embedding_model}")
        logging.info(f"Preparing embeddings using model: {embedding_model}")
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        faiss_dir = os.path.join(base_dir, 'faiss')
        
        if not os.path.exists(faiss_dir):
            os.makedirs(faiss_dir)
            
        index_file=os.path.join(faiss_dir, f"{file_id}.index")
        
        if os.path.exists(index_file):
            logging.info(f"Index already exists for file {file_id}, skipping creation.")
            return
        
        if embedding_model == "huggingface_transformers":
            self.create_embeddings_huggingface(pdf_chunks,index_file,file_id)
        else:
            self.create_embeddings_gemini_api(pdf_chunks, index_file,file_id)
         
    '''
        1) For Huggingface Transformers we use sentence-transformers
              models to generate embeddings
    '''   
    def create_embeddings_huggingface(self, pdf_chunks: list, index_file: str, file_id:int):
        
        logging.info(f"Creating embeddings with Hugging Face for file_id: {file_id}")
         
        try:
        
            ''' 
                1. Load a pre-trained Sentence Transformer model
                all-MiniLM-L6-v2' is a good starting point
            '''
        
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            ''' 2. Extract the content from the PDFChunk objects '''

            chunk_contents = [chunk.content for chunk in pdf_chunks]

            logging.info(f"Encoding {len(chunk_contents)} chunks to generate embeddings.")
            
            ''' 3. Generate embeddings for all chunks '''
            embeddings = model.encode(chunk_contents, convert_to_numpy=True)
            logging.info(f"Embeddings shape before reshape: {embeddings.shape}")

            if embeddings.ndim == 1:
                logging.warning("Single chunk detected, reshaping embeddings.")
                embeddings = embeddings.reshape(1, -1)
            
            if embeddings.shape[0] != len(chunk_contents):
                logging.warning("Number of embeddings does not match number of chunks!")
            
            
            ''' 4. Save embeddings to the database '''
            logging.info("Building FAISS index...")
            embedding_dimension = embeddings.shape[1] 
            index = faiss.IndexFlatL2(embedding_dimension) 
            
            index.add(np.array(embeddings)) 
            # Add the vectors to the index
            
            faiss.write_index(index, index_file)
            logging.info(f"FAISS index saved to {index_file}")
               
            logging.info("Storing embeddings in the database...")
            print(pdf_chunks)
            for i, chunk in enumerate(pdf_chunks):
                
                # Create a new Embedding object for each chunk
                new_embedding = Embedding(
                    file_id=file_id,
                    chunk_id=chunk.id,
                    vector=embeddings[i].tolist()  # Store as a Python list, PickleType will handle it
                )
                db.session.add(new_embedding) 
                db.session.flush()
                  # Flush to get the ID assigned
                chunk.embedding_data = new_embedding.id
                db.session.add(chunk)
            
            db.session.commit()
            logging.info("Successfully stored embeddings in the database.")

        except Exception as e:
            db.session.rollback() # Rollback the transaction on error
            logging.error(f"Error creating Hugging Face embeddings: {e}")
            
            raise
    
    '''
        1) For Gemini API we use google gemini api to generate embeddings
    '''
    def create_embeddings_gemini_api(self,pdf_chunks:list,index_file:str,file_id:int):
        
        logging.info(f"Creating embeddings with Gemini API for file_id: {file_id}")
        
        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set.")
            
            genai.configure(api_key=api_key)
            
            chunk_contents = [chunk.content for chunk in pdf_chunks]
            logging.info(f"Generating embeddings for {len(chunk_contents)} chunks using Gemini API.")
            
            all_embeddings=[]
            BATCH_SIZE=100
            model_name = 'models/embedding-001'
            
            logging.info(f"Encoding chunks into vectors using Gemini API (in batches of {BATCH_SIZE})...")
            for i in range(0, len(chunk_contents), BATCH_SIZE):
                batch_texts = chunk_contents[i:i + BATCH_SIZE]
                
                # Make the API call for the current batch
                result = genai.embed_content(
                    model=model_name,
                    content=batch_texts,
                    task_type="RETRIEVAL_DOCUMENT" 
                )
                
                if 'embedding' not in result:
                    raise ValueError("No 'embedding' in API response")

                embeddings = result['embedding']
                
                if isinstance(embeddings[0], float):
                    logging.warning("Single chunk embedding detected, wrapping it in a list.")
                    embeddings = [embeddings]
        
                all_embeddings.extend(result['embedding'])
                
                
                logging.info(f"Processed batch {i//BATCH_SIZE + 1}/{(len(chunk_contents)-1)//BATCH_SIZE + 1}")
                # Add a small delay to avoid hitting rate limits (e.g., 60 requests per minute)
                time.sleep(1) 

            embeddings_np = np.array(all_embeddings)
            if embeddings_np.ndim != 2:
                raise ValueError(f"Embeddings have invalid shape: {embeddings_np.shape}")
            
            logging.info("Building FAISS index...")
            embedding_dimension = embeddings_np.shape[1] 
            index = faiss.IndexFlatL2(embedding_dimension) 
            # Using L2 distance for similarity
            
            index.add(np.array(embeddings_np)) 
            # Add the vectors to the index
            
            faiss.write_index(index, index_file)
            logging.info(f"FAISS index saved to {index_file}")
               
            logging.info("Storing embeddings in the database...")
            for i, chunk in enumerate(pdf_chunks):
                
                # Create a new Embedding object for each chunk
                new_embedding = Embedding(
                    file_id=file_id,
                    chunk_id=chunk.id,
                    vector=embeddings_np[i].tolist()  # Store as a Python list, PickleType will handle it
                )
                db.session.add(new_embedding)  
                db.session.flush()
                
                  # Flush to get the ID assigned
                chunk.embedding_data = new_embedding.id
                db.session.add(chunk)
                
            db.session.commit()
            logging.info("Successfully stored embeddings in the database.")

        except Exception as e:
            db.session.rollback() # Rollback the transaction on error
            logging.error(f"Error creating Gemini API embeddings: {e}")
            
            raise

     

if __name__ == "__main__":
    pdf_file = "sample_document.pdf"  # path to PDF file
    de = DecisionEngine()
    result = de.analyze_pdf(pdf_file)
    print("Decision:", result)