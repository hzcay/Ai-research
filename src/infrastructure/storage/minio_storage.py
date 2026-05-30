import io
from minio import Minio
from src.infrastructure.config.settings import get_settings

class MinioStorage:
    def __init__(self):
        settings = get_settings()
        self.client = Minio(
            settings.minio_url,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False
        )
        self.bucket_name = settings.minio_bucket
        
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)
            
    def upload_file(self, object_name: str, file_path: str):
        self.client.fput_object(self.bucket_name, object_name, file_path)
        
    def upload_bytes(self, object_name: str, data: bytes):
        self.client.put_object(
            self.bucket_name, 
            object_name, 
            io.BytesIO(data), 
            length=len(data)
        )
        
    def get_object(self, object_name: str) -> bytes:
        response = None
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            return response.read()
        finally:
            if response:
                response.close()
                response.release_conn()
