
FROM python:3.8-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .


RUN python -m nltk.downloader punkt
RUN python -m nltk.downloader wordnet
# Expose FastAPI default port
EXPOSE 8001

# Command to run the API
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
