import os

from dotenv import load_dotenv

# load environment variables.
load_dotenv()

project_id = os.getenv("GCP_PROJECT_ID")
bucket_name = os.getenv("GCP_BUCKET_NAME")
service_account_key = os.getenv("GCP_SERVICE_ACCOUNT_KEY")
