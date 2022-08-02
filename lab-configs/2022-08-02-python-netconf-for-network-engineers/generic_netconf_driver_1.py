from ncclient import manager


class GenericNetconfDriver:
    """Generic NETCONF driver which implements common logic across all vendors.

    All Vendor drivers must inherit this class.

    Arguments:
        host:           IP or Domain Name of the device
        port:           NETCONF Port
        username:       NETCONF Username
        password:       Optional Password
        hostkey_verify: Uses ~/.ssh/known_hosts to verify SSH host keys
        look_for_keys:  Attempts to use any keys with path '~/.ssh/id_*'
        kwargs:         Keyword arguments which will be passed to ncclient connect() method
    """

    def __init__(
        self,
        *,
        host: str,
        port: int = 830,
        username: str,
        password: str = "",
        hostkey_verify: bool = False,
        look_for_keys: bool = False,
        **kwargs
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.hostkey_verify = hostkey_verify
        self.look_for_keys = look_for_keys
        self.session = None