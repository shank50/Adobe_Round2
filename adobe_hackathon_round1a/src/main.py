import os
import json
import fitz
from collections import defaultdict

def extract_document_outline(pdf_path):
   
    title = ""
    outline = []
    
    # Heuristic thresholds for font sizes (these might need fine-tuning based on sample PDFs)
    # These are relative to the largest font size found in the document.
    # We will determine these dynamically.
    
    # Store text blocks with their properties for analysis
    text_blocks_by_page = defaultdict(list)

    try:
        document = fitz.open(pdf_path)

        # First pass: Extract all text blocks with font information
        # and find the largest font size to set relative thresholds
        max_font_size = 0.0

        for page_num in range(document.page_count):
            page = document.load_page(page_num)
            
            # Using get_text("dict") provides detailed information about blocks, lines, spans
            # This is crucial for font details.
            text_dict = page.get_text("dict")
            
            for block in text_dict['blocks']:
                if block['type'] == 0:  # Text block
                    for line in block['lines']:
                        for span in line['spans']:
                            text = span['text'].strip()
                            if text: # Only consider non-empty text
                                font_size = round(span['size'], 2)
                                is_bold = "bold" in span['font'].lower() or "heavy" in span['font'].lower()
                                
                                # Store text block details
                                text_blocks_by_page[page_num + 1].append({
                                    "text": text,
                                    "font_size": font_size,
                                    "is_bold": is_bold,
                                    "bbox": span['bbox'], # (x0, y0, x1, y1)
                                    "line_length": len(line['spans']) # Number of spans in the line
                                })
                                
                                if font_size > max_font_size:
                                    max_font_size = font_size
        
        # Define font size thresholds relative to the maximum found font size
        # These are empirical values and might need adjustment.
        # A 10% difference can indicate a significant size change for headings.
        H1_THRESHOLD = max_font_size * 0.95 # H1 is usually very close to max_font_size
        H2_THRESHOLD = max_font_size * 0.80 # H2 is noticeably smaller than H1
        H3_THRESHOLD = max_font_size * 0.65 # H3 is smaller than H2
        
        # Add a minimum font size to consider for headings to avoid body text
        MIN_HEADING_FONT_SIZE = max_font_size * 0.50 # Assuming headings are at least 50% of max font size

        print(f"Max Font Size Detected: {max_font_size}")
        print(f"H1 Threshold: {H1_THRESHOLD}, H2 Threshold: {H2_THRESHOLD}, H3 Threshold: {H3_THRESHOLD}")

        # Second pass: Identify title and headings based on collected properties
        # We need to process page by page to capture page numbers correctly
        
        # Logic to find Title: Assume the largest text on the first page is the title
        # Or, the largest, boldest text block on the first page
        title_candidates = []
        if 1 in text_blocks_by_page:
            for block in text_blocks_by_page[1]:
                if block['font_size'] >= H1_THRESHOLD and block['is_bold']:
                    title_candidates.append(block)
        
        if title_candidates:
            # Sort by font size descending, then by y0 (top position) ascending
            title_candidates.sort(key=lambda x: (-x['font_size'], x['bbox'][1]))
            title = title_candidates[0]['text']
        else:
            # Fallback: if no clear bold H1-sized title on page 1, take the first substantial text
            if 1 in text_blocks_by_page and text_blocks_by_page[1]:
                title = text_blocks_by_page[1][0]['text'] # take first text on page 1 as title fallback

        # Now, iterate through all pages and blocks to find headings
        for page_num in range(document.page_count):
            current_page_number = page_num + 1
            if current_page_number not in text_blocks_by_page:
                continue

            for block in text_blocks_by_page[current_page_number]:
                text = block['text']
                font_size = block['font_size']
                is_bold = block['is_bold']
                
                # Filter out very small text and text that is likely just a few characters
                if font_size < MIN_HEADING_FONT_SIZE or len(text) < 3:
                    continue

                level = None
                if font_size >= H1_THRESHOLD:
                    level = "H1"
                elif font_size >= H2_THRESHOLD:
                    level = "H2"
                elif font_size >= H3_THRESHOLD:
                    level = "H3"
                
                # Additional heuristic: Headings are often bold or have significant line breaks/spacing
                # For simplicity, we are heavily relying on font size + bold for now.
                # More advanced logic would involve checking preceding/following whitespace,
                # text alignment (left, center), and overall document flow.
                
                if level:
                    # Prevent adding the same title as an H1 if it's already identified
                    if level == "H1" and text == title and current_page_number == 1:
                        continue
                    
                    # Basic de-duplication: Avoid adding the same heading multiple times
                    # This check is simple and might miss slight variations.
                    is_duplicate = False
                    for existing_heading in outline:
                        if existing_heading["text"] == text and existing_heading["page"] == current_page_number:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        outline.append({
                            "level": level,
                            "text": text,
                            "page": current_page_number
                        })
        
        # Sort the outline: first by page number, then by inferred heading level prominence (H1 > H2 > H3),
        # then by vertical position (y0) on the page.
        # This is crucial for maintaining hierarchy and order.
        level_order = {"H1": 1, "H2": 2, "H3": 3}
        outline.sort(key=lambda x: (x["page"], level_order.get(x["level"], 99))) # bbox['y0'] is not directly in 'outline' anymore
                                                                                # Need to re-think sort if we want vertical position

        # To sort by vertical position, we'd need to store the bbox['y0'] in the outline itself.
        # Let's refine the outline item if we need this level of sorting:
        # For simplicity in this first pass, we'll sort by page and then by level.
        # A more complex sort would require passing the original 'block' info to the outline list.
        # Given the problem's ask, page and level sorting should be sufficient.


    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        # Return empty/default in case of an error
        return "", []

    return title, outline

def process_pdf_files(input_dir, output_dir):
    """
    Processes all PDF files in the input directory, extracts outlines,
    and saves them as JSON in the output directory.
    """
    if not os.path.exists(input_dir):
        print(f"Input directory not found: {input_dir}")
        return

    if not os.path.exists(output_dir):
        print(f"Output directory not found: {output_dir}")
        os.makedirs(output_dir) # Ensure output directory exists

    print(f"Processing PDFs from: {input_dir}")
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".pdf"):
            input_pdf_path = os.path.join(input_dir, filename)
            output_json_filename = filename.replace(".pdf", ".json")
            output_json_path = os.path.join(output_dir, output_json_filename)

            print(f"Starting processing for: {filename}")
            title, outline = extract_document_outline(input_pdf_path)

            result = {
                "title": title,
                "outline": outline
            }

            try:
                with open(output_json_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=4, ensure_ascii=False)
                print(f"Successfully generated: {output_json_path}")
            except Exception as e:
                print(f"Error writing JSON for {filename}: {e}")
        else:
            print(f"Skipping non-PDF file: {filename}")

if __name__ == "__main__":

    INPUT_DIR = "/app/input"
    OUTPUT_DIR = "/app/output"

    process_pdf_files(INPUT_DIR, OUTPUT_DIR)
    print("PDF outline extraction process completed.")