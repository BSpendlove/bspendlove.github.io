from device_drivers.netconf.vendors.cisco import IOSXRNetconfDriver
from argparse import ArgumentParser

parser = ArgumentParser(
    description="Test NETCONF calls against vendor specific devices using openconfig or vendor specific XML/yang models"
)

parser.add_argument(
    "--host", type=str, help="IP address of NETCONF endpoint", required=True
)
parser.add_argument("--username", type=str, help="NETCONF Username", required=True)
parser.add_argument("--password", type=str, help="NETCONF Password", required=True)

arguments = parser.parse_args()

device = IOSXRNetconfDriver(
    host=arguments.host,
    username=arguments.username,
    password=arguments.password,
)

device.connect(password=device.password)

config = device.get_interfaces_config()
print(config)