import os
import re
from tqdm import tqdm
from functools import lru_cache

"""
Uploading two lists of Russian words:
list `yo_sure` - words where <Ё> letter is 100% certain;
list `yo_unsure` - words with uncertianty about <Ё> letters.
"""

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
YO_SURE_PATH = os.path.join(SCRIPT_DIR, 'yobase/yo_sure.txt')
YO_UNSURE_PATH = os.path.join(SCRIPT_DIR, 'yobase/yo_unsure.txt')
YO_SURE_COLLOCATIONS_PATH = os.path.join(SCRIPT_DIR, 'yobase/yo_sure_collocations.txt')
YE_SURE_PATH = os.path.join(SCRIPT_DIR, 'yobase/ye_sure.txt')
YE_SURE_FIRST_WORDS_PATH = os.path.join(SCRIPT_DIR, 'yobase/ye_sure_first_words.txt')
YO_SURE_COMPOUND_PATH = os.path.join(SCRIPT_DIR, 'yobase/yo_sure_compound.txt')
SENTENCE_ENDS = '.,!?;–—…'
AFTER_WORD = SENTENCE_ENDS + ' '

# Precompiled static regex patterns
RE_WORD_BOUNDARY = re.compile(r'\b\w+\b')
RE_ESCAPE_E_LOWER = re.compile(r'<е>')
RE_ESCAPE_E_UPPER = re.compile(r'<Е>')

assert os.path.isfile(YO_SURE_PATH), \
    f'\nFile with words always spelled with the <Ё> letter not found!' + \
    f'\nФайл со словами, которые всегда пишутся с буквой <Ё>, не найден!\n\033[1m{YO_SURE_PATH}\033[0m'
assert os.path.isfile(YO_UNSURE_PATH), \
    f'\nFile with words not always spelled with the <Ё> letter not found!' + \
    f'\nФайл со словами, которые не всегда пишутся с буквой <Ё>, не найден!\n\033[1m{YO_UNSURE_PATH}\033[0m'

# Load all dictionaries once at module initialization
with open(YO_SURE_PATH, 'r', encoding='UTF-8') as file:
    yo_sure = {word.replace('ё', 'е').replace('Ё', 'Е'): word for word in file.read().split()}
with open(YO_UNSURE_PATH, 'r', encoding='UTF-8') as file:
    yo_unsure = {word.replace('ё', 'е').replace('Ё', 'Е'): word for word in file.read().split()}

# Load additional dictionaries once
yo_sure_compound = {}
if os.path.isfile(YO_SURE_COMPOUND_PATH):
    with open(YO_SURE_COMPOUND_PATH, 'r', encoding='utf-8') as file:
        for line in file:
            word = line.strip()
            yo_sure_compound[word.replace('ё', 'е').replace('Ё', 'Е')] = word

yo_sure_collocations = {}
if os.path.isfile(YO_SURE_COLLOCATIONS_PATH):
    with open(YO_SURE_COLLOCATIONS_PATH, 'r', encoding='utf-8') as file:
        for line in file:
            word = line.strip()
            yo_sure_collocations[word.replace('ё', 'е').replace('Ё', 'Е')] = word

ye_sure = {}
if os.path.isfile(YE_SURE_PATH):
    with open(YE_SURE_PATH, 'r', encoding='utf-8') as file:
        for line in file:
            word = line.strip()
            ye_sure[word.replace('<', '').replace('>', '')] = word

ye_sure_first_words = {}
if os.path.isfile(YE_SURE_FIRST_WORDS_PATH):
    with open(YE_SURE_FIRST_WORDS_PATH, 'r', encoding='utf-8') as file:
        for line in file:
            word = line.strip()
            ye_sure_first_words[word.replace('<', '').replace('>', '')] = word


@lru_cache(maxsize=512)
def _compile_regex(pattern: str) -> re.Pattern:
    """Cache compiled regex patterns for dynamic patterns."""
    return re.compile(pattern)


