---
layout: post
title: Netmiko - Check if VLAN exist on switch
subtitle: Automation is everything
comments: true
---

This blog post demonstrates an example on network validation, checking if a specific VLAN exists. The purpose of writing functions is to make your life easier, when you need to perform this task then you can just reference the function and you don't need to re-write the same code every time you want to perform this task.

A key detail regarding a function that performs such a validation isn't so you can constantly check if X vlan exists, but for example: Say you have a web front-end that allows junior network engineers to create a VLAN within the datacenter however, you want to implement a validation to check if VLAN X (manual input on the GUI) already exist. You can simply perform this check against a device database (if you have a database/repository for device configurations) however this isn't considered a true source of information (unless your database is constantly being updated/checked nightly for the VLANs on all devices).

For this example, we will simply use Netmiko with TextFSM to parse the 'show vlan brief' command on a Cisco Switch. It's good to consider vendor operability when writing a function such as checking if the specified VLAN exist but this just demonstrates a Cisco Catalyst switch.

1. We technically don't need to import Netmiko into our script because we will be passing the Netmiko ConnectHandler into this function (therefore our functions can be contained within a separate Python library/module or file)
2. We will parse the 'show vlan brief' output with TextFSM to return more readable/structured data in JSON format. We could go ahead and try to use NETCONF however that isn't covered in this post.
3. When we have returned output of all vlans that exist on the switch, we will run through a loop for all vlans and match it with the input of the function to find VLAN X
4. If we find VLAN X, we want to simply return the function to be **'True'** (meaning the VLAN does exist). If the VLAN doesn't exist then we will simply return **'False'**
5. We will also add an addition to allow the user to return the VLAN information (such as interfaces and VLAN name) if specified when calling the function

**Retreiving VLAN information**

Firstly, let's define a function to retreive the VLAN information from a given switch. We will directly use the Netmiko functions (**send_command()**) since we will require the ConnectHandler to be passed into our own function. I'm also going to use a TextFSM function I've created to extract the data based on a TextFSM template.
{% highlight python linenos %}
def get_vlan_data(netmiko_session):
    show_vlan = netmiko_session.send_command("show vlan brief")

    return(textfsm_extractor('cisco_ios_show_vlan.template',show_vlan))
{% endhighlight %}
~~~
Output Example:
[{'interfaces': ['Gi1/0'], 
 'name': 'IT', 
 'status': 'active', 
 'vlan_id': '10'},
 {'interfaces': ['Gi1/1'], 
  'name': 'HR', 
  'status': 'active', 
  'vlan_id': '20'},
 {'interfaces': ['Gi1/2'],
  'name': 'SALES',
  'status': 'active',
  'vlan_id': '30'},
 {'interfaces': ['Gi1/3'],
  'name': 'TEST_VLAN',
  'status': 'active',
  'vlan_id': '220'}]
  ~~~

As you can see, the returned output example demonstrates the JSON format like output for each VLAN. Each VLAN is returned as a dictionary with some basic information such as: VLAN ID, VLAN Name, Interfaces that belong to that VLAN (excluding trunk interfaces) and the VLAN status.

We can simply run a **for loop**. Logically, we can write:
{% highlight python linenos %}
vlans = get_vlan_data(_session)

for vlan in vlans:
    print(vlan)

Example Output:
{'vlan_id': '10', 'name': 'IT', 'status': 'active', 'interfaces': ['Gi1/0']}
{'vlan_id': '20', 'name': 'HR', 'status': 'active', 'interfaces': ['Gi1/1']}
{'vlan_id': '30', 'name': 'SALES', 'status': 'active', 'interfaces': ['Gi1/2']}
{'vlan_id': '220', 'name': 'TEST_VLAN', 'status': 'active', 'interfaces': ['Gi1/3']}
{% endhighlight %}

