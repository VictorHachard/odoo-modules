# -*- coding: utf-8 -*-
"""Helpers to build Mermaid flowchart sources from records."""

# Mermaid entity codes (``#name;``) are decoded inside labels, so they let any
# text be written in a quoted label without ending it or starting a tag.
_MERMAID_ENTITIES = {
    '#': '#35;',
    '&': '#amp;',
    '"': '#quot;',
    '<': '#lt;',
    '>': '#gt;',
    '\r': ' ',
    '\n': ' ',
}


def mermaid_escape(text):
    """Return ``text`` safe to put between the double quotes of a Mermaid label."""
    return ''.join(_MERMAID_ENTITIES.get(char, char) for char in str(text or ''))


def mermaid_label(*parts):
    """Quoted Mermaid label made of ``parts``, one per line, empty parts skipped."""
    return '"%s"' % '<br>'.join(mermaid_escape(part) for part in parts if part)
