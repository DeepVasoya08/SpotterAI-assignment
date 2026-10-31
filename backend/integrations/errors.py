class ProviderError(Exception):
    """An upstream API failed or returned a response we cannot use."""

    def __init__(self, provider: str, message: str) -> None:
        super().__init__(f"{provider}: {message}")
        self.provider = provider
