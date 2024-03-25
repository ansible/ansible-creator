"""Utilities for jinja2."""
import re

from html import escape as html_escape

from ansible.module_utils._text import to_text
from ansible.module_utils.six import string_types
from jinja2.runtime import Undefined


NS_MAP = {}

_ITALIC = re.compile(r"I\(([^)]+)\)")
_BOLD = re.compile(r"B\(([^)]+)\)")
_MODULE = re.compile(r"M\(([^)]+)\)")
_URL = re.compile(r"U\(([^)]+)\)")
_LINK = re.compile(r"L\(([^)]+), *([^)]+)\)")
_CONST = re.compile(r"C\(([^)]+)\)")
_RULER = re.compile(r"HORIZONTALLINE")


def to_kludge_ns(key, value):
    """Save a value for later use.

    :param key: The key to store under
    :param value: The value to store
    :return: An empty string to not confuse jinja
    """
    NS_MAP[key] = value
    return ""


def from_kludge_ns(key):
    """Recall a value stored with to_kludge_ns.

    :param key: The key to look for
    :return: The value stored under that key
    """
    return NS_MAP[key]


def html_ify(text):
    """Convert symbols like I(this is in italics) to valid HTML.

    :param text: The text to transform
    :return: An HTML string of the formatted text
    """
    if not isinstance(text, string_types):
        text = to_text(text)

    text = html_escape(text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _MODULE.sub(r"<span class='module'>\1</span>", text)
    text = _URL.sub(r"<a href='\1'>\1</a>", text)
    text = _LINK.sub(r"<a href='\2'>\1</a>", text)
    text = _CONST.sub(r"<code>\1</code>", text)
    text = _RULER.sub(r"<hr/>", text)

    return text.strip()


def rst_ify(text):
    """Convert symbols like I(this is in italics) to valid restructured text.

    :param text: The text to transform
    :return: An RST string of the formatted text
    """
    text = _ITALIC.sub(r"*\1*", text)
    text = _BOLD.sub(r"**\1**", text)
    text = _MODULE.sub(r":ref:`\1 <\1_module>`", text)
    text = _LINK.sub(r"`\1 <\2>`_", text)
    text = _URL.sub(r"\1", text)
    text = _CONST.sub(r"``\1``", text)
    text = _RULER.sub(r"------------", text)

    return text


def documented_type(text):
    """Convert any python type to a type for documentation.

    :param text: A python type
    :return: The associated documentation form of that type
    """
    if isinstance(text, Undefined):
        return "-"
    if text == "str":
        return "string"
    if text == "bool":
        return "boolean"
    if text == "int":
        return "integer"
    if text == "dict":
        return "dictionary"
    return text
