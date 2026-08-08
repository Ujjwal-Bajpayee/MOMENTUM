from fastapi import APIRouter
from momentum.privacy.manager import privacy_manager

router = APIRouter()


@router.get("/privacy")
def get_privacy_config():
    config = privacy_manager.get_config()
    return config.to_dict()


@router.post("/privacy/pause")
def pause_observation():
    privacy_manager.pause()
    return {"status": "paused"}


@router.post("/privacy/resume")
def resume_observation():
    privacy_manager.resume()
    return {"status": "resumed"}


@router.post("/privacy/exclude/{app_name}")
def exclude_app(app_name: str):
    privacy_manager.exclude_application(app_name)
    return {"excluded": app_name}


@router.delete("/privacy/exclude/{app_name}")
def include_app(app_name: str):
    privacy_manager.include_application(app_name)
    return {"included": app_name}
