# Start with Python 3.13 base image (-slim variant)
FROM python:3.13-slim

# Set a working dir
WORKDIR /streamlit

# Copy all the files to the image's working dir
COPY * ./

# Install all required python packages and libraries
RUN pip install -r requirements.txt

# Expose a port
EXPOSE 8501

# Run streamlit application 
CMD ["streamlit", "run", "streamlit_app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
