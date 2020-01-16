---
layout: post
title: CCNP R&S - EVN Basics 
subtitle: Easy Virtual Network
comments: true
---

Easy Virtual Network - EVN... What exactly is EVN and why do I care?

Well if you're currently studying for the CCNP Route exam, then objective 4.3 Describe Easy Virtual Networking (EVN) is a reason why you should care! but before that, let's take a quick overview of the core feature that we use EVN with which is called VRF-Lite (let's just call it VRF...)

Imagine a hyper visor (Vmware or Hyper-V) where we allocate resources of the host to multiple VMs to run multiple services or servers on the same device. Now imagine that with a router but purely running multiple routing table instances instead of one big global routing table. We virtually create routing tables (or VRFs) which store routing information so they are completely independent. Take a look at the image below, this is a great example to first show someone who hasn't even heard of VRF:

![EVN Topology](/img/2020-01-16-ccnp-evn-basics/ccnp-evn-topology.JPG)

So imagine we put R1s interface connecting to CUSTOMER-A Site 1 into a VRF, and then R1s interface connecting to CUSTOMER-B Site 1 into a different VRF. The global routing table (show ip route) will currently just show the interface connecting to R2. If we look at the routing table for VRF-A on R1, we can see CUSTOMER-As subnets and the same with VRF-B/CUSTOMER-B.

Take a look at the customer subnets. CUSTOMER-A has 10.0.0.0/24 but so does CUSTOMER-B. This is a big advantage with VRFs because we now have multiple routing tables, so we can actually have multiple entries of the same subnet although it gets a bit tricky when we want this traffic to pass on the link towards R2.

Without getting too far ahead, normally we would use something like MP-BGP with the VPNv4 feature/attribute which will allow us to perform route importing and exporting on VRFs, uniquely identifying which route belongs to which customers VRF with a route distinguisher. This isn't too complicated to understand behind the background or to configure, but it just sounds long doesn't it? Why can't we simply have an easy way to allow this traffic from the VRFs traverse the link and simply reach the customers other site?

This is where Easy Virtual Network (EVN) comes into play! Implementing EVN requires no MP-BGP, VRF route importing/exporting, VPNv4 configuration etc.. and it simply does this via a protocol we mastered in our CCNA studies, 802.1Q.


Just imagine that R1 and R2 were switches for a moment, and we configured all this at layer 2. We configure a 802.1Q trunk between R1 and R2 to allow CUSTOMER-A vlan and CUSTOMER-B vlan, configure the ports connecting to CUSTOMER-A in vlan 100, and CUSTOMER-B in vlan 200. An 802.1Q header appears for traffic going on the trunk, so that the neighbor switch can determine which VLAN this traffic belongs to, funny enough with a few more terms this is starting to sound like what EVN does at it's core.

EVN allows us to configure the link between R1 and R2 as a 'vnet' trunk, traffic will include a 'vnet' tag which allows us to define which traffic will belong to which VRF. Oh this just sounds like your just adding the word 'vnet' in front of every word for a typical setup for VLANs and 802.1Q.

Routers act a bit different when they receive a vnet tagged frame on a vnet trunk, but the concept is exactly the same as we know layer 2. Take a look at an OSPF packet which is currently going across the vnet trunk in this lab:
![EVN VNET Configuration](/img/2020-01-16-ccnp-evn-basics/ccnp-evn-vnet-diagram.png)
![EVN VNET OSPF Capture](/img/2020-01-16-ccnp-evn-basics/ccnp-evn-wireshark-vnet-ospf.png)

All I see, is an OSPF packet from 10.0.0.2, going across a trunk with the VLAN id tagged as 100....? Where is EVN? Does this mean my packets can traverse across multiple switches?

EVN simply reuses the 802.1Q header to carry the VNET tag. So in theory, you can have this traffic traverse a switch in a local network but it isn't recommended to use EVN as a 'gateway' solution in a typical network, it wasn't designed for that.

Because we define the vnet tag in a VRF, if a router receives traffic for vnet 100, then it will use the VRF table to perform the routing lookups on that specific VRF table.

 
Enough theory, let's look at some basic configuration:

## R1
~~~
interface GigabitEthernet0/0
 vnet trunk
 ip address 10.0.0.1 255.255.255.252
~~~
## R2
~~~
interface GigabitEthernet0/0
 vnet trunk
 ip address 10.0.0.2 255.255.255.252
~~~

The link between R1 and R2 has now been configured as a VNET Trunk, so let's create the VRFs and define a TAG for the traffic in VRF: CUSTOMER-A as 100, and VRF: CUSTOMER-B as 200. We'll also use the command 'address-family ipv4' otherwise we won't be able to configure an IP address on the interface that we put into the VRF:

## R1
~~~
vrf definition CUSTOMER-A
 vnet tag 100
 address-family ipv4

vrf definition CUSTOMER-B
 vnet tag 200
 address-family ipv4
~~~
## R2
~~~
vrf definition CUSTOMER-A
 vnet tag 100
 address-family ipv4

vrf definition CUSTOMER-B
 vnet tag 200
 address-family ipv4
~~~

Let's quickly configure the interfaces for CUSTOMER-A on R1 and R2, we'll also quickly create an OSPF process for both VRFs so we can establish a neighborship between both VRFs.

## R1
~~~
interface GigabitEthernet0/1
 vrf forwarding CUSTOMER-A
 ip address 192.168.1.1 255.255.255.252
 ip ospf 10 area 0

router ospf 10 vrf CUSTOMER-A
 network 10.0.0.1 0.0.0.0 area 0 !This is the OSPF relationship between R1 and R2 so that routes can be propagated)

