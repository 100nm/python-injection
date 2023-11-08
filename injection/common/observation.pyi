from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

_T = TypeVar("_T")

class Observer(Generic[_T], ABC):
    """
    Object that can subscribe to an observable.
    """

    @abstractmethod
    def notify(self, obj: _T, /):
        """
        Method called when the observer is subscribed to one or more observables and one of them notifies a change.

        :param obj: Data shared from the observable.
        """

class Observable(Observer[_T], ABC):
    """
    Object for managing and notifying subscribers.
    """

    @abstractmethod
    def notify(self, obj: _T | None = ..., /):
        """
        Method called to notify subscribers. It can be called by itself or by another observable.

        :param obj: Leave the default value if the method is called by itself. It is shared data if it is called from
        another observable.
        """
    @abstractmethod
    def subscribe(self, observer: Observer):
        """
        Method for subscribing an observer.
        """
    @abstractmethod
    def unsubscribe(self, observer: Observer):
        """
        Method for unsubscribing an observer. Shouldn't raise exception if observer isn't subscriber.
        """

@dataclass
class Observation:
    """
    Temporary object used to manage an observation. If this object is destroyed, it automatically unsubscribes the
    observer.
    """

    observer: Observer
    observable: Observable

    def keep(self):
        """
        Method which does nothing. Its call just ensures that the object is referenced to avoid deletion.
        """
    def subscribe(self):
        """
        Method for subscribing the observer.
        """
    def unsubscribe(self):
        """
        Method for unsubscribing the observer.
        """
