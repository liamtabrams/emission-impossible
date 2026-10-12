import os

from dotenv import load_dotenv

# load environment variables
load_dotenv()
project_id = os.getenv('GCP_PROJECT_ID')
bucket_name = os.getenv('GCP_BUCKET_NAME')
service_account_key = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

# csv written to the bucket by the /transform endpoint
file_name = 'processed/co2_gdp_by_state_year.csv'
