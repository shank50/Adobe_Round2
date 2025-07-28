# Use a lightweight Python base image compatible with AMD64
FROM --platform=linux/amd64 python:3.9-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download the small English spaCy model during build
RUN python -m spacy download en_core_web_lg --no-cache-dir

# ... (rest of Dockerfile) ...

# Create input and output directories
RUN mkdir -p /app/input /app/output

# Copy the application source code
COPY src/ /app/src/

# Set the entrypoint command
CMD ["python", "/app/src/main.py"]
