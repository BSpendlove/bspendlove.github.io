---
layout: post
title: My experience with trying to design a BNG infrastructure (#1)
subtitle: Probably a very long and boring post about IPoE and DHCP
comments: true
---

NOTE: This will be a multi-part post because there is too much to cover in 1 sitting...

I am still quite very new to BNGs and have had to chance to lead a massive part of a design that required a brand new concept introduced into the network which is running BNGs. Essentially you terminate subscribers on a BNG to handle simple things like user authorization, policing/qos, central accounting and can handle other things but let me tell you the requirements I've had to deal with that I will hope to speak about in this blog post(s):

1) Carry QinQ (double tagged frames) back to a BNG

2) Authorize customers based on IPoE (DHCP triggered) sessions

3) Provide policing (speed packages) and basic activating/deactivating services

4) Dynamic vs Static IP address assignment

5) Static IPv6 PD assignment

6) Centralized accounting purely for building additional tools to perform further actions (eg. troubleshooting tools)

7) RADIUS must be redundant, however all subscribers must be allowed to get to the internet if the AAA functions fail (eg. RADIUS is unreachable)

8) Account for distributed vs centralized BNG design with all the above requirements

The actual reason for the implementation of BNGs was to deal with QinQ in a "easy" and "simple" way from the network perspective, the more simple the network, the easier it is to troubleshoot at 3am on a Sunday...

Majority of articles and blogs discussing BNGs I've found will typically start with showing a demonstration of the CPE connecting to a DSLAM, and then carrying that CPE traffic via Layer 2 to a BNG using something like L2TP. Take this example diagram:

![DSLAM L2TP/PWHE](/img/2022-05-14-bng-radius-design/dslam_l2tp.PNG)

This is obviously a very simplified diagram, more technologies might be in the background or even more BNGs/DSLAMs however this will be fine for the general concept. Subscribers will be transparent to the whole process but the most common 2 protocols/technologies are PPPoE (PPP over Ethernet) and IPoE (IP over Ethernet). However I will only be speaking about IPoE because I don't have any experience with PPPoE and BNGs... Note there are advantages and disadvantages with the 2 methods of deployment, for example IPoE is triggered typically by the DHCP discover packet and requires a bit more intervention to reauthenticate a customer by forcing them to renew DHCP (eg. via DHCP NACK or just terminating the service using Radius COA), DHCP does not have a keepalive mechanism so typically you would wait for the lease to expire whereas with PPPoE, you do have keepalives and can have an easier time terminating a session and the CPE would react properly.

Now let's jump into 2022 and replace "DSLAM" with "OLT" because I'm only 25 and haven't touched a DSLAM...

When a subscriber connects to the network, a DHCP discover message is sent upstream so it can grab an IP address and start talking to the internet. It looks like any other DHCP discover message you've seen in your networking career, just a device sending a broadcast message trying to see if anyone will give them an IP address:

![DHCP Discover](/img/2022-05-14-bng-radius-design/dhcp_discover.PNG)

Let's skip over transporting this message from the OLT to the BNG for now and skip ahead quickly. The BNG will typically look at this DHCP message and attempt to authenticate/authorize the subscriber typically based on a username/password combination. The most common way to do this is to open up the DHCP discover message, look for Option 82 which will include sub options that identify the user however this isn't presented in the initial DHCP discover from the client in the above example. You can authenticate based on the MAC address instead of option-82 and create usernames in your radius database as MAC addresses but remember, customers change routers/devices so this is a massive administrative pain and I wouldn't recommend it.

Therefore we need to "inject" or "insert" some information before this DHCP message gets to our BNG, we can do that by intercepting DHCP traffic (so majority if not all vendors will open up this discover and insert some value you configure on the device), its up to you what exactly you want to insert to idenfity the client but a common sub-option for DHCP Option-82 is sub-option 6 (Subscriber ID). You could insert the customers email address (which should be unique?) or some unique identifier that ties into your CRM to identify that specific customer.

![DHCP Option 82 Inserted](/img/2022-05-14-bng-radius-design/dhcp_option_82.PNG)

On the BNG, you would configure a subscriber policy or step of instructions that deal with managing the subscriber, of course this varies between vendors the basic concept is that the BNG will process a policy configured by you to perform specific actions based on certain scenarios, in this example I'll attempt to be as generic as possible and not provide speicfic CLI output but my blog post is purely based on Cisco BNG along with whatever Juniper BNG documentation I come across.

