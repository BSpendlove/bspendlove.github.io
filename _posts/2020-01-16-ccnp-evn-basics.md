---
layout: post
title: CCNP: EVN Basics
subtitle: Easy Virtual Network
comments: true
---

Easy Virtual Network - EVN... What exactly is EVN and why do I care?

Well if you're currently studying for the CCNP Route exam, then objective 4.3 Describe Easy Virtual Networking (EVN) is a reason why you should care! but before that, let's take a quick overview of the core feature that we use EVN with which is called VRF-Lite (let's just call it VRF...)

Imagine a hyper visor (Vmware or Hyper-V) where we allocate resources of the host to multiple VMs to run multiple services or servers on the same device. Now imagine that with a router but purely running multiple routing table instances instead of one big global routing table. We virtually create routing tables (or VRFs) which store routing information so they are completely independent. Take a look at the image below, this is a great example to first show someone who hasn't even heard of VRF:
![EVN Topology]('img/2020-01-16-ccnp-evn-basics/ccnp-evn-topology.jpg'){: .center-block :}