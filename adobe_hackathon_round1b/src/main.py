import os
import json
import fitz # PyMuPDF
import spacy
import re
from datetime import datetime
from collections import defaultdict

# --- Global NLP Model (Load once) ---
try:
    nlp = spacy.load("en_core_web_lg")
    print("SpaCy model 'en_core_web_lg' loaded successfully.")
    if nlp.vocab.vectors.name is None:
        print("[WARNING] The loaded SpaCy model 'en_core_web_lg' still has no word vectors loaded. This is unexpected for LG model. Falling back to keyword matching.")
        nlp = None # Force fallback if no vectors unexpectedly
except OSError:
    print("SpaCy model 'en_core_web_lg' not found. Please ensure it's downloaded during Docker build.")
    print("Falling back to keyword matching for relevance as no suitable NLP model is available.")
    nlp = None

# --- Round 1A Logic (Enhanced for Round 1B) ---

def extract_document_sections(pdf_path):
    """
    Extracts the title and detailed sections (H1, H2, H3) with their
    full text content and page numbers from a PDF.
    Focus on more robust heading identification and content accumulation.
    """
    title = ""
    sections = [] 
    
    document = fitz.open(pdf_path)
    
    text_blocks_on_pages = defaultdict(list)
    max_font_size = 0.0
    
    all_raw_lines_in_order = [] 

    for page_num in range(document.page_count):
        page = document.load_page(page_num)
        
        page_raw_blocks = page.get_text("dict")['blocks']
        
        for block_idx, block in enumerate(page_raw_blocks):
            if block['type'] == 0: # Text block
                for line_idx, line in enumerate(block['lines']):
                    line_text = "".join([span['text'] for span in line['spans']]).strip()
                    if not line_text: continue # Skip empty lines

                    first_span = line['spans'][0] if line['spans'] else {}
                    font_size = round(first_span.get('size', 0.0), 2)
                    is_bold = "bold" in first_span.get('font', '').lower() or "heavy" in first_span.get('font', '').lower()
                    
                    line_info = {
                        "text": line_text,
                        "font_size": font_size,
                        "is_bold": is_bold,
                        "bbox_y0": line['bbox'][1], 
                        "page": page_num + 1,
                        "is_heading_candidate": False, 
                        "actual_level": None
                    }
                    text_blocks_on_pages[page_num + 1].append(line_info)
                    all_raw_lines_in_order.append(line_info)

                    if font_size > max_font_size:
                        max_font_size = font_size
    
    if not all_raw_lines_in_order:
        print(f"Warning: No meaningful text lines found in {pdf_path}")
        return "", []

    H1_REL_THRESHOLD = 0.90 
    H2_REL_THRESHOLD = 0.75
    H3_REL_THRESHOLD = 0.60
    
    MIN_BODY_FONT_SIZE_APPROX = 10.0 
    
    h1_thresh = max_font_size * H1_REL_THRESHOLD
    h2_thresh = max_font_size * H2_REL_THRESHOLD
    h3_thresh = max_font_size * H3_REL_THRESHOLD
    
    h3_thresh = max(h3_thresh, MIN_BODY_FONT_SIZE_APPROX * 1.2) 
    h2_thresh = max(h2_thresh, h3_thresh * 1.15) 
    h1_thresh = max(h1_thresh, h2_thresh * 1.1)  

    # Heuristic to find Title: Largest text on the first page, likely bold.
    title_candidates = []
    if 1 in text_blocks_on_pages:
        for line_info in text_blocks_on_pages[1]:
            if line_info['font_size'] >= h1_thresh and \
               len(line_info['text'].split()) < 20 and \
               (line_info['is_bold'] or line_info['font_size'] == max_font_size):
                title_candidates.append(line_info)
        
        if title_candidates:
            title_candidates.sort(key=lambda x: (-x['font_size'], x['bbox_y0']))
            title = title_candidates[0]['text']
            # Remove title text from processing stream
            all_raw_lines_in_order = [b for b in all_raw_lines_in_order if not (b['text'] == title and b['page'] == 1)]
        else:
            if all_raw_lines_in_order and all_raw_lines_in_order[0]['page'] == 1:
                title = all_raw_lines_in_order[0]['text']
                all_raw_lines_in_order = all_raw_lines_in_order[1:] # Remove first line if used as title

            
    current_section_content_lines = []
    current_section_meta = None
    
    for i, line_info in enumerate(all_raw_lines_in_order):
        text = line_info['text']
        font_size = line_info['font_size']
        is_bold = line_info['is_bold']
        page = line_info['page']

        is_heading = False
        determined_level = None

        # Check for common non-heading starting characters (bullets, short numbers)
        # combined with less-than-H1 font size to avoid misclassification.
        if (font_size < h1_thresh and re.match(r'^[•\*-]\s*|^\d+\.\s*|^\d+\.\d+\s*$', text.split(' ')[0])):
            # This is likely a list item or sub-point, not a major heading.
            is_heading = False # Explicitly mark as not a heading
        else:
            # Apply heading criteria
            if is_bold and font_size >= h1_thresh and len(text.split()) < 15:
                determined_level = "H1"
                is_heading = True
            elif is_bold and font_size >= h2_thresh and len(text.split()) < 20:
                determined_level = "H2"
                is_heading = True
            elif font_size >= h3_thresh and len(text.split()) < 25 and not text.endswith('.'):
                # H3 can be less strictly bold, but still short and not ending with a period.
                determined_level = "H3"
                is_heading = True
            
            # Further filter: Ensure potential headings are not just short, common words or symbols.
            if is_heading and (len(text.strip()) < 4 or text.strip().lower() in ["summary", "introduction", "conclusion"]):
                # Allow 'Summary', 'Introduction', 'Conclusion' as headings if matched elsewhere.
                # But filter very short non-semantic "headings" like '1.', '2.', etc. unless they're followed by meaningful text.
                if re.match(r'^\d+(\.\d+)*\s*$', text.strip()): # e.g. "1.", "2.1" without other text
                    is_heading = False
                elif len(text.strip()) < 4 and not is_bold: # Very short non-bold text usually isn't a heading
                    is_heading = False


        if is_heading:
            if current_section_meta is not None:
                final_content = " ".join(current_section_content_lines).strip()
                # Replace multiple newlines with single spaces for cleaner text
                final_content = re.sub(r'\n\s*\n', ' ', final_content) 
                final_content = re.sub(r'\s+', ' ', final_content) # Collapse multiple spaces
                
                if final_content: # Only add if content exists for the section
                    sections.append({
                        "level": current_section_meta["level"],
                        "text": current_section_meta["text"], 
                        "page": current_section_meta["page"],
                        "full_content": final_content
                    })
            
            # Start new section
            current_section_meta = {
                "level": determined_level,
                "text": text,
                "page": page
            }
            current_section_content_lines = [] 
        else:
            current_section_content_lines.append(text)
    
    # After the loop, add the very last section if any content was accumulated
    if current_section_meta is not None:
        final_content = " ".join(current_section_content_lines).strip()
        final_content = re.sub(r'\n\s*\n', ' ', final_content)
        final_content = re.sub(r'\s+', ' ', final_content)
        
        if final_content:
            sections.append({
                "level": current_section_meta["level"],
                "text": current_section_meta["text"],
                "page": current_section_meta["page"],
                "full_content": final_content
            })
            
    level_order = {"H1": 1, "H2": 2, "H3": 3}
    sections.sort(key=lambda x: (x["page"], level_order.get(x["level"], 99)))

    return title, sections


