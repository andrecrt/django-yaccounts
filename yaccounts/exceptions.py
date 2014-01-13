class InvalidParameter(Exception):
    """
    Exception raised when there is a problem with a method parameter. 
    """
    def __init__(self, parameter, message):
        self.parameter = parameter
        self.message = message
    def __str__(self):
        return repr(self.err)