A dictionary in Python is similar to a real dictionary. If you open the Oxford Dictionary, you will find a word... next to the word is an explanation or an example how it's used.
Python defines this as for every key, there is a value. We can specifically reference the value of a key simply using the square brackets with the key we want - ** ['key'] **

{% highlight python linenos %}
netmiko_dict = {
    'host':'192.0.2.33',
    'device_type':'cisco_ios',
    'username':'myUsername',
    'password':'myPassword',
    'secret':'mySecret'
    }

print(netmiko_dict['host'])

Example Output:
192.0.2.33
{% endhighlight %}

In the previous example that demonstrated the interfaces that belong to each VLAN, the **interfaces** key has a value which is a list, meaning a collection of strings, integers, etc... or a mixture. If more than a single interface belongs to a specific VLAN, we'll see something like this:
~~~
{'vlan_id': '10', 'name': 'IT', 'status': 'active', 'interfaces': ['Gi1/0', 'Gi1/1', 'Gi1/2', 'Gi1/3']}
~~~

If we take our **for loop* example, we can introduce an **if** statement to only print the interfaces that belong to VLAN 10:
{% highlight python linenos %}
for vlan in vlans:
    if vlan['vlan_id'] == '10':
        print(vlan['interfaces'])

Example Output:
['Gi1/0', 'Gi1/1', 'Gi1/2', 'Gi1/3']
{% endhighlight %}

Each item within the list can specifically be accessed by the use of an index number (similar to how a book has an index). Starting from 0, we can select each interface by referencing the index position in the list [0], [1], [2] or [3]. Remember that we can run another **for** loop to reference each interface within the list like this:

{% highlight python linenos %}
for vlan in vlans:
    if vlan['vlan_id'] == '10':
        for interface in vlan['interfaces']:
            print("Interface: {0}".format(interface))

Example Output:
Interface: G1/0
Interface: G1/1
Interface: G1/2
Interface: G1/3
{% endhighlight %}

While I think it's relevant to demonstrate the basic Python fundamentals to interact with different data types, loops and such for those who are not familiar with Python or those that have just dived straight into Network Automation/Programmability without actually learning the basic Python fundamentals. Let's continue with our VLAN check function...

We have successfully wrote a function to return the **'show vlan brief'** command and parse it through TextFSM so that we have structured data to work with, let's write the function to check if the VLAN we input exists:

Start with basic logic in english:
1. Function - check_vlan_exist that requires 2 inputs (+ additional input to return the VLAN info): the netmiko session itself and then the VLAN we want to run the check on
2. Grab the current VLAN database information from our previous function we have created
3. Create a boolean called found_vlan and set to False
4. Loop through the VLANs (for vlan in vlans)
5. If vlanX (input) is found, then set found_vlan to True... If vlanX is not found, don't do anything since our Boolean Variable is still set to False
6. Optional: If we want the VLAN information to be returned, we will return the VLAN JSON data as soon as the VLAN has been found... breaking the loop instantly once found and preventing us from running through the remaining VLANs

{% highlight python linenos %}
def check_vlan_exist(netmiko_session, vlan_id, return_vlan_info=False):
    """
    netmiko_session = ConnectHandler function from Netmiko passed into this function
    vlan_id = VLAN ID that you are looking to match
    return_vlan_info = If this is set to true, the VLAN JSON output will be returned otherwise it will return False
    """
    found_vlan = False
    vlans = get_vlan_data(netmiko_session) #Our function we have already created previously

    for vlan in vlans:
        if vlan['vlan_id'] == vlan_id:
            found_vlan = True #If the VLAN is found, set it to True
            
            if return_vlan_info: #If return_vlan_info is set to True, return the VLAN information
                return(vlan)

        return(found_vlan) #Return VLAN as soon as we find the VLAN
    
    return(found_vlan) #If the VLAN doesn't exist, we will simply return it and it will be False
{% endhighlight %}

I want to actually take a look at this function and pick out specific details on how to improve the function or prevent issues with validation in mind. We all know that if something can break the function such as a mistyped VLAN (or even a letter instead of number), it's going to happen.

