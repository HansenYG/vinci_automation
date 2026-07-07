from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Liveness probe to confirm the API is running."""
    return {"status": "ok"}
