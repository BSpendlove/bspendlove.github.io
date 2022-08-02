from device_drivers.netconf.generic import GenericNetconfDriver


class OpenConfigDriver(GenericNetconfDriver):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def get_interfaces_config(self) -> str:
        xml_filter = """
        <interfaces xmlns="http://openconfig.net/yang/interfaces">
            <interface/>
        </interfaces>
        """
        response = self.session.get_config(
            source="running", filter=("subtree", xml_filter)
        )
        return response.data_xml