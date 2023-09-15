import os
from tenacity import retry, wait_random_exponential, stop_after_attempt
import anthropic

@retry(wait=wait_random_exponential(min=0.5, max=20), stop=stop_after_attempt(6))
def get_claude_completion(
    prompt: str = "",
    model="claude-instant-1",
    temperature=0.0,
    max_tokens=50,
    stop=anthropic.HUMAN_PROMPT,
) -> str:
    """Run a prompt completion with Claude, retrying with backoff in failure case."""
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.completions.create(
            prompt=prompt,
            stop_sequences=[stop],
            model=model,
            max_tokens_to_sample=max_tokens,
            temperature=temperature,
        )

        return response.completion
    except Exception as ex:
        raise ex


def get_simple_claude_completion(
    prompt: str = "",
    model="claude-instant-1",
    temperature=0.0,
    max_tokens=50,
    stop=anthropic.HUMAN_PROMPT,
) -> str:
    """Run a prompt completion with Claude with default prompt adornment, retrying with backoff in failure case."""
    response = get_claude_completion(
        f"{anthropic.HUMAN_PROMPT}{prompt}{anthropic.AI_PROMPT}",
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stop=stop,
    )

    return response
