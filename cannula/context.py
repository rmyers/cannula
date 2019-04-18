import typing


class Context:
    """Default Context Base

    Subclasses should implement a handle_request method to provide any
    extra functionality they need.
    """
    def __init__(self, request: typing.Any):
        self.request = self.handle_request(request)

    def handle_request(self, request: typing.Any) -> typing.Any:
        return request
