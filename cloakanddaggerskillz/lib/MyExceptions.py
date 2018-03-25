"""
This file holds all of the special exceptions raised by the game
"""


class OrderException(Exception):
    """
    This exception is raised when an order from a player is invalid for any reason
    """
    def __init__(self, message, order, *args, **kwargs):
        """
        :param message: The exception message
        :type message: str
        :param order: The invalid order
        :type order: dict[str, any]
        :param args: any args relevant to the exception
        :type args: any
        :param kwargs: keyword args for the exception
        :type kwargs: any
        """
        self.order = order
        super(OrderException, self).__init__(message, args, kwargs)


class InvalidOrderFormatException(OrderException):
    """
    This exception is raised when an order from the engine is in a bad format
    This kind of orders kills the player if the strict flag is True, otherwise it is simply ignored.
    """
    pass


class InvalidOrderException(OrderException):
    """
    This exception is raised when an order from a player is invalid.
    An invalid order is completely invalid and shouldn't be able to be sent unless
    there is a bug in the runner, or the player's bot is malicious and took control over
    the runner.
    This kind of orders kills the player if the strict flag is True, otherwise it is simply ignored.
    """
    pass


class IgnoredOrderException(OrderException):
    """
    This exception is raised when an order from a player should be ignored.
     An ignored order represents an order that is impossible according for game rules:
     attacking too far, moving too many steps and so on.
     This kind of orders are simply ignored.
    """
    pass


class PirateAlreadyActedException(OrderException):
    """
    This exception is raised when a player sends more than one order for the same pirate
    during the same turn.
    The orders are classified as ignored orders
    This kind of orders are simply ignored.
    """
    def __init__(self, message, order, pirate_id, *args, **kwargs):
        """
        :param message: The exception message
        :type message: str
        :param order: The invalid order
        :type order: dict[str, any]
        :param pirate_id: the id of the player given more than one order
        :type pirate_id: int
        :param args: any args relevant to the exception
        :type args: any
        :param kwargs: keyword args for the exception
        :type kwargs: any
        """
        self.pirate_id = pirate_id
        super(PirateAlreadyActedException, self).__init__(message, order, args, kwargs)


class StepLimitExceededException(OrderException):
    """
    This exception is raised when a player sends orders that would use more moves than allowed in a turn.
    The orders are classified as invalid orders
    This kind of orders kills the player if the strict flag is True, otherwise it is simply ignored.
    """
    pass