router ospf 20 vrf CUSTOMER-B
 network 10.0.0.1 0.0.0.0 area 0
~~~
## R2
~~~
interface GigabitEthernet0/1
 vrf forwarding CUSTOMER-A
 ip address 192.168.2.1 255.255.255.252
 ip ospf 10 area 0

interface GigabitEthernet0/2
 vrf forwarding CUSTOMER-B
 ip address 192.168.2.1 255.255.255.252
 ip ospf 20 area 0

router ospf 10 vrf CUSTOMER-A
 network 10.0.0.2 0.0.0.0 area 0

router ospf 20 vrf CUSTOMER-B
 network 10.0.0.2 0.0.0.0 area 0

!configure loopback on CUS-A-2 just for fun...
interface Loopback0
 ip address 10.0.1.1 255.255.255.0
 ip ospf network point-to-point
 ip ospf 1 area 0​
~~~

## IP Routing table confirmation on CUS-A-2:
~~~
CUS-A-2#show ip route
O        10.0.0.0/24 [110/4] via 192.168.2.1, 00:07:06, GigabitEthernet0/0
O        10.0.0.0/30 [110/2] via 192.168.2.1, 00:11:35, GigabitEthernet0/0
O        192.168.1.0 [110/3] via 192.168.2.1, 00:11:35, GigabitEthernet0/0
~~~

Let's look at an issue we've already ran into. The link between R1 and R2 (10.0.0.0/30) is advertising into OSPF so that is currently causing an issue for us because we are trying to use 10.0.0.0/24 from Site 1.

Well EVN is normally a service that you provide for a small environment and not provided by eg. an ISP so we can easily just adjust our subnetting scheme so nothing overlaps, you should always ensure that you have planned out subnets + future subnetting that may be required at remote sites etc..

The difference between the global routing table on R1 vs the VRF routing tables:
~~~
R1#show ip route
      10.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
C        10.0.0.0/30 is directly connected, GigabitEthernet0/0
L        10.0.0.1/32 is directly connected, GigabitEthernet0/0

R1#show ip route vrf CUSTOMER-A
Routing Table: CUSTOMER-A
      10.0.0.0/8 is variably subnetted, 4 subnets, 3 masks
O        10.0.0.0/24 [110/2] via 192.168.1.2, 00:13:18, GigabitEthernet0/1
C        10.0.0.0/30 is directly connected, GigabitEthernet0/0.100
L        10.0.0.1/32 is directly connected, GigabitEthernet0/0.100
O        10.0.1.0/24 [110/3] via 10.0.0.2, 00:10:14, GigabitEthernet0/0.100
      192.168.1.0/24 is variably subnetted, 2 subnets, 2 masks
C        192.168.1.0/30 is directly connected, GigabitEthernet0/1
L        192.168.1.1/32 is directly connected, GigabitEthernet0/1
      192.168.2.0/30 is subnetted, 1 subnets
O        192.168.2.0 [110/2] via 10.0.0.2, 00:10:14, GigabitEthernet0/0.100

R1#show ip route vrf CUSTOMER-B
Routing Table: CUSTOMER-B
      10.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
C        10.0.0.0/30 is directly connected, GigabitEthernet0/0.200
L        10.0.0.1/32 is directly connected, GigabitEthernet0/0.200
~~~

If you would like to dive deeper into EVN and VRFs, I would highly suggest checking out the IOS documentation by Cisco. For now, this is as much as you need to know to describe EVN, let's make a summary...

## Summary
**EVN allows us to:**
- Provide an easy way to perform traffic separation on a VRF basis without using all the big boy features like MP-BGP, VPNv4, RD/Route import/export  
- EVN (more VRFs) allow us to reuse IP addresses/subnets because the VRF will use a different routing table  
- VRFs don't cost anything, although we are limited to the amount of VRFs the device allow us to configure (normally 16 or 32) 

**Some disadvantages:**
- Personally, I think it's not very flexible when using on very large networks  
- As mentioned above, a disadvantage is that you can only configure a small amount of VRFs, not a massive limitation...  
