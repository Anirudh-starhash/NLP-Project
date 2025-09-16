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
        
        
        try:
            logging.info("Loading SentenceTransformer model into memory...")
            self.hf_model = SentenceTransformer('all-MiniLM-L6-v2')
            logging.info("SentenceTransformer model loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load SentenceTransformer model: {e}")
            self.hf_model = None 
        
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
            # This is the line to change
            logging.info("Choosing 'split_by_sentence'.")
            return "split_by_sentence"
        
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
            chunks_data = self.section_heading_split(text)
        elif chunking_strategy == "split_by_sentence":
            chunks_data = self.split_by_sentence(text)
        else:
            chunks_data = self.token_split(text)
        
        
        created_chunks = []
        for chunk_dict in chunks_data:
            pdf_chunk = PDFChunk(
                file_id=file_id,
                content=chunk_dict['content'],
                chunk_index=chunk_dict['chunk_index'],
            )
            db.session.add(pdf_chunk)
            created_chunks.append(pdf_chunk)
        
        db.session.commit() # Commit all new chunks at once
        
        print(f"Prepared and saved {len(created_chunks)} chunks.")
        return created_chunks # Return the list of created objects

        
        
        
     
     
    '''
        1)  In Section Heading Split we use NLP techniques using reges
            for sentence detection
        2)  Detect headings with regex
        3)  Group sentences under headings into chunks
        4)  Return a list of dicts with content, chunk_index, 
            start_char, end_char
    '''   
    def section_heading_split(self, text: str,max_chunk_size: int = 2000, overlap: int = 200) -> list:
        
        '''
            Splits text into chunks based on headings.
            Returns list of dicts with content, chunk_index, 
            start_char, end_char.
        '''
        
        final_chunks=[]
        #regex pattens for headings
        heading_pattern = re.compile(r'(^\d+(\.\d+)*\s.*)|(^Chapter\s\d+)', re.MULTILINE)
        # most chapters work with 1, 2.1 or Chapter X etc
        
        #Find all heading matches in the text
        matches=list(heading_pattern.finditer(text))
        
        if not matches:
            return self.split_by_sentence(text)
        
        start_pos=0
        raw_chunks=[]
        
        if matches[0].start() > 0:
            raw_chunks.append(text[0:matches[0].start()].strip())
       
        #create chunks based on headings positions
        for i, match in enumerate(matches):
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            raw_chunks.append(text[start_pos:end_pos].strip())
            
            
        '''
         2. Process raw chunks: subdivide if too large and add overlap
        '''
        
        chunk_idx_counter=0
        for i, chunk_text in enumerate(raw_chunks):
            
            '''
                OVERLAP-LOGIc
                Prepend the end of the PREVIOUS 
                chunk to the current one
            '''
           
            if i > 0 and overlap > 0:
                # Find the last N characters of the previous chunk
                overlap_text = raw_chunks[i-1][-overlap:]
                chunk_text = overlap_text + "\n...\n" + chunk_text


            '''
                SUBDIVISION LOGIC
                If the chunk is still too big, split it by sentences
            '''
            
            if len(chunk_text) > max_chunk_size:
                # Use your existing function to split the oversized chunk
                sub_chunks = self.split_by_sentence(chunk_text, max_chunk_size, overlap)
                for sub_chunk in sub_chunks:
                    sub_chunk['chunk_index'] = chunk_idx_counter
                    final_chunks.append(sub_chunk)
                    chunk_idx_counter += 1
                    
            # Otherwise, add the chunk as is
            elif chunk_text:
                final_chunks.append({
                    "content": chunk_text,
                    "chunk_index": chunk_idx_counter,
                })
                chunk_idx_counter += 1
                
        return final_chunks
    
   
    def split_by_sentence(self,text: str, max_chunk_size: int = 2000, overlap_sentences: int = 2) -> list:
        """
        Splits text into chunks by sentences, ensuring no chunk exceeds max_chunk_size.
        Creates a more robust overlap by reusing the last few sentences of the previous chunk.

        Args:
            text: The input text to split.
            max_chunk_size: The maximum number of characters for a chunk.
            overlap_sentences: The number of sentences from the end of the previous
                                chunk to prepend to the next one.

        Returns:
            A list of dictionaries, each containing the chunk content and its index.
        """
        if not text:
            return []

        # Use spaCy to efficiently split the text into sentences
        doc = nlp(text)
        sentences = list(doc.sents)

        chunks = []
        current_chunk_sentences = []
        current_chunk_len = 0
        chunk_idx_counter = 0

        for i, sentence in enumerate(sentences):
            # Check if adding the next sentence would exceed the max size
            if current_chunk_len + len(sentence.text_with_ws) > max_chunk_size and current_chunk_sentences:
                # 1. Finalize the current chunk
                chunks.append({
                    "content": "".join([s.text_with_ws for s in current_chunk_sentences]).strip(),
                    "chunk_index": chunk_idx_counter
                })
                chunk_idx_counter += 1

                # 2. Start a new chunk with an overlap of the last few sentences
                # This is more robust than character-based overlap
                start_index_for_overlap = max(0, len(current_chunk_sentences) - overlap_sentences)
                new_chunk_start_sentences = current_chunk_sentences[start_index_for_overlap:]
                
                # Reset the current chunk to the overlapping sentences
                current_chunk_sentences = new_chunk_start_sentences
                current_chunk_len = sum(len(s.text_with_ws) for s in new_chunk_start_sentences)

            # 3. Add the current sentence to the new or existing chunk
            current_chunk_sentences.append(sentence)
            current_chunk_len += len(sentence.text_with_ws)

        # Add the final remaining chunk
        if current_chunk_sentences:
            chunks.append({
                "content": "".join([s.text_with_ws for s in current_chunk_sentences]).strip(),
                "chunk_index": chunk_idx_counter
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
        
        i=0
        while i < len(tokens):
            chunk_tokens = tokens[i:i+max_tokens]
            chunk_text = " ".join(chunk_tokens) # FIX: join with a space

            chunks.append({
                "content": chunk_text,
                "chunk_index": idx,
            })
            idx += 1
            i += max_tokens - overlap
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
         
        if not self.hf_model:
                raise RuntimeError("Hugging Face model is not available.")
            
        try:
        
            ''' 
                1. Load a pre-trained Sentence Transformer model
                all-MiniLM-L6-v2' is a good starting point
            '''
        
            
            
            ''' 2. Extract the content from the PDFChunk objects '''

            chunk_contents = [chunk.content for chunk in pdf_chunks]

            logging.info(f"Encoding {len(chunk_contents)} chunks to generate embeddings.")
            
            ''' 3. Generate embeddings for all chunks '''
            embeddings = self.hf_model.encode(chunk_contents, convert_to_numpy=True)
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