def replace_by_regex(text: str, regex: str, old: str, new: str) -> str:
    """
    Replace old substring to new one inside the hits found by regular expression.
    
    str `regex` - string with regular expression for searching hits by re.findall;
    str `old` - string to be replace inside the hits found by regex;
    str `new` - target replacement;
    return: str - text with replacements in the hits.
    """
    compiled_regex = _compile_regex(regex)
    for hit in set(compiled_regex.findall(text)):
        hit_replace = hit.replace(old, new)
        text = text.replace(hit, hit_replace)
    return text


def get_words_with_ye(text: str) -> str:
    """
    Get all words of the text containing the Russian <е> letters.

    str `text` - text where to find words with the Russian <е> letters.

    return set of str - set of lower case words containing the Russian <е> letters.
    """
    text_words = RE_WORD_BOUNDARY.findall(text.lower())
    return set([word for word in text_words if 'е' in word])


def yobase_text_intersection(yobase: dict[str, str], text: str) -> list:
    """
    Find all potential words in the text to recover the <Ё> letters using Yobase.

    dict[str, str] `yobase` - mapping from 'е' version to 'ё' version of words;
    str `text` - text where to find words to recover the <Ё> letters.

    return list of str - potential words in which to recover the <Ё> letters.
    """
    text_words = get_words_with_ye(text)
    # Check each word from text against the yobase dict
    return [yobase[word] for word in text_words if word in yobase]


def recover_yo_sure_compound_adjective(text: str) -> str:
    """
    Recover the <Ё> letters in the first parts of the compound adjectives, e.g. "зелёно-синий".

    str `text` - text where to recover the <Ё> letters in the first parts of the compound adjectives.

    return str - text with the <Ё> letters recovered in the first parts of the compound adjectives.
    """
    # Use preloaded dictionary instead of reading file
    for word_ye, word_yo in yo_sure_compound.items():
        for w_yo in (word_yo.lower(), word_yo.upper(), word_yo.capitalize()):
            w_ye = w_yo.replace('ё', 'е').replace('Ё', 'Е')
            # Escape special regex characters in the word
            word_escaped = re.escape(w_ye)
            regex = rf'\b{word_escaped}-\w+\b'
            text = replace_by_regex(text, regex, w_ye, w_yo)

    return text


def escape_ye_sure_first_words(text: str) -> str:
    """
    Escape the <Е> letters in the words never used with prepositions.
    For example, "Я знаю, чем тебе помочь." becomes "Я знаю, ч<е>м тебе помочь.",
    because "чем" right after the comma is never written with the <Ё> letter.

    str `text` - text where to escape the <Е> letters.

    return str - text with the <Е> letters escaped.
    """
    # Use preloaded dictionary instead of reading file
    for word_wo_escape, word_with_escape in ye_sure_first_words.items():
        for w_with_escape in (word_with_escape.lower(), word_with_escape.upper(), word_with_escape.capitalize()):
            w_wo_escape = w_with_escape.replace('<', '').replace('>', '')
            # Escape special regex characters
            word_escaped = re.escape(w_wo_escape)
            sentence_ends_escaped = re.escape(SENTENCE_ENDS)
            after_word_escaped = re.escape(AFTER_WORD)
            regex = rf'[{sentence_ends_escaped}]\s{word_escaped}[{after_word_escaped}]'
            text = replace_by_regex(text, regex, w_wo_escape, w_with_escape)

    return text


def escape_ye_sure(text: str) -> str:
    """
    Escape the <Е> letters in the words with angle brackets where this letter is obligatory.
    For example, "прежде чем" becomes "прежде ч<е>м", because this collocation is never written with <Ё>.
    This allows to esape a set of words from the process of recovering the <Ё> letters.

    str `text` - text where to escape the <Е> letters.

    return str - text with the <Е> letters escaped.
    """
    text = escape_ye_sure_first_words(text)

    # Use preloaded dictionary instead of reading file
    for word_wo_escape, word_with_escape in ye_sure.items():
        for w_with_escape in (word_with_escape.lower(), word_with_escape.upper(), word_with_escape.capitalize()):
            w_wo_escape = w_with_escape.replace('<', '').replace('>', '')
            # Escape special regex characters
            word_escaped = re.escape(w_wo_escape)
            after_word_escaped = re.escape(AFTER_WORD)
            regex = rf'\s{word_escaped}[{after_word_escaped}]'
            text = replace_by_regex(text, regex, w_wo_escape, w_with_escape)

    return text


