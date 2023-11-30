import os
import cohere
from tenacity import retry, stop_after_attempt, wait_random_exponential


@retry(wait=wait_random_exponential(min=0.5, max=20), stop=stop_after_attempt(6))
def get_cohere_completion(
    prompt: str = "",
    model="command",
    temperature=0.0,
    max_tokens=50,
) -> str:
    """Run a prompt completion with Cohere, retrying with backoff in failure case."""
    try:
        co = cohere.Client(api_key=os.environ["COHERE_API_KEY"])
        response = co.generate(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response.generations[0].text
    except Exception as ex:
        raise ex
