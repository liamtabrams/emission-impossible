# read/write GCS
from google.cloud import storage
from google.oauth2 import service_account

def upload_to_gcs(service_account_key, project_id, bucket_name, file_name, data):
    """Upload data to the bucket as file_name."""
    credentials = service_account.Credentials.from_service_account_file\
        (service_account_key)
    client = storage.Client(project=project_id, credentials=credentials)
    bucket = client.bucket(bucket_name)
    file = bucket.blob(file_name)
    file.upload_from_string(data)
