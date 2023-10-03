import logging
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
        "gpt-3.5-turbo-16k": get_gpt_chat_completion,
        "gpt-4": get_gpt_chat_completion,
        "text-davinci-003": get_gpt_completion,
        "gpt-3.5-turbo-instruct": get_gpt_completion,
        "text-bison@001": get_palm_completion,
    }
    chat_models = ["gpt-3.5-turbo", "gpt-4"]

    completer = model_map.get(model, None)
    if model is None:
        print(f"Unknown model {model}")
        exit(-1)

    if model in chat_models:
        completion = completer(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=750,
            system=system,
        )
    else:
        completion = completer(
            prompt=prompt, model=model, temperature=temperature, max_tokens=500
        )

    # log
    logging.info(
        "=====%s @ %s=====\n%s\n-----\n%s\n>>>>>\n%s",
        model,
        temperature,
        system,
        prompt,
        completion,
    )

    return completion
