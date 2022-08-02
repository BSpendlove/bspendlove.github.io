from device_drivers.netconf.generic import GenericNetconfDriver


class IOSXRNetconfDriver(GenericNetconfDriver):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs, device_params={"name": "iosxr"})

    def get_interfaces_config(self) -> str:
        xml_filter = """
        <interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-um-interface-cfg">
            <interface/>
        </interfaces>
        """
        response = self.session.get_config(
            source="running", filter=("subtree", xml_filter)
        )
        return response.data_xml