"""
API para processamento de imagens.
Permite upload, OCR e análise de imagens.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.image_processor import image_processor
from app.auth import get_current_user
from app.models.auth_models import User

router = APIRouter()

@router.post("/upload", response_model=Dict[str, Any])
async def upload_image(
    file: UploadFile = File(...),
    description: Optional[str] = None,
    document_type: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Faz upload e processa uma imagem.

    - **file**: Arquivo de imagem (JPG, PNG, etc.)
    - **description**: Descrição opcional da imagem
    - **document_type**: Tipo de documento (opcional)
    """
    try:
        metadata = {
            "user_id": current_user.id,
            "description": description,
            "document_type": document_type,
            "uploaded_by": current_user.username
        }

        result = await image_processor.process_uploaded_image(
            file=file,
            session=session,
            user_id=current_user.id,
            metadata=metadata
        )

        return {
            "success": True,
            "message": "Imagem processada com sucesso",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro no processamento da imagem: {str(e)}"
        )

@router.post("/ocr", response_model=Dict[str, Any])
async def extract_text_from_image(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Extrai texto de uma imagem usando OCR.

    - **file**: Arquivo de imagem contendo texto
    """
    try:
        # Processar imagem
        result = await image_processor.process_uploaded_image(
            file=file,
            session=session,
            user_id=current_user.id
        )

        # Retornar apenas o texto extraído
        ocr_text = result.get("processing_result", {}).get("ocr_text")

        return {
            "success": True,
            "text": ocr_text,
            "has_text": result.get("processing_result", {}).get("has_text", False),
            "confidence": result.get("processing_result", {}).get("quality_score", 0.0)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na extração de texto: {str(e)}"
        )

@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_image(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analisa uma imagem e retorna informações detalhadas.

    - **file**: Arquivo de imagem para análise
    """
    try:
        result = await image_processor.process_uploaded_image(
            file=file,
            session=session,
            user_id=current_user.id
        )

        return {
            "success": True,
            "analysis": {
                "dimensions": result.get("processing_result", {}).get("dimensions"),
                "format": result.get("processing_result", {}).get("format"),
                "has_text": result.get("processing_result", {}).get("has_text"),
                "quality_score": result.get("processing_result", {}).get("quality_score"),
                "detected_type": await image_processor.detect_document_type(await file.read()),
                "file_size": result.get("file_size"),
                "filename": result.get("original_filename")
            },
            "extracted_text": result.get("processing_result", {}).get("ocr_text")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na análise da imagem: {str(e)}"
        )

@router.get("/info")
async def get_image_processing_info():
    """
    Retorna informações sobre os recursos de processamento de imagem disponíveis.
    """
    return {
        "supported_formats": ["jpg", "jpeg", "png", "bmp", "tiff"],
        "max_file_size": "10MB",
        "features": {
            "ocr": True,
            "document_detection": True,
            "quality_analysis": True,
            "storage": True
        },
        "ocr_languages": ["portuguese", "english"]
    }