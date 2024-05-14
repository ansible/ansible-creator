"""Custom exception classes for ansible-creator."""

from __future__ import annotations


class CreatorError(Exception):
    """Class representing exceptions raised from creator code."""

    def __init__(self: CreatorError, message: str) -> None:
        """Instantiate an object of this class.

        Args:
            message: The exception message.
        """
        super().__init__(message)
        self._message = message

    @property
    def message(self: CreatorError) -> str:
        """Craft and return the CreatorError message.

        Includes the 'cause' when raised from another exception.

        Returns:
            An exception message.
        """
        msg = self._message
        if getattr(self, "__cause__", ""):
            msg += f"\n{self.__cause__!s}"
        return msg

    def __str__(self: CreatorError) -> str:
        """Return a string representation of the exception.

        Returns:
            The exception message as a string.
        """
        return self.message