In this case, policies will typically be triggered based on a DHCP event for a new subscriber for a sub-interface that matches the inner/outer vlans of the incoming frame, once that DHCP discover message is processed then our BNG can start processing the subscriber and attempt to authenticate the user which then allows us to determine if they are authorized on the network and can reach which ever services they need access to (or are configured to access). This is where RADIUS comes in to play, the BNG will send an access-request message with any attributes that are used to authenticate the customer (such as copying option-82 subscriber ID to the User-Name attribute in the radius request), at this point it is purely RADIUS between the BNG and the radius server(s) and therefore having a reliable radius infrastructure is why point 7 at the start of the blog is actually an important point which we will discuss after this long intro to BNGs.

Upon RADIUS determining to send an Access-Accept message back (authenticate and authorize the user if found in the radius database), you would typically return attributes which allow the BNG to act upon such as putting the customer in a specific speed package/policing the speed of the subscriber, assigning a specific IP address to the customer or redirecting them into a different VRF/routing table.

### Getting the frames to the BNG

Using a distributed BNG design, you could deploy local BNGs across all your sites that connect to the tailend of your subscribers whether it be your own network or a wholesale provider and perform basic BNG functions as local to your customer without having to tunnel your customers traffic over L2 using something like L2TP, MPLS L2VPN or EPVN. However this cost money and would be quite boring to end the blog here... However this kind of design I could imagine looking something similar to this:

![Distributed BNG POPs](/img/2022-05-14-bng-radius-design/distributed_bng_pop.PNG)

However imagine trying to move to this design when your existing POP routers do not support BNG functionality and you already have hundreds of POPs? This can be very expensive and while it looks like a pretty diagram, it might not be in the companies interest to perform a major network overhaul that could cost millions. Virtualized BNGs at each POP may be an option at this point you are typically comparing amount of subscriber sessions supported on the platform vs total throughput.

If you need to bring back your QinQ traffic (or even just single tagged traffic) to a BNG then you'll be looking at a layer 2 tunneling technology such as L2TP or L2VPNs, in this case I'll be talking about EVPN in more depth on another blog post, but essentially you move from the above topology to something like this:

![Centralized BNG EVPN](/img/2022-05-14-bng-radius-design/central_bng_evpn.PNG)

EVPN route import/export policies can be controlled to prevent PEs learning the MAC addresses of other subscribers located on other PEs which resuts in a very scalable design, however at this point you are pushing east-west traffic (subscriber to subscriber) through your BNGs (this is preferred anyway because you don't want broadcast traffic to end up at your other pops otherwise you might as well just stop using EVPN/policies). In my experience this issue isn't really relevant in a retail broadband network however I could imagine this being an issue that would need to be solved when you are providing wholesale services via BNG to other businesses, that is out of the scope of my blog and actually out of the scope of my experience but ideally you would put your separate wholesale customers in a separate EVPN policy and import/export based on their requirements if they need east to west traffic :-)...

Cisco BNGs (whether it be virtual or physical boxes) can be separated at layer 3 and will handle the failover between active/standby so EVPN is actually great if you ensure the mac is propagated to all your POPs from the central BNG pair in my diagram above, as long as the subscriber gateway interface on the BNG is within the same EVPN then I would assume it would work similar to VM mobility and that the MAC addresses seen on the EVPN network more recently will increment a value which would force all the CPEs to use the new MAC address of the backup BNG when it takes over. (Juniper uses VRRP with this type of design whereas Cisco just use a vMAC based on the session redundancy group (SRG)).

# QinQ / Double Tagged design

When you have complete control over your network, it can be quite easy to just deploy services at the access layer with layer 3 at each POP and no involvement with a BNG. In my experience, it is easy to just configure VLAN based services to keep the network simple and route the customer out via the nearest exit point from the POP, however when going on top of other network providers (specifically companies who deploy fibre/OLTs and then sell that as a product for customers to run ontop and deal with the end users/CPEs) it is quite common to see an NNI presented to you with double tagged frames (QinQ - S and C vlans), with this type of deployment it requires you to create some kind of mapping on the BNG to match S and C vlans. My thought are 2 different designs:

1) S vlans (or a small range) can identify your POP from an ISP perspective (unlike a OLT/DSLAM perspective because we're now imagining a scenario where we don't have control/full-control over the access equipment) (left side of the below diagram example)

2) S vlans (a range) are chopped up per POP based on the wholesale provider that you will provide services over (right side of the below diagram example)

![Wholesale BNG Architecture Example](/img/2022-05-14-bng-radius-design/wholesale_provider_bng.PNG)

This isn't a recommended architecture or good practice, but an example of the thought process in my head. You could specifically reserve more than 1 S VLAN at a POP for per wholesale provider in example #2 to ensure you can take more than 4k customers at a single area. However it isn't actually dependent and if you reserve a block of VLANs for a specific wholesale provider and perform a range match on the outer VLAN within the BNG configuration, you should be fine if you mix the design with splitting a range of VLANs per provider that can be used at any POP.