## What will happen if I do this...

What will happen if I try to pass a netmiko session into the function, but the username/password is incorrect?
- Netmiko Exception will throw an error regarding Authentication failed. You can use the Netmiko library to catch this exception within a try block and then execute the required code after...

What will happen if I type an integer instead of a string?
- If you try to match a string (vlan_id from our JSON data) with an int, it will always return False. We can force the input to always be a string by using the **str()** function.
{% highlight python linenos %}
for vlan in vlans:
        if vlan['vlan_id'] == str(vlan_id):
{% endhighlight %}

What will happen if I type a letter instead of a valid VLAN ID?
- The returned output will ALWAYS be False...

The main concern with the last 2 points however hasn't been addressed. What do you think the main problem could be? Our function works as intended and returns False because the VLAN doesn't exist whether it's mistyped by accident or by purpose. However the issue is that resources are being used... Our function still runs as intended, pulling the VLAN information via SSH, parsing the output via TextFSM and running through each loop with some logic. These are useless CPU cycles and memory being used when we know the output will always be False, the logical explanation would be to prevent the user from making these mistakes and prompting/throwing some kind of error to prevent the function from further using resources and getting no where...

Let's write a separate function to be used against the VLAN ID we input. We want to validate the following:
1) Is it a valid number - It now makes sense to run checks against an integer instead of a string, so we want the input to ALWAYS be an integer
2) Is the number within the range of VLANs (1-4095)

These simple logical steps are much less resource intesive than continuing to establish the SSH session (requiring the TCP session to be initiated, SSH exchage, data to be sent and read, etc...)
{% highlight python linenos %}
def check_vlan(vlan_id):
    if isinstance(vlan_id, int):
        if vlan_id in range(0,4095):
            return(True)
    return(False)
{% endhighlight %}

~~~
check_vlan_exist(_session, 10) = True

However

check_vlan_exist(_session, '10') = False
~~~

We could however, always convert the input **vlan_id** to be an integer. Python is able to convert a string to an integer however it must be in Base10 format. Hexadecimal or Alphabetical characters for example will throw an error like this:

{% highlight python linenos %}
def check_vlan(vlan_id):
    if int(vlan_id) in range(0,4095):
        return(True)
    return(False)

Example Output:
check_vlan(10) = True
check_vlan('4093') = True
check_vlan(4096) = False
check_vlan('32768') = False
check_vlan('A') = ValueError: invalid literal for int() with base 10: 'A'
{% endhighlight %}

### check_vlan_exist function changed
{% highlight python linenos %}
def check_vlan_exist(netmiko_session, vlan_id, return_vlan_info=False):
    """
    netmiko_session = ConnectHandler function from Netmiko passed into this function
    vlan_id = VLAN ID that you are looking to match
    return_vlan_info = If this is set to true, the VLAN JSON output will be returned otherwise it will return False
    """
    found_vlan = False
    
    if check_vlan(vlan_id):
        vlans = get_vlan_data(netmiko_session) #Our function we have already created previously

        for vlan in vlans:
            if vlan['vlan_id'] == str(vlan_id):
                found_vlan = True #If the VLAN is found, set it to True
                
                if return_vlan_info: #If return_vlan_info is set to True, return the VLAN information
                    return(vlan)
                
            return(found_vlan) #Return VLAN as soon as we find the VLAN
        return(found_vlan) #If the VLAN doesn't exist, we will simply return it and it will be False
    
    else: #If check_vlan returns False (not a valid VLAN) then we won't even try to SSH to the Switch and loop through current VLANs
        return(found_vlan)

Example Output:
True
{% endhighlight %}

If you found this blog post an interesting read or if it was helpful, feel free to leave a comment. I hope that I have demonstrated a simple validation process which allows you to paint a bigger picture, how you should approach writing your own functions with the flexibility and structured process to prevent resources being used when they don't need to be used.