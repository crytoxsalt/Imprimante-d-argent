import re

_SUBS = [
    (r'\bAITA\b',       'Am I the Asshole'),
    (r'\bWIBTA\b',      'Would I be the Asshole'),
    (r'\bNTA\b',        'Not the Asshole'),
    (r'\bYTA\b',        "You're the Asshole"),
    (r'\bESH\b',        'Everyone Sucks Here'),
    (r'\bNAH\b',        'No Assholes Here'),
    (r'\br/AmItheAsshole\b', 'Am I the Asshole'),
    (r'\bOP\b',         'Original Poster'),
    (r'\bSO\b',         'significant other'),
    (r'\bMIL\b',        'mother in law'),
    (r'\bFIL\b',        'father in law'),
    (r'\bSIL\b',        'sister in law'),
    (r'\bBIL\b',        'brother in law'),
    (r'\bDM\b',         'direct message'),
    (r'\bTW\b',         'trigger warning'),
]


def preprocess(text):
    for pattern, replacement in _SUBS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text
