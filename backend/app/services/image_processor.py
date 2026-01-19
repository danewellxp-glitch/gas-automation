"""
Módulo para processamento de imagens no sistema de automação de gás.
Inclui funcionalidades para upload, OCR, e análise de imagens.
"""

import os
import uuid
from typing import Optional, Dict, Any
from pathlib import Path
from PIL import Image
import pytesseract
import cv2
import numpy as np
import io
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.minio_client import MinIOClient


class ImageProcessor:
    """Processador de imagens para o sistema de automação de gás"""

    def __init__(self):
        self.minio_client = MinIOClient()
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB

    async def process_uploaded_image(
        self,
        file: UploadFile,
        session: AsyncSession,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Processa uma imagem enviada via upload.

        Args:
            file: Arquivo de imagem enviado
            session: Sessão do banco de dados
            user_id: ID do usuário (opcional)
            metadata: Metadados adicionais (opcional)

        Returns:
            Dict com informações da imagem processada
        """
        # Validar arquivo
        await self._validate_image_file(file)

        # Gerar nome único para o arquivo
        file_extension = Path(file.filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        # Ler conteúdo do arquivo
        file_content = await file.read()

        # Salvar no MinIO
        minio_path = f"images/{unique_filename}"
        await self.minio_client.upload_file(
            file_content=file_content,
            file_path=minio_path,
            content_type=file.content_type
        )

        # Processar imagem
        processing_result = await self._process_image_content(file_content, file.filename)

        # Retornar resultado
        result = {
            "filename": unique_filename,
            "original_filename": file.filename,
            "minio_path": minio_path,
            "file_size": len(file_content),
            "content_type": file.content_type,
            "processing_result": processing_result,
            "metadata": metadata or {}
        }

        return result

    async def _validate_image_file(self, file: UploadFile) -> None:
        """Valida se o arquivo é uma imagem válida"""
        # Verificar extensão
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de arquivo não permitido. Use: {', '.join(self.allowed_extensions)}"
            )

        # Verificar tamanho
        file_content = await file.read()
        if len(file_content) > self.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"Arquivo muito grande. Máximo: {self.max_file_size / (1024*1024)}MB"
            )

        # Resetar ponteiro do arquivo
        await file.seek(0)

        # Tentar abrir como imagem
        try:
            image = Image.open(file.file)
            image.verify()
            await file.seek(0)  # Resetar novamente
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Arquivo de imagem inválido: {str(e)}"
            )

    async def _process_image_content(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Processa o conteúdo da imagem"""
        result = {
            "dimensions": None,
            "format": None,
            "ocr_text": None,
            "has_text": False,
            "quality_score": 0.0
        }

        try:
            # Abrir imagem com PIL
            image = Image.open(io.BytesIO(file_content))

            # Informações básicas
            result["dimensions"] = image.size
            result["format"] = image.format

            # Converter para OpenCV para processamento
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

            # OCR
            try:
                ocr_text = pytesseract.image_to_string(cv_image, lang='por+eng')
                result["ocr_text"] = ocr_text.strip()
                result["has_text"] = len(ocr_text.strip()) > 0
            except Exception as e:
                print(f"Erro no OCR: {e}")
                result["ocr_text"] = None
                result["has_text"] = False

            # Análise de qualidade básica
            result["quality_score"] = self._calculate_image_quality(cv_image)

        except Exception as e:
            print(f"Erro no processamento da imagem: {e}")

        return result

    def _calculate_image_quality(self, cv_image: np.ndarray) -> float:
        """Calcula uma pontuação básica de qualidade da imagem"""
        try:
            # Converter para grayscale
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

            # Calcular variância (medida de nitidez)
            variance = cv2.Laplacian(gray, cv2.CV_64F).var()

            # Normalizar para uma escala de 0-1
            quality_score = min(variance / 500.0, 1.0)

            return round(quality_score, 2)
        except:
            return 0.0

    async def extract_text_from_image(self, image_path_or_url: str) -> Optional[str]:
        """Extrai texto de uma imagem usando OCR"""
        try:
            # Se for URL do MinIO, baixar primeiro
            if image_path_or_url.startswith("http"):
                # TODO: Implementar download da URL
                pass
            else:
                # Caminho local
                image = cv2.imread(image_path_or_url)
                text = pytesseract.image_to_string(image, lang='por+eng')
                return text.strip()
        except Exception as e:
            print(f"Erro na extração de texto: {e}")
            return None

    async def detect_document_type(self, image_content: bytes) -> str:
        """Detecta o tipo de documento na imagem"""
        try:
            image = Image.open(io.BytesIO(image_content))
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

            # OCR para detectar palavras-chave
            text = pytesseract.image_to_string(cv_image, lang='por').lower()

            # Regras básicas de detecção
            if any(word in text for word in ['cpf', 'rg', 'identidade']):
                return "documento_pessoal"
            elif any(word in text for word in ['comprovante', 'pagamento', 'recibo']):
                return "comprovante_pagamento"
            elif any(word in text for word in ['endereco', 'residencia', 'comprovante']):
                return "comprovante_endereco"
            else:
                return "documento_geral"

        except Exception as e:
            print(f"Erro na detecção de tipo: {e}")
            return "desconhecido"


# Instância global
image_processor = ImageProcessor()