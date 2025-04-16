from abc import ABC, abstractmethod
from utils import load_config

class AiClient(ABC):
    """Abstract base class for all ai clients."""

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def generate_content(self, prompt: str) -> str:
        pass