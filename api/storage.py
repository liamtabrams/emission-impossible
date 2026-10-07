# read/write GCS
from google.cloud import storage
from google.oauth2 import service_account


def upload_to_gcs(service_account_key, project_id, bucket_name, file_name, data):
    """Upload data to the bucket as file_name."""
    credentials = service_account.Credentials.from_service_account_file(
        service_account_key
    )
    client = storage.Client(project=project_id, credentials=credentials)
    bucket = client.bucket(bucket_name)
    file = bucket.blob(file_name)
    file.upload_from_string(data)


def download_from_gcs(service_account_key, project_id, bucket_name, file_name):
    """Download file_name from the bucket and return its contents as bytes."""
    credentials = service_account.Credentials.from_service_account_file(
        service_account_key
    )
    client = storage.Client(project=project_id, credentials=credentials)
    bucket = client.bucket(bucket_name)
    return bucket.blob(file_name).download_as_bytes()


def list_gcs_files(service_account_key, project_id, bucket_name, prefix):
    """Return the names of all files in the bucket whose path starts with prefix."""
    credentials = service_account.Credentials.from_service_account_file(
        service_account_key
    )
    client = storage.Client(project=project_id, credentials=credentials)
    files = client.list_blobs(bucket_name, prefix=prefix)

    file_names = []
    for file in files:
        file_names.append(file.name)
    return file_names
