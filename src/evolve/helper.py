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
