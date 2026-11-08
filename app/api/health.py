from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Проверка живости")
def health() -> dict[str, str]:
    return {"status": "ok"}
