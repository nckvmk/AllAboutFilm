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
