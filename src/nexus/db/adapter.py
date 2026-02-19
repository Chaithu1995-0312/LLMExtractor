from abc import ABC, abstractmethod
from contextlib import contextmanager


class DBAdapter(ABC):

    @abstractmethod
    def execute(self, query: str, params: tuple = None):
        pass

    @abstractmethod
    def fetch_one(self, query: str, params: tuple = None):
        pass

    @abstractmethod
    def fetch_all(self, query: str, params: tuple = None):
        pass

    @abstractmethod
    @contextmanager
    def transaction(self):
        pass
