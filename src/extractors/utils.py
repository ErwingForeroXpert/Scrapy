
import re

def extract_meters_and_kilometers(text: str, reg_extractor: str = r"(\d{1,3}.*\m)") -> str:

    results = re.findall(reg_extractor, text)

    return results[0]