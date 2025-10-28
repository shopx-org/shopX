# shipping/cities.py
import json, unicodedata
from django.contrib.staticfiles import finders

def _norm(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s).strip()
    s = s.replace("ي", "ی").replace("ك", "ک").replace("\u200c", "").replace("\xa0", " ")
    s = " ".join(s.split())
    return s

CITIES_BY_PROVINCE, CITIES_NORM = {}, {}

path = finders.find('data/iran_cities.json')
if path:
    with open(path, 'r', encoding='utf-8') as f:
        CITIES_BY_PROVINCE = json.load(f)

for prov, cities in (CITIES_BY_PROVINCE or {}).items():
    p = _norm(prov)
    CITIES_NORM[p] = sorted({_norm(c) for c in cities})