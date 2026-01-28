"""
API de Exportação de Pedidos para Arquivos.

Endpoints para exportar pedidos em CSV, XML ou formato Gasmaster.
Alternativa para cenários onde o Firebird é somente leitura.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

from app.auth import get_current_user
from app.models.auth_models import User
from app.services.file_export_service import (
    ExportFormat,
    file_export_service,
    export_order_to_file,
    export_delivered_orders_to_file,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Schemas ====================

class ExportResponse(BaseModel):
    """Resposta de exportação."""
    success: bool
    filename: str
    format: str
    orders_count: int
    message: str


class ExportedFileInfo(BaseModel):
    """Info de arquivo exportado."""
    name: str
    path: str
    format: str
    size: int
    created_at: str


# ==================== Endpoints ====================

@router.get("/formats")
async def list_export_formats():
    """Lista formatos de exportação disponíveis."""
    return {
        "formats": [
            {
                "id": "csv",
                "name": "CSV (Excel)",
                "description": "Arquivo separado por ponto-e-vírgula, compatível com Excel",
                "extension": ".csv",
            },
            {
                "id": "xml",
                "name": "XML",
                "description": "Formato XML estruturado para importação em ERPs",
                "extension": ".xml",
            },
            {
                "id": "gasmaster_txt",
                "name": "Gasmaster TXT",
                "description": "Formato posicional específico para sistema Gasmaster",
                "extension": ".txt",
            },
        ]
    }


@router.get("/files", response_model=list[ExportedFileInfo])
async def list_exported_files(
    format: Optional[str] = Query(None, description="Filtrar por formato (csv, xml, gasmaster_txt)"),
    limit: int = Query(50, ge=1, le=200, description="Limite de arquivos"),
    current_user: User = Depends(get_current_user),
):
    """Lista arquivos já exportados."""
    export_format = None
    if format:
        try:
            export_format = ExportFormat(format)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Formato inválido: {format}")

    files = file_export_service.list_exported_files(format=export_format, limit=limit)
    return files


@router.get("/order/{order_id}")
async def export_single_order(
    order_id: UUID,
    format: str = Query("csv", description="Formato: csv, xml, gasmaster_txt"),
    download: bool = Query(True, description="Se True, retorna arquivo para download"),
    current_user: User = Depends(get_current_user),
):
    """
    Exporta um único pedido.

    Retorna o arquivo no formato especificado.
    """
    try:
        export_format = ExportFormat(format)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Formato inválido: {format}")

    try:
        content, filename = await export_order_to_file(order_id, export_format)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Erro ao exportar pedido {order_id}")
        raise HTTPException(status_code=500, detail=f"Erro ao exportar: {str(e)}")

    if download:
        # Retornar arquivo para download
        content_type = _get_content_type(export_format)
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Filename": filename,
            },
        )
    else:
        # Retornar JSON com conteúdo
        return {
            "success": True,
            "filename": filename,
            "format": format,
            "content": content,
        }


@router.post("/batch")
async def export_orders_batch(
    format: str = Query("csv", description="Formato: csv, xml, gasmaster_txt"),
    status: Optional[str] = Query(None, description="Filtrar por status (ex: delivered)"),
    date_from: Optional[datetime] = Query(None, description="Data inicial (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Data final (ISO format)"),
    exclude_exported: bool = Query(True, description="Excluir pedidos já exportados"),
    save_file: bool = Query(True, description="Salvar arquivo no servidor"),
    mark_exported: bool = Query(True, description="Marcar pedidos como exportados"),
    download: bool = Query(True, description="Retornar arquivo para download"),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Exporta lote de pedidos.

    Filtra por status, data e outros critérios.
    Pode salvar no servidor e/ou retornar para download.
    """
    try:
        export_format = ExportFormat(format)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Formato inválido: {format}")

    try:
        content, filename, count = await file_export_service.export_orders_batch(
            format=export_format,
            status=status,
            date_from=date_from,
            date_to=date_to,
            exclude_exported=exclude_exported,
            save_to_file=save_file,
            mark_as_exported=mark_exported,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Erro ao exportar pedidos em lote")
        raise HTTPException(status_code=500, detail=f"Erro ao exportar: {str(e)}")

    if download:
        content_type = _get_content_type(export_format)
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Filename": filename,
                "X-Orders-Count": str(count),
            },
        )
    else:
        return JSONResponse({
            "success": True,
            "filename": filename,
            "format": format,
            "orders_count": count,
            "message": f"{count} pedidos exportados com sucesso",
            "saved_to_server": save_file,
            "marked_as_exported": mark_exported,
        })


@router.post("/delivered")
async def export_delivered_orders(
    format: str = Query("csv", description="Formato: csv, xml, gasmaster_txt"),
    date_from: Optional[datetime] = Query(None, description="Data inicial"),
    date_to: Optional[datetime] = Query(None, description="Data final"),
    download: bool = Query(True, description="Retornar arquivo para download"),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Atalho para exportar apenas pedidos entregues (delivered).

    Útil para exportação diária de vendas finalizadas.
    """
    try:
        export_format = ExportFormat(format)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Formato inválido: {format}")

    try:
        content, filename, count = await export_delivered_orders_to_file(
            format=export_format,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Erro ao exportar pedidos entregues")
        raise HTTPException(status_code=500, detail=f"Erro ao exportar: {str(e)}")

    if download:
        content_type = _get_content_type(export_format)
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Filename": filename,
                "X-Orders-Count": str(count),
            },
        )
    else:
        return JSONResponse({
            "success": True,
            "filename": filename,
            "format": format,
            "orders_count": count,
            "message": f"{count} pedidos entregues exportados",
        })


@router.get("/preview/{order_id}")
async def preview_export(
    order_id: UUID,
    format: str = Query("csv", description="Formato: csv, xml, gasmaster_txt"),
    current_user: User = Depends(get_current_user),
):
    """
    Preview da exportação de um pedido.

    Retorna os dados formatados sem fazer download.
    """
    try:
        export_format = ExportFormat(format)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Formato inválido: {format}")

    try:
        content, filename = await export_order_to_file(order_id, export_format)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Limitar preview para evitar respostas muito grandes
    preview_content = content[:5000]
    truncated = len(content) > 5000

    return {
        "filename": filename,
        "format": format,
        "content_preview": preview_content,
        "truncated": truncated,
        "full_size": len(content),
    }


# ==================== Helpers ====================

def _get_content_type(format: ExportFormat) -> str:
    """Retorna content-type apropriado para o formato."""
    if format == ExportFormat.CSV:
        return "text/csv; charset=utf-8"
    elif format == ExportFormat.XML:
        return "application/xml; charset=utf-8"
    else:
        return "text/plain; charset=utf-8"
