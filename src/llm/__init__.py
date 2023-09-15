from .claude_completion import get_simple_claude_completion
from .gpt_completion import get_gpt_chat_completion, get_gpt_completion
from .palm_completion import get_palm_completion


##############################################
def complete(model, temperature, prompt, system=""):
    """Perform a completion using the specified model"""

    model_map = {
        "claude-instant-1": get_simple_claude_completion,
        "claude-2": get_simple_claude_completion,
        "gpt-3.5-turbo": get_gpt_chat_completion,
        "gpt-4": get_gpt_chat_completion,
        "text-davinci-003": get_gpt_completion,
        "text-bison@001": get_palm_completion,
    }
    chat_models = ["gpt-3.5-turbo", "gpt-4"]

    completer = model_map.get(model, None)
    if model is None:
        print(f"Unknown model {model}")
        exit(-1)

    if model in chat_models:
        return completer(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=500,
            system=system,
        )
    else:
        return completer(
            prompt=prompt, model=model, temperature=temperature, max_tokens=500
        )
