"""bcbio-nextgen-vm base exception handling."""


class BCBioException(Exception):
    """Base bcbio-nextgen-vm exception

    To correctly use this class, inherit from it and define
    a `template` property.

    That `template` will be formated using the keyword arguments
    provided to the constructor.

    Example:
    ::
        class InvalidCluster(BCBioException):

            template = "Cluster %(cluser_name)r is not defined in %(config)r."


        raise InvalidCluster(cluser_name="Cluster name",
                             config="cluster.config")
    """

    template = "An unknown exception occurred."

    def __init__(self, message=None, **kwargs):
        message = message or self.template

        try:
            message = message % kwargs
        except (TypeError, KeyError):
            # Something went wrong during message formatting.
            # Probably kwargs doesn't match a variable in the message.
            message = ("Message: %(template)s. Extra or "
                       "missing info: %(kwargs)s" %
                       {"template": message, "kwargs": kwargs})

        super(BCBioException, self).__init__(message)


class NotFound(BCBioException):

    """The required object is not available in container."""

    template = "The %(object)r was not found in %(container)s."


class NotSupported(BCBioException):

    """The functionality required is not available in the current context."""

    template = "%(feature)s is not available in %(context)s."


class InvalidConfig(BCBioException):

    """Not available or invalid configuration."""

    template = ("No clusters found or invalid configuration with config "
                "file %(config_file)r and storage directory %(storage_dir)r")
