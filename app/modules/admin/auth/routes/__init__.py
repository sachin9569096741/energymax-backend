from fastapi import APIRouter


router = APIRouter(
    prefix="/admin/auth",
    tags=["Admin Authentication"],
)