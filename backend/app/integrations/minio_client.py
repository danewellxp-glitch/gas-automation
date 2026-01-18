"""
Cliente MinIO para armazenamento de arquivos.
Suporta upload/download de comprovantes, fotos e documentos.
"""

import io
import logging
from datetime import timedelta
from typing import BinaryIO, Optional
from urllib.parse import urlparse

from app.config import settings

logger = logging.getLogger(__name__)

# MinIO SDK é opcional - verificar se está instalado
try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    logger.warning("MinIO SDK não instalado. Funcionalidades de storage desabilitadas.")


class MinIOClient:
    """
    Cliente para integração com MinIO (Object Storage compatível com S3).

    Buckets padrão:
    - payment-receipts: Comprovantes de pagamento
    - customer-photos: Fotos de clientes/entregas
    - documents: Documentos gerais
    """

    DEFAULT_BUCKETS = [
        "payment-receipts",
        "customer-photos",
        "documents",
        "exports",  # Relatórios exportados
    ]

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: bool = False,
    ):
        if not MINIO_AVAILABLE:
            self._client = None
            return

        self.endpoint = endpoint or settings.minio_endpoint
        self.access_key = access_key or settings.minio_access_key
        self.secret_key = secret_key or settings.minio_secret_key
        self.secure = secure

        if not self.endpoint:
            logger.warning("MinIO endpoint não configurado")
            self._client = None
            return

        try:
            self._client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
            logger.info(f"MinIO client conectado: {self.endpoint}")
        except Exception as e:
            logger.error(f"Erro ao conectar MinIO: {e}")
            self._client = None

    @property
    def is_available(self) -> bool:
        """Verifica se o cliente está disponível."""
        return self._client is not None

    def ensure_buckets(self) -> None:
        """Cria buckets padrão se não existirem."""
        if not self.is_available:
            return

        for bucket in self.DEFAULT_BUCKETS:
            try:
                if not self._client.bucket_exists(bucket):
                    self._client.make_bucket(bucket)
                    logger.info(f"Bucket criado: {bucket}")
            except S3Error as e:
                logger.error(f"Erro ao criar bucket {bucket}: {e}")

    def upload_file(
        self,
        bucket: str,
        object_name: str,
        file_data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        """
        Faz upload de um arquivo.

        Args:
            bucket: Nome do bucket
            object_name: Nome/path do objeto no bucket
            file_data: Dados do arquivo em bytes
            content_type: MIME type do arquivo
            metadata: Metadados adicionais

        Returns:
            URL do objeto ou None se falhar
        """
        if not self.is_available:
            logger.warning("MinIO não disponível para upload")
            return None

        try:
            # Garantir que o bucket existe
            if not self._client.bucket_exists(bucket):
                self._client.make_bucket(bucket)

            # Fazer upload
            self._client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=io.BytesIO(file_data),
                length=len(file_data),
                content_type=content_type,
                metadata=metadata,
            )

            logger.info(f"Arquivo enviado: {bucket}/{object_name}")
            return f"{bucket}/{object_name}"

        except S3Error as e:
            logger.error(f"Erro no upload MinIO: {e}")
            return None

    def upload_stream(
        self,
        bucket: str,
        object_name: str,
        file_stream: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> Optional[str]:
        """Faz upload de um stream de arquivo."""
        if not self.is_available:
            return None

        try:
            if not self._client.bucket_exists(bucket):
                self._client.make_bucket(bucket)

            self._client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=file_stream,
                length=length,
                content_type=content_type,
            )

            return f"{bucket}/{object_name}"

        except S3Error as e:
            logger.error(f"Erro no upload stream MinIO: {e}")
            return None

    def download_file(
        self,
        bucket: str,
        object_name: str,
    ) -> Optional[bytes]:
        """
        Baixa um arquivo do MinIO.

        Returns:
            Conteúdo do arquivo em bytes ou None
        """
        if not self.is_available:
            return None

        try:
            response = self._client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data

        except S3Error as e:
            logger.error(f"Erro no download MinIO: {e}")
            return None

    def get_presigned_url(
        self,
        bucket: str,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
    ) -> Optional[str]:
        """
        Gera URL temporária para acesso ao arquivo.

        Args:
            bucket: Nome do bucket
            object_name: Nome do objeto
            expires: Tempo de expiração da URL

        Returns:
            URL pré-assinada ou None
        """
        if not self.is_available:
            return None

        try:
            url = self._client.presigned_get_object(
                bucket_name=bucket,
                object_name=object_name,
                expires=expires,
            )
            return url

        except S3Error as e:
            logger.error(f"Erro ao gerar URL MinIO: {e}")
            return None

    def get_upload_url(
        self,
        bucket: str,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
    ) -> Optional[str]:
        """
        Gera URL temporária para upload direto.

        Returns:
            URL pré-assinada para PUT ou None
        """
        if not self.is_available:
            return None

        try:
            url = self._client.presigned_put_object(
                bucket_name=bucket,
                object_name=object_name,
                expires=expires,
            )
            return url

        except S3Error as e:
            logger.error(f"Erro ao gerar URL de upload MinIO: {e}")
            return None

    def delete_file(
        self,
        bucket: str,
        object_name: str,
    ) -> bool:
        """Remove um arquivo do MinIO."""
        if not self.is_available:
            return False

        try:
            self._client.remove_object(bucket, object_name)
            logger.info(f"Arquivo removido: {bucket}/{object_name}")
            return True

        except S3Error as e:
            logger.error(f"Erro ao remover arquivo MinIO: {e}")
            return False

    def list_files(
        self,
        bucket: str,
        prefix: str = "",
        recursive: bool = True,
    ) -> list[str]:
        """
        Lista arquivos em um bucket.

        Args:
            bucket: Nome do bucket
            prefix: Prefixo para filtrar (ex: "orders/2024/")
            recursive: Listar recursivamente

        Returns:
            Lista de nomes de objetos
        """
        if not self.is_available:
            return []

        try:
            objects = self._client.list_objects(
                bucket_name=bucket,
                prefix=prefix,
                recursive=recursive,
            )
            return [obj.object_name for obj in objects]

        except S3Error as e:
            logger.error(f"Erro ao listar arquivos MinIO: {e}")
            return []

    def file_exists(
        self,
        bucket: str,
        object_name: str,
    ) -> bool:
        """Verifica se um arquivo existe."""
        if not self.is_available:
            return False

        try:
            self._client.stat_object(bucket, object_name)
            return True
        except S3Error:
            return False


