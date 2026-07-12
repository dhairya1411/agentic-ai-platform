from fastapi import APIRouter

router = APIRouter(tags=["workspace"])


@router.get("/projects")
async def projects() -> list[dict[str, object]]:
    return []


@router.get("/approvals")
async def approvals() -> list[dict[str, object]]:
    return []


@router.get("/activity")
async def activity() -> list[dict[str, object]]:
    return []


@router.get("/memories")
async def memories() -> list[dict[str, object]]:
    return []
