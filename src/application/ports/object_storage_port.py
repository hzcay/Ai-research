from typing import Protocol

class ObjectStoragePort(Protocol):
    def upload_file(self, object_name: str, file_path: str) -> None:
        ...

    def upload_bytes(self, object_name: str, data: bytes) -> None:
        ...

    def get_object(self, object_name: str) -> bytes:
        ...
