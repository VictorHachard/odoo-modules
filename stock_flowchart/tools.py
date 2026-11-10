# -*- coding: utf-8 -*-
"""Helpers to build Mermaid flowchart sources from records."""

# Mermaid entity codes (``#name;``) are decoded inside labels, so they let any
# text be written in a quoted label without ending it or starting a tag.
_MERMAID_ENTITIES = {
    '#': '#35;',
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


def mermaid_node_id(prefix, record):
    """Stable Mermaid node id of ``record``, also for new records of an onchange."""
    record.ensure_one()
    if record._origin.id:
        return f'{prefix}{record._origin.id}'
    return f'{prefix}new{abs(hash(record.id))}'


def mermaid_click(prefix, record):
    """Mermaid ``click`` line opening ``record`` in a new tab, '' for an unsaved record."""
    record.ensure_one()
    if not record._origin.id:
        return ''
    return f'click {mermaid_node_id(prefix, record)} "/odoo/{record._name}/{record._origin.id}" _blank'
