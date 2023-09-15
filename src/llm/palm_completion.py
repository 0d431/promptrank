import vertexai.preview.language_models
from tenacity import retry, wait_random_exponential, stop_after_attempt


# global model for bison
_client = vertexai.preview.language_models.TextGenerationModel.from_pretrained('text-bison@001')


@retry(wait=wait_random_exponential(min=0.5, max=20), stop=stop_after_attempt(6))
def get_palm_completion(
    prompt: str = "", model="text-bison@001", temperature=0.0, max_tokens=50
) -> str:
    """Run a prompt completion with PaLM, retrying with backoff in failure case."""
    try:
        assert model == "text-bison@001", "Must select text-bison@001"

        response = _client.predict(
            prompt, max_output_tokens=max_tokens, temperature=temperature
        )

        return response.text
    except Exception as ex:
        raise ex
