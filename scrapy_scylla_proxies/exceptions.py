class SSPException(Exception):
    """Top level SSP middleware exception."""
    pass


class SSPScyllaNotReachableError(SSPException):
    """Unable to reach the Scylla API."""
    pass


class SSPScyllaResponseError(SSPException):
    """Unexpected or missing values in the reponse from the Scylla API."""
    pass


class SSPNoProxiesError(SSPException):
    """The middleware has an empty proxy list."""
    pass


class SSPScyllaNoProxiesError(SSPException):
    """There were no proxies returned from the Scylla API."""
    pass