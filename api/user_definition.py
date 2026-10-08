import os

from dotenv import load_dotenv

# load environment variables.
load_dotenv()

project_id = os.getenv("GCP_PROJECT_ID")
bucket_name = os.getenv("GCP_BUCKET_NAME")
service_account_key = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
bea_api_key = os.getenv("BEA_API_KEY")
