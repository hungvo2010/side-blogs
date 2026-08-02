FROM python:3.11-slim

WORKDIR /app

# Copy only ai-blog-automation (the app runs from this dir)
COPY ai-blog-automation/ /app/

# Install deps
RUN pip install --no-cache-dir -r requirements.txt

# Streamlit runs on port 7860 in HF Spaces
EXPOSE 7860

ENV PYTHONPATH=/app/src
ENV STREAMLIT_SERVER_PORT=7860
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

CMD ["streamlit", "run", "streamlit_app/app.py", "--server.headless", "true"]