def unescape_ye_sure(text: str) -> str:
    """
    Remove <Е> letters escaping.

    str `text` - text where to unescape the <Е> letters.

    return str - text with the <Е> letters unescaped.
    """
    text = RE_ESCAPE_E_LOWER.sub('е', text)
    text = RE_ESCAPE_E_UPPER.sub('Е', text)
    return text


@lru_cache(maxsize=1024)
def _compile_word_boundary_regex(word: str) -> re.Pattern:
    """Compile word boundary regex for a specific word."""
    word_escaped = re.escape(word)
    return re.compile(rf'\b{word_escaped}\b')


def recover_yo_sure(text: str) -> str:
    """
    Recover all certain <Ё> in the text.

    str `text` - text where to find and recover certain <Ё> letters;
    return - str: text with certain <Ё> letters recovered.
    """
    text = recover_yo_sure_compound_adjective(text)

    yo_sure_words = yobase_text_intersection(yo_sure, text)

    # Use preloaded dictionary instead of reading file - add collocations values
    yo_sure_words += list(yo_sure_collocations.values())

    for word in tqdm(yo_sure_words, disable=True):
        for w_yo in (word.lower(), word.upper(), word.capitalize()):
            w_ye = w_yo.replace('ё', 'е').replace('Ё', 'Е')
            # Use precompiled regex with caching
            compiled_regex = _compile_word_boundary_regex(w_ye)
            text = compiled_regex.sub(w_yo, text)

    return text


def recover_yo_unsure(text: str, print_width: int=100, yes_reply: str='ё') -> str:
    """
    Recover all uncertain <Ё> in the text in the interaction mode.
    
    str `text` - text where to find and recover uncertain <Ё> letters;
    int `print_width` - how many characters to print while interaction (default: 100);
    str `yes_reply` - input required to confirm replacement <Е> with <Ё> (default: "ё");
    return - str: text with uncertain <Ё> letters recovered.
    """
    yo_unsure_words = yobase_text_intersection(yo_unsure, text)
    
    text = escape_ye_sure(text)

    for word in yo_unsure_words:
        for w in [word, word.capitalize(), word.upper()]:
            word_with_ye = w.replace('ё', 'е').replace('Ё', 'Е')
            # Use precompiled regex with caching
            compiled_regex = _compile_word_boundary_regex(word_with_ye)
            hits = compiled_regex.finditer(text)
            
            for hit in hits:
                start = hit.start()
                end = hit.end()
                hit_len = end - start
                print_start = max(0, start - print_width // 2 + hit_len // 2 + hit_len % 2)
                print_end = min(len(text), end + print_width // 2 - hit_len // 2)
                
                start_diff = start - print_start
                end_diff = print_end - end
                print_sum = start_diff + end_diff + hit_len
                
                if end_diff < start_diff and print_sum < print_width:
                    print_start = max(0, print_start - (print_width - print_sum))
                if end_diff > start_diff and print_sum < print_width:
                    print_end = min(len(text), print_end + (print_width - print_sum))
                
                printed_text = f'\n{text[print_start:start]}\033[1;31m{text[start:end]}\033[0m{text[end:print_end]}\n'
                printed_text = unescape_ye_sure(printed_text)
                cli_width = round(os.get_terminal_size().columns * 0.75)
                
                print('_' * cli_width)
                print(printed_text)

                if input(f'{word_with_ye} → {w}? ').lower() == yes_reply:
                    text = text[:start] + text[start:end].replace(word_with_ye, w) + text[end:]

    text = unescape_ye_sure(text)
    
    print('\n\033[1;31m<Ё> recovery complete!\033[0m')
    print('\033[1;31mРасстановка точек над <Ё> завершена!\033[0m')
    return text