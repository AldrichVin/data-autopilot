from abc import ABC, abstractmethod

import pandas as pd

from models.schemas import CleaningOptions, CleaningReport


class CleaningEngine(ABC):
    @abstractmethod
    def clean(
        self, df: pd.DataFrame, options: CleaningOptions
    ) -> tuple[pd.DataFrame, CleaningReport]:
        ...
