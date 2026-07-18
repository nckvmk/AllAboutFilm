"""Cache-busting static tag.

`{% static_v 'css/styles.css' %}` renders the normal static URL with the file's
last-modified time appended as a `?v=` query string, e.g.
`/static/css/styles.css?v=1752260400`. Whenever the file changes the URL
changes, so the browser is forced to fetch the fresh copy instead of serving a
stale cached one. Falls back to the plain URL if the file can't be located.
"""

import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static as static_url

register = template.Library()


@register.simple_tag
def static_v(path):
    url = static_url(path)
    absolute = finders.find(path)
    if absolute:
        try:
            return f"{url}?v={int(os.path.getmtime(absolute))}"
        except OSError:
            pass
    return url


@register.filter
def star_states(rating):
    """Turn a numeric rating into a list of five states — 'full', 'half' or
    'empty' — so a template can render a five-star row. Half is used when the
    fractional part is 0.5 or more (e.g. 4.2 -> 4 full + 1 empty; 4.6 -> 4 full
    + 1 half)."""
    try:
        value = float(rating or 0)
    except (TypeError, ValueError):
        value = 0.0
    states = []
    for position in range(1, 6):
        if value >= position:
            states.append('full')
        elif value >= position - 0.5:
            states.append('half')
        else:
            states.append('empty')
    return states
