---
layout: post
title: Cisco XR YDK Useful Modules
subtitle: A list and examples of useful modules in Python
comments: true
---

I'm sharing this list because of the amount of trouble/time it has taken me to find useful modules for help the average netconf/yang virgin that is unable to find a good example on configuring devices running Cisco XR or even just reading information such as interface configurations, IGP configs, implementing IS-IS via netconf, etc....

Firstly, don't skip over installation documentation for Cisco's YDK. It should be as simple as running a few pip install commands to obtain the python modules and away you go. However depending on different versions of Python, you'll come across countless errors if you just start sudo'ing your way through things or attempt to do anything on Windows OS (kidding, but these things are horrible to experience on Windows, try using pyang and converting a YANG model with the pyangbind profile that generates the Python class automatically... No thank you!)

As of writing this, I have a virtual environment (python -m venv .venv)
```
(.venv) bspendlove@home-ubuntu:~/dev/github/netconf-xrv-example$ python --version
Python 3.6.9
```

I also have a few other modules installed on this venv but you can also see ydk and ydk-models-cisco-ios-xr (which will automatically install  ydk-models-ietf)
```
(.venv) bspendlove@home-ubuntu:~/dev/github/netconf-xrv-example$ pip list
DEPRECATION: The default format will switch to columns in the future. You can use --format=(legacy|columns) (or define a format=(legacy|columns) in your pip.conf under the [list] section) to disable this warning.
bcrypt (3.1.7)
cffi (1.14.0)
cryptography (2.9.2)
lxml (4.5.1)
ncclient (0.6.7)
paramiko (2.7.1)
pip (9.0.1)
pkg-resources (0.0.0)
pyang (2.2.1)
pybind11 (2.5.0)
pycparser (2.20)
PyNaCl (1.4.0)
setuptools (39.0.1)
six (1.15.0)
ydk (0.8.4)
ydk-models-cisco-ios-xr (6.6.3)
ydk-models-ietf (0.1.5.post2)
```

Let's take a look at the base python script I'm using when I play around with the different modules:
```python
from ydk.providers import NetconfServiceProvider
from ydk.services import CRUDService
#from ydk.models.cisco_ios_xr import Cisco_IOS_XR_ifmgr_cfg as ifmgr # This is an example module, when we import modules referenced later in this post, it will be located here

provider = NetconfServiceProvider(
        address="192.168.0.51",
        port=830,
        username="cisco",
        password="cisco",
        protocol="ssh"
    )

crud = CRUDService() #CRUD service is what handles the operations between our Python code and creating the actual XML data for forming create/read/update/delete (CRUD) requests
```

## Reading Interfaces

The YANG model that Cisco IOS-XR uses to reference it's interfaces is called the ifmgr like such:
```python
from ydk.models.cisco_ios_xr import Cisco_IOS_XR_ifmgr_cfg as ifmgr #http://ydk.cisco.com/py/docs/gen_doc_df76b47e76a58aa15aee29b3b0484ba370fd9172.html
```

the CRUD reader requires us to pass in the netconf service provider (which is the handler for the netconf session) as a variable, and also our entity which will be the InterfaceConfigurations().

```python
interfaces = ifmgr.InterfaceConfigurations()

#Why don't we quickly print the interface names too while we are at it...
for interface in  interfaces.interface_configuration:
    print(interface.interface_name)


Output Example:
TenGigE0/0/0/0
TenGigE0/0/0/1
TenGigE0/0/0/2
TenGigE0/0/0/3
TenGigE0/0/0/4
TenGigE0/0/0/5
TenGigE0/0/0/6
...
```

## Reading/Setting the hostname

```python
from ydk.providers import NetconfServiceProvider
from ydk.services import CRUDService
from ydk.models.cisco_ios_xr import Cisco_IOS_XR_shellutil_cfg as shutil

provider = NetconfServiceProvider(
        address="192.168.0.51",
        port=830,
        username="cisco",
        password="cisco",
        protocol="ssh"
    )

crud = CRUDService()

hostname = shutil.HostNames()

current_hostname = crud.read(provider, hostname)

print("Current hostname: ".format(hostname.host_name))

#Now we can directly interact with the shutil.HostNames() class since this holds all the attributes/variables that can be used for the crud.update() function.

hostname.host_name = "test.ydk.example"
crud.update(provider, hostname)
print("New hostname: {}".format(crud.read(provider, shutil.HostNames()).host_name)) #This is a bad example but I have tried to not reuse any class to show you 100% the hostname has changed:

Output:
Current hostname: xr-test-device
New hostname: test.ydk.example
```

Blog needs to be finished, I'm a lazy bastard...