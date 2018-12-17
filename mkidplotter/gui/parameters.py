from pymeasure.experiment import Parameter


class FileParameter(Parameter):
    """
    :class:`.Parameter` sub-class for use inputing files. Acts just like the base class.
    :var value: The value of the parameter
    :param name: The parameter name
    :param default: The default value
    :param ui_class: A Qt class to use for the UI of this parameter
    """
    pass


class DirectoryParameter(Parameter):
    """
    :class:`.Parameter` sub-class for use inputing files. Acts just like the base class.
    :var value: The value of the parameter
    :param name: The parameter name
    :param default: The default value
    :param ui_class: A Qt class to use for the UI of this parameter
    """
    pass