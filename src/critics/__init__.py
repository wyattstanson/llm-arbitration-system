from src.critics.accuracy_critic import AccuracyCritic
from src.critics.completeness_critic import CompletenessCritic
from src.critics.logic_critic import LogicCritic

__all__ = ["AccuracyCritic", "LogicCritic", "CompletenessCritic"]


def all_critics():
    """Instantiate all three critics in dimension order."""
    return [AccuracyCritic(), LogicCritic(), CompletenessCritic()]
