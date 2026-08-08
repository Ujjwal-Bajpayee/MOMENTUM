from fastapi import APIRouter
from momentum.learning.trainer import run_learning_from_history
from momentum.learning.bandit import get_bandit

router = APIRouter()


@router.post("/learning/run")
def trigger_learning():
    result = run_learning_from_history()
    return result


@router.get("/learning/status")
def learning_status():
    bandit = get_bandit()
    return bandit.get_stats()
