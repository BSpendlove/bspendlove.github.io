---
layout: post
title: Using Netmiko to gather Cisco IOS Hostname
subtitle: Cisco ISR 4321 Automation
comments: true
---

Sometimes, you forget to document important information such as device Hostnames or your colleagues don't always update documentation, change management IP addresses and you need to confirm the IP address to a specific device matches up to a certain hostname.

Or even you've been tasked to inventory a few hundred devices and obtain the hostname and take note of the device hostname along with the management IP address. With Python and the Netmiko library, it's actually very simple to obtain the devices hostname with just a username and password (no secret needed) because of the device prompt that appears when you SSH into a device.

Cisco normally prompt the device hostname after you authenticate the SSH session and you are sitting at the user EXEC level:

~~~
login as: cisco
Using keyboard-interactive authentication.
Password:
RTR01>
~~~

Netmiko has an inbuilt function to retrieve the prompt and return just the configured hostname:

{% highlight python linenos %}
from netmiko import ConnectHandler
details = {
'device_type' : 'cisco_ios',
'ip' : '10.198.224.254',
'username' : 'cisco',
'password' : 'letmein'
}

ssh_session = ConnectHandler(**details)
device = ssh_session.find_prompt()
print(device)

Output: RTR01>
{% endhighlight %}

We establish the SSH session with the ConnectHandler function and then can use the **find_prompt()** function that is inbuilt into the Netmiko Cisco Base Connection class. We now need to remove the > which can easily be achieved by using a python inbuilt function called **replace**.

~~~
device = device.replace('>','')
~~~

{% highlight python linenos %}
from netmiko import ConnectHandler
ip_addresses = ['10.198.224.254','10.198.224.10']
details = {
    'device_type' : 'cisco_ios',
    'username' : 'cisco',
    'password' : 'letmein'
    }
for ip_address in ip_addresses:
    details.update({'ip': ip_address})
    
    ssh_session = ConnectHandler(**details)
    device = ssh_session.find_prompt()
    device = device.replace('>','')
    
    print(device)

Output: RTR01
Output: DB-CSW01
{% endhighlight %}