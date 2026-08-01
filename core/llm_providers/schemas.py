class LLMResponse(str):
    """A string subclass that behaves exactly like a standard text string.

    Also contains token usage metadata as attributes.
    """
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    provider_name: str

    def __new__(cls, content, prompt_tokens=0, completion_tokens=0, total_tokens=0, provider_name=""):
        """Create new."""
        obj = str.__new__(cls, content)
        obj.prompt_tokens = prompt_tokens
        obj.completion_tokens = completion_tokens
        obj.total_tokens = total_tokens
        obj.provider_name = provider_name
        return obj
