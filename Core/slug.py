from django.utils.text import slugify

def slug_en(value: str, fallback="item", max_length=160) -> str:
    s = slugify(value, allow_unicode=False)
    return (s or fallback)[:max_length]

def slug_fa(value: str, fallback="item", max_length=160) -> str:
    s = slugify(value, allow_unicode=True)
    return (s or fallback)[:max_length]
