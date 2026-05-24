import re

def clean_text(raw_text: str) -> str:
    if not raw_text:
        return ""


    text = raw_text.lower()


    text = re.sub(r'http\S+\s*', ' ', text)
    text = re.sub(r'\S*@\S*\s?', ' ', text)


    text = re.sub(r'[^\w\s]', ' ', text)

    text = re.sub(r'\s+', ' ', text).strip()

    return text