from datetime import timedelta
from io import BytesIO
from uuid import uuid4

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.errors import AppError

ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
ALLOWED_DOCUMENT_TYPES = {"application/pdf": ".pdf"}


class StorageService:
    def __init__(self) -> None:
        self.client = Minio(
            settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=settings.s3_secure,
        )

    def ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(settings.s3_bucket):
                self.client.make_bucket(settings.s3_bucket)
        except S3Error as exc:
            raise AppError("Falha ao preparar armazenamento de arquivos", 500, "storage_error") from exc

    async def upload_image(self, file: UploadFile, prefix: str) -> str:
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise AppError("Tipo de arquivo inválido. Envie JPG, PNG ou WEBP.", 400, "invalid_file_type")

        data = await file.read(settings.max_upload_bytes + 1)
        if len(data) > settings.max_upload_bytes:
            raise AppError("Arquivo maior que o limite permitido.", 413, "file_too_large")
        if len(data) == 0:
            raise AppError("Arquivo vazio.", 400, "empty_file")
        try:
            image = Image.open(BytesIO(data))
            image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise AppError("Arquivo de imagem inválido.", 400, "invalid_image") from exc

        extension = ALLOWED_IMAGE_TYPES[file.content_type]
        object_name = f"{prefix.strip('/')}/{uuid4()}{extension}"
        self.upload_bytes(object_name, data, file.content_type)
        return object_name

    def upload_bytes(self, object_name: str, data: bytes, content_type: str) -> str:
        self.ensure_bucket()
        self.client.put_object(
            settings.s3_bucket,
            object_name,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return object_name

    def presigned_get_url(self, object_name: str, expires_seconds: int | None = None) -> str:
        self.ensure_bucket()
        return self.client.presigned_get_object(
            settings.s3_bucket,
            object_name,
            expires=timedelta(seconds=expires_seconds or settings.s3_presigned_expires_seconds),
        )

    def get_bytes(self, object_name: str) -> bytes:
        self.ensure_bucket()
        response = self.client.get_object(settings.s3_bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()


storage_service = StorageService()