# --- Round 1B Logic (Minor adjustment to refined_text and cleaning) ---

def clean_text_for_output(text):
    """Cleans text by removing common bullet/list characters and extra whitespace."""
    if not text:
        return ""
    # Remove leading bullet points or common list numbers (e.g., "• Text", "1. Text", "- Text")
    text = re.sub(r'^(?:[•\*-]|\d+\.|\d+\.\d+\.)\s*', '', text, flags=re.MULTILINE).strip()
    # Replace multiple newlines/whitespace with a single space for fluidity
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def analyze_document_collection(collection_path, output_base_path):
    """
    Analyzes a document collection based on persona and job-to-be-done.
    """
    print(f"\n--- Analyzing Collection: {os.path.basename(collection_path)} ---")
    
    collection_input_json_path = os.path.join(collection_path, "challenge1b_input.json")
    pdf_dir = os.path.join(collection_path, "PDFs")

    if not os.path.exists(collection_input_json_path):
        print(f"Error: {collection_input_json_path} not found.")
        return
    if not os.path.exists(pdf_dir):
        print(f"Error: PDFs directory not found at {pdf_dir}")
        return

    with open(collection_input_json_path, 'r', encoding='utf-8') as f:
        collection_input = json.load(f)

    challenge_id = collection_input["challenge_info"]["challenge_id"]
    test_case_name = collection_input["challenge_info"]["test_case_name"]
    input_documents_meta = collection_input["documents"]
    persona_role = collection_input["persona"]["role"]
    job_task = collection_input["job_to_be_done"]["task"]

    print(f"Challenge ID: {challenge_id}, Test Case: {test_case_name}")
    print(f"Persona: {persona_role}, Job: {job_task}")

    job_doc = nlp(job_task) if nlp else None
    persona_doc = nlp(persona_role) if nlp else None
    
    nlp_has_vectors = (nlp is not None and job_doc is not None and job_doc.has_vector and \
                       persona_doc is not None and persona_doc.has_vector)

    all_sections_for_processing = [] 
    processed_input_filenames = []

    for doc_meta in input_documents_meta:
        filename = doc_meta["filename"]
        pdf_path = os.path.join(pdf_dir, filename)
        
        if not os.path.exists(pdf_path):
            print(f"Warning: PDF not found: {pdf_path}. Skipping.")
            continue
        
        print(f"  Extracting sections from {filename}...")
        doc_title, sections_data_from_pdf = extract_document_sections(pdf_path)
        
        processed_input_filenames.append(filename)

        for section in sections_data_from_pdf:
            section["document"] = filename
            
            relevance_score = 0.0
            section_text_doc = nlp(section["full_content"]) if nlp else None

            if nlp_has_vectors and section_text_doc and section_text_doc.text.strip():
                try:
                    job_similarity = section_text_doc.similarity(job_doc) if job_doc and job_doc.has_vector else 0.0
                    persona_similarity = section_text_doc.similarity(persona_doc) if persona_doc and persona_doc.has_vector else 0.0
                    relevance_score = (job_similarity * 0.7) + (persona_similarity * 0.3)
                except ValueError: 
                    relevance_score = 0.0
            else:
                job_keywords = set(j for j in job_task.lower().split() if len(j) > 2)
                section_keywords = set(s for s in section["full_content"].lower().split() if len(s) > 2)
                matching_keywords = len(job_keywords.intersection(section_keywords))
                section_len = len(section_keywords)
                relevance_score = matching_keywords / section_len if section_len > 0 else 0

            section["relevance_score"] = relevance_score 
            all_sections_for_processing.append(section)

    all_sections_for_processing.sort(key=lambda x: x["relevance_score"], reverse=True)

    extracted_sections_output = []
    subsection_analysis_output = []
    
    top_n_sections_for_analysis = 10 

    for i, section in enumerate(all_sections_for_processing):
        # Apply cleanup to section_title before output
        cleaned_section_title = clean_text_for_output(section["text"])

        extracted_sections_output.append({
            "document": section["document"],
            "section_title": cleaned_section_title, 
            "importance_rank": i + 1,
            "page_number": section["page"]
        })

        if i < top_n_sections_for_analysis:
            refined_text = ""
            full_content = section["full_content"]

            if nlp_has_vectors and full_content and full_content.strip():
                section_nlp_doc = nlp(full_content)
                sentences = [sent.text.strip() for sent in section_nlp_doc.sents if sent.text.strip() and len(sent.text.strip()) > 15] 
                
                sentence_scores = []
                for sent_text in sentences:
                    sent_nlp_doc = nlp(sent_text)
                    if sent_nlp_doc.has_vector and job_doc and job_doc.has_vector: 
                        sentence_scores.append((sent_nlp_doc.similarity(job_doc), sent_text))
                    else:
                        sent_keywords = set(s for s in sent_text.lower().split() if len(s) > 2)
                        job_keywords = set(j for j in job_task.lower().split() if len(j) > 2)
                        sent_len = len(sent_keywords)
                        score = len(sent_keywords.intersection(job_keywords)) / sent_len if sent_len > 0 else 0
                        sentence_scores.append((score, sent_text))

                sentence_scores.sort(key=lambda x: x[0], reverse=True)
                
                refined_text_parts = []
                min_score_threshold_for_sentence = 0.3 if nlp_has_vectors else 0.1 
                sentence_count = 0
                for score, text in sentence_scores:
                    if score >= min_score_threshold_for_sentence and sentence_count < 3: 
                        # Apply cleanup here as well for sentence text
                        cleaned_sent_text = clean_text_for_output(text)
                        if cleaned_sent_text: # Only add if after cleaning it's not empty
                            refined_text_parts.append(cleaned_sent_text)
                            sentence_count += 1
                    elif nlp_has_vectors and score < min_score_threshold_for_sentence:
                        break 
                    elif not nlp_has_vectors and score == 0:
                        break 
                
                refined_text = " ".join(refined_text_parts).strip()
                
            elif full_content: 
                 lines = [line.strip() for line in full_content.split('\n') if line.strip() and len(line.strip()) > 20] 
                 # Apply cleanup to each line if using fallback
                 cleaned_lines = [clean_text_for_output(line) for line in lines]
                 refined_text = "\n".join(cleaned_lines[:3]).strip()
            
            if refined_text:
                subsection_analysis_output.append({
                    "document": section["document"],
                    "refined_text": refined_text,
                    "page_number": section["page"] 
                })

    output_data = {
        "metadata": {
            "input_documents": processed_input_filenames,
            "persona": persona_role,
            "job_to_be_done": job_task,
            "processing_timestamp": datetime.now().isoformat()
        },
        "extracted_sections": extracted_sections_output,
        "subsection_analysis": subsection_analysis_output
    }

    collection_output_dir = os.path.join(output_base_path, os.path.basename(collection_path))
    os.makedirs(collection_output_dir, exist_ok=True)
    
    output_json_path = os.path.join(collection_output_dir, "challenge1b_output.json")
    
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    print(f"  Generated output for {os.path.basename(collection_path)}: {output_json_path}")


if __name__ == "__main__":
    INPUT_ROOT_DIR = "/app/input"
    OUTPUT_ROOT_DIR = "/app/output"

    if not os.path.exists(INPUT_ROOT_DIR):
        print(f"Error: Input root directory not found: {INPUT_ROOT_DIR}")
        exit(1)
    
    # Ensure the root output dir exists in case it was entirely removed manually
    os.makedirs(OUTPUT_ROOT_DIR, exist_ok=True)

    for collection_name in os.listdir(INPUT_ROOT_DIR):
        collection_path = os.path.join(INPUT_ROOT_DIR, collection_name)
        
        # Sort collection names to ensure consistent processing order (optional but good practice)
        if os.path.isdir(collection_path) and collection_name.startswith("Collection_"):
            analyze_document_collection(collection_path, OUTPUT_ROOT_DIR)
        else:
            print(f"Skipping non-collection directory or non-directory item in input root: {collection_name}")

    print("\nAll document collections processed.")