If we can't specifically create a range on the BNG, it would require multiple sub-interfaces and a lot of configuration however Cisco (and I am sure other vendors support it) can match outer VLANs based on a range. The inner VLAN must be learned to properly send traffic to the correct customer when return traffic is going out via your NNI with the wholesale provider. You can either manually configure this (however this will require a separate sub interface PER C VLAN which is not very scalable configuration wise), therefore on Cisco you can use the `ambiguous` command as a match for the inner VLAN (or in Juniper, you can use something along the lines of `vlan-tags outer $junos-stacked-vlan-id inner $junos-vlan-id` inside a dynamic profile, however I could be wrong since I don't actually deal with juniper equipment, its just an example of matching any vlan). The diagram above assumes that you will match the outer-vlan range and use any inner-vlan (aka ambiguous in Cisco terms) so this massively simplifies configuration on the BNG itself.

### Hardware/Software decisions

I'm sure many of the readers would agree but you typically don't want to purchase hardware just because it has a certain name on the box. At the end of the day, we would all love a free BNG that does Terabits of throughput with 2 million sessions but that isn't going to happen so we need to find the best BNG boxes (or software) for our requirements and at the best possible price. Therefore these are the things I've noticed that need to been considered when chosing the right hardware/software:

1) Throughput - You can think of this on a port basis, eg. 10Gs, 40Gs, 100Gs however you need to consider the platform architecture itself and how the limitations may affect you, for example you need to pay close attention to the various NPUs/chips and support if BNG fuctions will work on the specific linecards

2) Sessions - You need to ensure you get the correct # of supported sessions however you also need to consider the limitations of the platform similar to point #1. Running a bundle interface for example with 2 interfaces that are effectively connected to separate NPUs in the backplane will duplicate your subscriber count and not double your total amount of sessions you can run. The platform may support 128/256k sessions however a physical port may only be limited to 32/64k. Also find out from the vendors you are speaking with, does running QoS on the interface where your subscribers are arriving half the total amount of sessions? Is the BNG implementation counting IPv6 as separate sessions or will count as a single session (Dual-Stack)?

3) Cost - An obvious point that I shouldn't make however the above 2 points should make you question, why is this box more expensive than the other box yet does 32k less sessions with the same throughput? I personally haven't looked too much into the various virtualized BNG platforms that you can run on a server but it doesn't hurt to check out the virtualized options, although virtualized software doesn't always = cheap.

### Reading Material

Here are some posts that are great reading material on BNGs

- [IOS-XR BNG Deployment Guide](https://community.cisco.com/t5/service-providers-documents/asr9000-xr-bng-deployment-guide/ta-p/3110436)
- [BNG Dual-Stack Sessions](https://community.cisco.com/t5/service-providers-documents/asr9000-xr-bng-and-dual-stack-ipv4-and-ipv6-sessions/ta-p/3137979)
- [ASR9K Deployment Scale Guidelines](https://community.cisco.com/t5/service-providers-documents/bng-deployment-scale-guidelines-on-asr9000/ta-p/3156300)
- [ASR9K Understanding Geo-Redundancy](https://community.cisco.com/t5/service-providers-documents/asr9000-xr-using-and-understanding-bng-geo-redundancy/ta-p/3158636)
- [RADIUS and COA Deployment Guide](https://community.cisco.com/t5/service-providers-documents/asr9k-bng-radius-and-coa-deployment-guide/ta-p/3155211?attachment-id=86679)
- [Juniper Understanding Subscriber Management and BNGs](https://www.juniper.net/documentation/en_US/design-and-architecture/service-provider-edge/information-products/topic-collections/understanding-subscriber-mgmt.pdf)
- [Intel BNG in NFV](https://builders.intel.com/docs/networkbuilders/re-architecting-the-broadband-network-gateway-bng-in-a-network-functions-virtualization-nfv-and-cloud-native-world-1633374232.pdf)

### Next time

My next blog post will continue by talking about the radius infrastructure that sits behind the BNG to authenticate, authorize and performing accounting. The main reason is that I want to setup a quick lab and provide configurations and better diagrams with working examples so please tune in for the next post about my experience and thoughts being very new to BNGs :-)

We will discuss how users are authenticated via RADIUS and then returned attributes that make up a service (eg. a speed package for broadband customers), a few problem scenarios with dynamic and static IP assignment for CPEs, creating/the design of a redundant database backend and how dumb CPEs can be when you run IPv6.