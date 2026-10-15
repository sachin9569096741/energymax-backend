from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.services.auth_service import (
    AffiliateAuthService,
)

_bearer = HTTPBearer(auto_error=False)


def get_current_affiliate(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Affiliate:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Affiliate authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return AffiliateAuthService(db).authenticate_session(
            credentials.credentials
        )
    except HTTPException:
        db.rollback()
        raise