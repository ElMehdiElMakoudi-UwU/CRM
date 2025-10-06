from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    A custom filter to access dictionary value by key in Django templates.
    Usage: {{ dictionary|get_item:key }}
    """
    return dictionary.get(key)