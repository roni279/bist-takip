from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    """İki değer arasındaki farkı döndürür"""
    try:
        return value - arg
    except (TypeError, ValueError):
        return value
    
@register.filter
def divide(value, arg):
    """İlk değeri ikinci değere böler"""
    try:
        return value / arg if arg != 0 else 0
    except (TypeError, ValueError):
        return 0
    
@register.filter
def multiply(value, arg):
    """İki değeri çarpar"""
    try:
        return value * arg
    except (TypeError, ValueError):
        return 0 