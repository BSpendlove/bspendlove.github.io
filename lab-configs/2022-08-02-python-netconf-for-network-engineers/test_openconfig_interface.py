from device_drivers.netconf.openconfig import OpenConfigDriver
from argparse import ArgumentParser

parser = ArgumentParser(
    description="Test NETCONF calls against vendor specific devices using openconfig or vendor specific XML/yang models"
)

parser.add_argument(
    "--host", type=str, help="IP address of NETCONF endpoint", required=True
)
parser.add_argument("--username", type=str, help="NETCONF Username", required=True)
parser.add_argument("--password", type=str, help="NETCONF Password", required=True)
parser.add_argument(
    "--interface", type=str, help="Name of the Interface", required=True
)

arguments = parser.parse_args()

device = OpenConfigDriver(
    host=arguments.host,
    username=arguments.username,
    password=arguments.password,
)

device.connect(password=device.password)

config = device.get_interface_config(interface=arguments.interface)
print(config)