from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from slate_edge.domain import Game, OddsQuote


class ScheduleProvider(ABC):
    @abstractmethod
    def games(self, slate_date: date) -> list[Game]: ...


class OddsProvider(ABC):
    @abstractmethod
    def quotes(self, slate_date: date, games: list[Game]) -> list[OddsQuote]: ...


class ContextProvider(ABC):
    @abstractmethod
    def enrich(self, games: list[Game]) -> list[Game]: ...

