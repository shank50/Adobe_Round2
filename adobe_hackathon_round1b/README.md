
# Adobe India Hackathon - Connecting the Dots: Round 1B Solution

### Solution Structure

```
adobe_hackathon_round1b/
├── Dockerfile
├── input
│   ├── Collection_1
│   │   ├── challenge1b_input.json
│   │   └── PDFs
│   │       ├── South of France - Cities.pdf
│   │       ├── South of France - Cuisine.pdf...(more files)
│   ├── Collection_2
│   │   ├── challenge1b_input.json
│   │   └── PDFs
│   │       ├── Learn Acrobat - Create and Convert_1.pdf
│   │       ├── Learn Acrobat - Create and Convert_2.pdf
│   │       ├── Learn Acrobat - Edit_1.pdf...(more files)
│   └── Collection_3
│       ├── challenge1b_input.json
│       └── PDFs
│           ├── Breakfast Ideas.pdf
│           ├── Dinner Ideas - Mains_1.pdf...(more files)
├── output
│   ├── Collection_1
│   │   └── challenge1b_output.json
│   ├── Collection_2
│   │   └── challenge1b_output.json
│   └── Collection_3
│       └── challenge1b_output.json
├── README.md
├── requirements.txt
└── src
    └── main.py

```
---

### Models and Libraries Used

-   **PyMuPDF (fitz):** Used for efficient PDF parsing and text extraction.
    
-   **Python Standard Libraries:** For file I/O, JSON serialization, and fundamental data structures.
    
-   **`re` module:** For regular expression-based text processing and cleaning.
---

### Approach Details


1.  **Multi-Collection and Input Configuration Handling:**
    
    -   The solution processes multiple independent document collections. Each collection is expected to be in its own subdirectory within the `input/` folder (e.g., `Collection_1`, `Collection_2`).
        
    -   For each collection, it reads a `challenge1b_input.json` file. This file precisely defines the PDFs within that collection, the user's `persona` (role), and the `job_to_be_done` (task).
        
2.  **Advanced PDF Sectioning (Reusing and Enhancing Round 1A Logic):**
    
    -   It reuses and enhances the robust PDF parsing and heading detection logic from Round 1A.
        
    -   `PyMuPDF` is used to extract all text blocks along with font details (size, bold status, position).
        
    -   Dynamic thresholds based on the document's maximum font size, combined with stricter heuristics (e.g., word count limits, exclusion of common list markers and trailing punctuation), are used to accurately identify true hierarchical headings (H1, H2, H3).
        
    -   Text content is intelligently grouped under these detected headings to form coherent "sections." This ensures that `full_content` passed to the NLP module represents meaningful blocks of text.
        
3.  **Semantic Relevance Ranking (SpaCy `en_core_web_lg`):**
    
    -   The core of the "intelligence" is powered by `spaCy`'s `en_core_web_lg` (large) English language model. This model includes high-quality pre-trained word vectors, enabling advanced semantic understanding.
        
    -   The `persona`'s role and the `job_to_be_done` task are converted into numerical vector representations using `spaCy`.
        
    -   Similarly, the `full_content` of each extracted document section is transformed into its vector representation.
        
    -   A relevance score is calculated for each section by computing the cosine similarity between the section's vector and the vectors of both the `job_to_be_done` and the `persona`. The `job_to_be_done`'s similarity is weighted more heavily (e.g., 70%) to prioritize direct task relevance.
        
    -   All extracted sections from all documents within a collection are then sorted and assigned an `importance_rank` based on these calculated relevance scores (lower rank means higher relevance).
        
    -   (Fallback Mechanism): If the `en_core_web_lg` model cannot be loaded or unexpectedly lacks word vectors, the system gracefully falls back to a normalized keyword matching strategy. This fallback counts shared significant keywords (longer than 2 characters) between the query and the section, normalized by the section's keyword count, to still provide a basic level of relevance ordering.
        
4.  **Refined Text Generation (Sub-section Analysis):**
    
    -   For the top 10 most relevant sections, a more granular analysis is performed to generate concise `refined_text` snippets.
        
    -   `spaCy`'s robust sentence segmentation is applied to the `full_content` of these top sections.
        
    -   Each extracted sentence is then scored based on its semantic similarity to the `job_to_be_done` (or by keyword matching in fallback mode).
        
    -   The top 1-3 most relevant sentences (that meet minimum length and relevance thresholds) are selected to form the `refined_text` for the subsection analysis. This aims to provide highly condensed, actionable information.
        
5.  **Output Cleaning and Standardized Format:**
    
    -   A `clean_text_for_output` helper function is applied throughout the process. This function uses regular expressions to remove common PDF parsing artifacts such as leading bullet points (`•`, `*`, `-`), numerical list markers (e.g., `1.`, `1.1.`), and collapses multiple newlines and whitespace into single spaces. This ensures cleaner and more readable `section_title` and `refined_text` outputs.
        
    -   The final output for each collection is saved in a `challenge1b_output.json` file within a structured `output/Collection_X/` directory, conforming to the specified JSON schema.
        

## Models and Libraries Used

-   **PyMuPDF (fitz):** Used for efficient and robust PDF text and layout extraction.
    
-   **spaCy (en_core_web_lg):** For advanced Natural Language Processing, including tokenization, sentence segmentation, and pre-trained word vectors for semantic similarity calculations (approx. 500MB).
    
-   **Python Standard Library:** For file I/O, JSON processing, and fundamental data structures.
    
-   **`re` module:** For regular expression-based text processing and cleaning.

### How to Build and Run the Solution 

#### Building the image
* Have docker installed on your system. 
*  The `input/` directory should contain the `Collection_X` subdirectories, each with its `challenge1b_input.json` and `PDFs/` folder as structured above.
*  Build the Docker Image 
	 ```bash
	 docker build --platform linux/amd64 -t adobe_hackathon_r1b:latest .
	 ```

#### Run the container
* After successfully building the image, run the container using the following command:
	```bash 
	docker run --rm -v "$(pwd)/input:/app/input" -v "$(pwd)/output:/app/output" --network none adobe_hackathon_r1b:latest
	```

---
### Output
The output JSON files are created in the `output/Collection_X` folder for each of the input collections.

---
### Our testing
We used the sample files provided to test our solution. And in our sandbox environment comprising of 6 GB RAM and 4 Core CPU, the files were processed within **28 seconds** boasting the efficiency of our solution.

![1a](https://ik.imagekit.io/8zofjhk6p/1b_benchmark.png)
---
### Requirement Checklist