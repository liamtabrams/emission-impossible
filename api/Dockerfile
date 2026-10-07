# Start with Python 3.13 base image (-slim variant)
FROM python:3.13-slim

# Set a working dir
WORKDIR /api

# Copy all the files and directories to the image's working directory
COPY . ./

# Install all required python packages and libraries
RUN pip install -r requirements.txt

# Expose a port
EXPOSE 8000

# Run FastAPI application on 0.0.0.0
CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
