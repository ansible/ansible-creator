"""Custom exception classes for ansible-creator."""


class CreatorError(Exception):
    """Class representing exceptions raised from creator code."""

    def __init__(self, message=""):
        """Instantiate an object of this class.

        :params message: The exception message.
        """
        super().__init__(message)
        self._message = message

    @property
    def message(self):
        """Craft and return the CreatorError message
           (including the 'cause' when raised from another exception).

        :returns: An exception message.
        """
        msg = self._message
        if getattr(self, "__cause__", ""):
            msg += f"\n{str(self.__cause__)}"
        return msg

    def __str__(self):
        return self.message