# Instância global
minio_client = MinIOClient()


# Funções de conveniência
async def upload_payment_receipt(
    order_id: str,
    file_data: bytes,
    filename: str,
    content_type: str = "image/png",
) -> Optional[str]:
    """
    Faz upload de comprovante de pagamento.

    Returns:
        URL pré-assinada do arquivo ou None
    """
    object_name = f"orders/{order_id}/{filename}"
    result = minio_client.upload_file(
        bucket="payment-receipts",
        object_name=object_name,
        file_data=file_data,
        content_type=content_type,
        metadata={"order_id": order_id},
    )

    if result:
        return minio_client.get_presigned_url(
            bucket="payment-receipts",
            object_name=object_name,
        )
    return None


async def upload_delivery_photo(
    delivery_id: str,
    file_data: bytes,
    photo_type: str = "proof",  # proof, signature, damage
) -> Optional[str]:
    """
    Faz upload de foto de entrega.

    Returns:
        URL pré-assinada do arquivo ou None
    """
    import uuid
    from datetime import datetime

    filename = f"{photo_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
    object_name = f"deliveries/{delivery_id}/{filename}"

    result = minio_client.upload_file(
        bucket="customer-photos",
        object_name=object_name,
        file_data=file_data,
        content_type="image/jpeg",
        metadata={"delivery_id": delivery_id, "photo_type": photo_type},
    )

    if result:
        return minio_client.get_presigned_url(
            bucket="customer-photos",
            object_name=object_name,
        )
    return None


async def get_file_url(
    bucket: str,
    object_name: str,
    expires_hours: int = 1,
) -> Optional[str]:
    """Gera URL temporária para um arquivo."""
    return minio_client.get_presigned_url(
        bucket=bucket,
        object_name=object_name,
        expires=timedelta(hours=expires_hours),
    )
