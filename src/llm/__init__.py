import logging
from tenacity import retry, wait_random_exponential, stop_after_attempt
from .claude_completion import get_claude_completion
from .gpt_completion import get_gpt_chat_completion, get_gpt_completion
from .palm_completion import get_palm_completion
from .cohere_completion import get_cohere_completion


##############################################
@retry(wait=wait_random_exponential(min=0.5, max=20), stop=stop_after_attempt(5))
def complete(model, prompt, system="", temperature=0.0, max_tokens=750):
    """Perform a completion using the specified model"""

    completion_map = {
        "text-davinci-003": get_gpt_completion,
        "gpt-3.5-turbo-instruct": get_gpt_completion,
        "text-bison@001": get_palm_completion,
        "command": get_cohere_completion,
    }
    chat_map = {
        "claude-instant-1": get_claude_completion,
        "claude-2": get_claude_completion,
        "claude-2.1": get_claude_completion,
        "gpt-3.5-turbo": get_gpt_chat_completion,
        "gpt-3.5-turbo-16k": get_gpt_chat_completion,
        "gpt-3.5-turbo-1106": get_gpt_chat_completion,
        "gpt-4": get_gpt_chat_completion,
        "gpt-4-1106-preview": get_gpt_chat_completion,
    }

    if model in chat_map:
        completion = chat_map[model](
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system=system,
        )
    elif model in completion_map:
        completion = completion_map[model](
            prompt=prompt, model=model, temperature=temperature, max_tokens=max_tokens
        )
    else:
        print(f"Unknown model {model}")
        exit(-1)

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
