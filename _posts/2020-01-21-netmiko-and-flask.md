---
layout: post
title: Netmiko and web front-end example
subtitle: Automation is everything
comments: true
---

Flask is a Python framework that allows you to build a web application using Python and Jinja. There is much more to Flask but in this blog, I'm going to simply demonstrate how you can write a basic Flask app to interact with a Cisco device and display the returned output on a html file.

Let's start with the Netmiko/SSH side of things first, we'll write a quick function to retreive the hostname, IOS version and some other details. I've wrote a basic function with the TextFSM library that parses the data from show commands. You can use the Netmiko in-built TextFSM but I prefer using my own with templates located in a folder called 'templates' in the root folder of my project.

{% highlight python linenos %}
def netmiko_get_facts(ipaddr, username, password, secret):
    netmiko_returned = {}
    netmiko_dict = {'host' : ipaddr,
                    'device_type': 'cisco_ios',
                    'username': username,
                    'password': password,
                    'secret': secret}

    ssh_conn = ConnectHandler(**netmiko_dict)

    showVer = ssh_conn.send_command("show version")

    iosDetails = textfsm_extractor('cisco_ios_show_version.template', showVer)
    netmiko_returned = {iosDetails[0]['hostname'] : iosDetails}

    return(netmiko_returned)
{% endhighlight %}

**Here is an example of an output returned by this function:**
~~~
{'testrtr': [{'config_register': '0x2102',
              'hardware': ['ISR4321/K9'],
              'hostname': 'testrtr',
              'reload_reason': 'PowerOn',
              'rommon': 'IOS-XE',
              'running_image': 'isr4300-universalk9.16.06.03.SPA.bin',
              'serial': ['FDO2224A1SK'],
              'uptime': '2 weeks, 2 hours, 5 minutes',
              'version': '16.6.3'}]}
~~~

This function will be used when rendering the HTML template in our Flask APP script.

Our flask run file will just ensure that the netmiko function we have created will pass the data into the template renderer and display when we try to reach our local web page:
~~~
testrtr
Hardware Platform: ISR4321/K9
IOS Version: 16.6.3
Serial Number: FDO2224A1SK
Running IOS Image: isr4300-universalk9.16.06.03.SPA.bin
~~~

###Flask python script:

{% highlight python linenos %}
from flask import render_template
from app import app
from app.functions import netmiko_get_facts

@app.route('/')
@app.route('/index')

def index():
    devices = [netmiko_get_facts('192.168.110.53', 'cisco', 'cisco', 'cisco')]
    return render_template('index.html', title='Home', devices=devices)
{% endhighlight %}

TO be updated in the future...