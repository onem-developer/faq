from django.core import validators
from django.utils.deconstruct import deconstructible


@deconstructible
class UsernameValidator(validators.RegexValidator):
    regex = r'[^\w\-_.]'
    message = str('Enter a valid username. This value must start with a letter'
                  ', may contain numbers, letters and ./-/_ characters.')
    flags = 0
