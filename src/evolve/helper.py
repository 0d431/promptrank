import random
import string
import textwrap
from ruamel.yaml.scalarstring import LiteralScalarString

#################################################
def generate_random_id(length=3):
    return "".join(
        [random.choice(string.ascii_lowercase) for _ in range(length)]
    ).upper()



def LS(s):
    """Helper function for YAML writing"""
    return LiteralScalarString(textwrap.dedent(s))


#################################################
def ensure_single_placeholder_occurrence(text, placeholder):
    text = text.replace(f"{placeholder}", "---fofofox---", 1)
    text = text.replace(f"{placeholder}", "text")
    return text.replace("---fofofox---", f"{placeholder}")


EVOLUTION_MODEL = "gpt-4-1106-preview"