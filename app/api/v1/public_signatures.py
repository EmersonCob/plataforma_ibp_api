from fastapi import APIRouter, Depends, File, Request, UploadFile
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.rate_limit import public_rate_limit
from app.db.session import get_db
from app.schemas.signature import PublicContractRead, PublicSignRequest, PublicSignatureStatus, SignatureRead, UploadPhotoResponse
from app.services.redis import get_redis
from app.services.signatures import signature_service

router = APIRouter(prefix="/public/contracts", tags=["Public Signatures"], dependencies=[Depends(public_rate_limit)])


@router.get("/{token}", response_model=PublicContractRead)
def get_public_contract(token: str, db: Session = Depends(get_db)) -> PublicContractRead:
    contract = signature_service.get_contract_by_token(db, token, mark_viewed=True)
    return PublicContractRead(
        id=contract.id,
        title=contract.title,
        content=contract.content,
        status=contract.status,
        client_name=contract.client.full_name,
        link_expires_at=contract.link_expires_at,
        signed_at=contract.signed_at,
    )


@router.post("/{token}/upload-photo", response_model=UploadPhotoResponse)
async def upload_photo(
    token: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> UploadPhotoResponse:
    path, url = await signature_service.upload_photo(db, redis, token, file)
    return UploadPhotoResponse(face_photo_path=path, face_photo_url=url)


@router.post("/{token}/sign", response_model=SignatureRead)
async def sign_contract(
    token: str,
    payload: PublicSignRequest,
    request: Request,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> SignatureRead:
    return await signature_service.sign(db, redis, token, payload, request)


@router.get("/{token}/status", response_model=PublicSignatureStatus)
def signature_status(token: str, db: Session = Depends(get_db)) -> dict:
    return signature_service.status(db, token)

