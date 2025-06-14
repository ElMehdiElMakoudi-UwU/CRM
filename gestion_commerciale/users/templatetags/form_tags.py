from django import template

register = template.Library()

@register.filter(name='addclass')
def addclass(field, css_classes):
    """Add CSS classes to a form field."""
    return field.as_widget(attrs={'class': css_classes}) 