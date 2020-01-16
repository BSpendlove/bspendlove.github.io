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