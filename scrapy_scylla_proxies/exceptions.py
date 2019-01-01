# My exceptions for this package

class SSPException(Exception):
    pass

class SSPScyllaNotReachable(SSPException):
    pass

class SSPScyllaResponseError(SSPException):
    pass
