import uuid
from urllib.parse import ParseResult, urljoin


def gen_filename():
    return str(uuid.uuid4())


def normalize_link(url: str, base: ParseResult) -> str:
    return urljoin(base.geturl(), url)
