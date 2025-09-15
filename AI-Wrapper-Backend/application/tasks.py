from . import celery
from application.models import PDFFile, PDFChunk as PDFC, SummarizedPdfContent, QuestionBank
from application.database import db
import logging
from application.de import DecisionEngine
from celery import chain
import json
import math

from transformers import pipeline
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

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
        
    

        de.prepare_chunks(pdf_file.chunking_strategy,pdf_file.filepath,file_id)
        
        
        
        pdf_file.status = 'chunks_ready'
        db.session.commit()
        
        pdf_chunks=db.session.query(PDFC).filter_by(file_id=file_id).all()
        print(pdf_chunks)
        
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


@celery.task(bind=True)
def summarize_document_chunks(self,file_id):
    """
    A Celery task to generate summaries for all chunks of a specific PDF file.
    """
    # Tasks run outside the normal Flask request context, so we create one
    
    app,api,celery = create_app()
    with app.app_context():
        # --- All your original logic now lives inside the task ---
        
        pdf_record = PDFFile.query.get(file_id)
        if not pdf_record:
            print(f"Task failed: PDF with file_id {file_id} not found.")
            return
        # Initialize models
        
        chunk_summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        structured_summarizer = pipeline("summarization", model="t5-base")

        # Parameters
        batch_size = 5  # Number of chunks per summarization request
        chunk_max_length = 60
        chunk_min_length = 20
        final_max_length = 300
        final_min_length = 100
        
        try:
            all_chunks = [chunk for chunk in pdf_record.chunks if not chunk.chunk_summary]
            batch_summaries = []

            # Process chunks in batches
            # Create batch prompt by combining your structured chunk prompt
                
            for i in range(0, len(all_chunks), batch_size):
                batch_chunks = all_chunks[i:i + batch_size]

                # 1. Create a LIST of prompts, not a single string
                prompts_for_batch = []
                for chunk in batch_chunks:
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
                    prompts_for_batch.append(prompt)

                # 2. Pass the LIST to the pipeline. It will return a list of results.
                batch_results = chunk_summarizer(
                    prompts_for_batch, max_length=chunk_max_length, min_length=chunk_min_length, do_sample=False
                )

                # 3. Assign each summary to its corresponding chunk
                for chunk, result in zip(batch_chunks, batch_results):
                    summary_text = result['summary_text'].strip()
                    chunk.chunk_summary = summary_text
                    db.session.add(chunk)
                    batch_summaries.append(summary_text) # For the final summary

                # Commit DB once per batch
                db.session.commit()
                time.sleep(1)

            db.session.commit()
            # Create final structured summary using your second prompt
            final_prompt = f"""
            You are tasked with creating a structured summary from multiple individual summaries extracted from different sections of a document. These summaries may overlap or be slightly redundant. Your job is to:

            1. Consolidate the key points from the provided summaries.
            2. Eliminate redundancy and organize the information logically.
            3. Create a structured summary with headings and bullet points if applicable.
            4. Keep it concise while preserving important details.

            Here are the individual summaries:
            ---
            {" ".join(batch_summaries)}
            ---

            Structured Summary:
            """

            final_summary = structured_summarizer(
                final_prompt, max_length=final_max_length, min_length=final_min_length, do_sample=False
            )[0]['summary_text']

            # Save final summary in DB
            summary_entry = SummarizedPdfContent(
                summary_text=final_summary.strip(),
                original_pdf_id=pdf_record.file_id,
                user_id=pdf_record.user_id
            )
            db.session.add(summary_entry)
            db.session.commit()

            print(f"Final summary saved in database for file_id: {pdf_record.file_id}")

        except Exception as e:
            db.session.rollback()
            print(f"An error occurred during summarization for file_id {pdf_record.file_id}: {e}")
            raise
            
        
    


        
    
@celery.task(bind=True)
def question_generation(self,file_id):
    """
        Celery task to generate questions for a PDF file using existing NCERT exercises as context.
    """
    
    
    app,api,celery = create_app()
    with app.app_context():
        
        pdf_record = PDFFile.query.get(file_id)
        if not pdf_record:
            print(f"Task failed: PDF with file_id {file_id} not found.")
            return
        
        try:
            tokenizer = AutoTokenizer.from_pretrained("allenai/unifiedqa-t5-small", use_fast=False)
            model = AutoModelForSeq2SeqLM.from_pretrained("allenai/unifiedqa-t5-small")
            qg_pipeline = pipeline("text2text-generation", model=model, tokenizer=tokenizer)

            last_chunks = PDFC.query.filter_by(file_id=file_id).order_by(PDFC.chunk_index.desc()).limit(3).all()
            example_questions = []
            for chunk in last_chunks:
                if chunk.chunk_summary:
                    example_questions.append(chunk.chunk_summary)

            example_context = "\n".join(example_questions) if example_questions else "No example questions available."

            prompt = f"""
            You are tasked with generating 100 exam questions for a textbook chapter based on the following example questions. The questions should be diverse and cover the entire chapter content.

            Here are some example questions from the last page of the chapter:
            ---
            {example_context}
            ---

            Generate 100 questions in JSON format. Each question should have the following fields:
            1. question_text: The question statement.
            2. question_type: One of 'mcq', 'msq', 'numeric', 'integer'.
            3. options: A list of possible answers (only for 'mcq' and 'msq' types; for others, leave it empty or null).
            4. correct_answer: The correct answer(s) as a string or a list depending on the question type.

            Return only the JSON array without any extra text.
            """

            questions_output = qg_pipeline(prompt, max_length=512, num_return_sequences=1)

            questions_json = questions_output[0]['generated_text'].strip()

            try:
                questions_list = json.loads(questions_json)
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Response was:\n{questions_json}")
                raise

            for q in questions_list:
                question = QuestionBank(
                    question_text=q.get('question_text'),
                    question_type=q.get('question_type'),
                    options=json.dumps(q.get('options')) if q.get('options') else None,
                    correct_answer=json.dumps(q.get('correct_answer')) if isinstance(q.get('correct_answer'), list) else q.get('correct_answer'),
                    file_id=file_id,
                    user_id=pdf_record.user_id
                )
                db.session.add(question)

            db.session.commit()
            print(f"Successfully generated and stored {len(questions_list)} questions for file_id: {file_id}")

        except Exception as e:
            db.session.rollback()
            print(f"An error occurred during question generation for file_id {file_id}: {e}")
            raise
        
    
    