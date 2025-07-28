# Adobe India Hackathon - Connecting the Dots: Round 1A

### Solution Structure


```
adobe_hackathon_round1a/
├── Dockerfile
├── input
│   ├── Linux-Tutorial (Copy).pdf
│   └── Linux-Tutorial.pdf
├── output
│   ├── Linux-Tutorial (Copy).json
│   └── Linux-Tutorial.json
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
###  Our Approach

1.   **PDF Parsing (PyMuPDF):** The solution utilizes `PyMuPDF` (known as `fitz` in Python) for efficient parsing of PDF documents. It extracts all text blocks, along with critical properties such as font size, bold status, and their vertical position on the page.
    
2. **Dynamic Font Size Analysis:** A crucial step involves scanning the entire document to determine the maximum font size used. This maximum size then serves as a baseline to define relative thresholds for identifying different heading levels (H1, H2, H3). This makes the system adaptive to various document designs that may not use absolute standard font sizes.
    
3.  **Robust Heading Heuristics:** Headings are identified based on a combination of criteria:
    
    -   **Font Size:** Headings are expected to have a significantly larger font size than regular body text.
        
    -   **Boldness:** Headings, especially H1 and H2, are typically bold.
        
    -   **Length & Punctuation:** Headings are generally concise and do not typically end with sentence-ending punctuation like a period. Heuristics are in place to filter out overly long lines or those ending with periods that might otherwise be misclassified.
        
    -   **Exclusion of List Items:** Lines that start with common list markers (like bullets or sequential numbers) are usually excluded from being identified as major headings, preventing misinterpretations of lists as structural elements.
        
4.    **Title Extraction:** The document title is typically identified as the largest and most prominent (often bold) text block found on the first page of the document.
    
5.   **Structured Output Generation:** The extracted document title and the identified headings (along with their determined level, original text, and starting page number) are then formatted into a JSON structure as specified by the hackathon requirements. The `section_title` field specifically contains the cleaned heading text.

---

### How to Build and Run the Solution 

#### Building the image
* Have docker installed on your system. 
* Place an input sample PDF file (example `Linux-Tutorial.pdf`) inside the `input/` directory. 
*  Build the Docker Image 
	 ```bash
	docker build --platform linux/amd64 -t adobe_hackathon_r1a:latest .
	```

#### Run the container
* After successfully building the image, run the container using the following command:
	```bash
	docker run --rm -v "$(pwd)/input:/app/input" -v "$(pwd)/output:/app/output" --network none adobe_hackathon_r1a:latest
	```

---
### Output
The output JSON files are created in the `output` folder for each of the input files.

We used the `Linux_Tutorial.pdf` file (49 pages) and it's copy to test both multiple inputs and the speed. And in our sandbox environment comprising of 6 GB RAM and 4 Core CPU, the files were processed within **2 seconds** boasting the efficiency of our solution.


![1a](https://ik.imagekit.io/8zofjhk6p/1a_benchmark.png)

---

### Requirement Checklist:

- ✔️ Every PDF in the input directory is processed.
- ✔️ JSON output files are generated for each PDF.
- ✔️ Output format matches the required structure.
- ✔️ Output conforms to the schema provided in 	`output_schema.json`.
- ✔️ Processing for 50-page PDFs completes within **2** seconds.
- ✔️ Solution works without internet access.
- ✔️ Memory usage stays way below the 16GB limit.
- ✔️ Compatible with AMD64 architecture.

