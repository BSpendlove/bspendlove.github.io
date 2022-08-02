from device_drivers.netconf.generic import GenericNetconfDriver


class IOSXRNetconfDriver(GenericNetconfDriver):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)