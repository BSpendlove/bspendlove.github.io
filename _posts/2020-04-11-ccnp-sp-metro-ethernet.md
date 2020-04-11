---
layout: post
title: Metro Ethernet Studies
subtitle: CCNP Service Provider
comments: true
---

1.1.a Core architectures (Metro Ethernet, MPLS, unified MPLS, SR)

Describing Metro Ethernet.... If you're like me then you probably have tried reading a few articles on the first page of google and have came to the conclusion that Metro Ethernet is a transport service that appears to the customer as one big single switch and that "it's only used in MANs (metropolitan area network)".... **yawn**

While it isn't a hard concept to understand, it's such a boring topic to read. I'm sitting here thinking to myself, is this one of those Frame Relay type topics where it's just not used in 2020?

A typical diagram you'll see looks something like this:
![MetroE Basic Topology](/img/2020-04-11-ccnp-sp-metro-ethernet/basic-topology.JPG)

You must keep in mind that Metro Ethernet refers to the technology (Ethernet) and doesn't force you to only use Ethernet Media. The Ethernet protocol itself can be used on a wide variety of Media, the two most common obviously being Copper and Optical Fibre.

## MAN

The word 'Metro' in Metro Ethernet stands for Metropolitan Area Network. I want you, the reader, to focus on the word 'Metropolitan'.

Here is the first few lines on Wikipedia about a Metropolitan Area:
```A metropolitan area is a region consisting of a densely populated urban core and its less-populated surrounding territories, sharing industry, infrastructure, and housing.```

Let's assume with some basic fundamental knowledge, as a service provider you could offer a Metro Ethernet service by connecting a customer to a switch (via Copper or Fibre) in a local pop/datacenter and run dark fibre between a few streets to another switch located in another pop/datacenter, put the customer into a VLAN and call it a Metro Ethernet Service right?

![Big Brain MetroE Solution](/img/2020-04-11-ccnp-sp-metro-ethernet/big-brain-solution.JPG)

So that was an easy solution? Oh the customer wants to add more sites? That's fine... Let's just... ahhh sh*t. What went wrong?

Oh, you've extended the Layer 2 domain across a large area? are you running the OSPF core on the MetroEthernet Multipoint service and every neighbor is flapping because of an unstable neighbor? Is STP crushing your network because we all know the golden rule about STP?

I would like to share some questions that I asked myself to determine why/when you would deploy Metro Ethernet:

- Is Metro Ethernet scalable? The name suggests that the solution should only exist in a single area (eg. London)
- Isn't MPLS L2VPN providing the same solution with scalability?
- Is Metro Ethernet a solution that we implement on it's own or with other technologies/protocols?
- VPLS is practically just an enhanced version of Metro Ethernet...

So where did Metro Ethernet come from? A group called Metro Ethernet Forum (MEF) decided to release a framework and define the services that a service provider could provide to customers looking for services such as Ethernet First Mile while ensuring that the framework meets some kind of standard. (such as the standards developed by IEEE and IETF)

### ME Standards

MEF focused on standardizing 3 main key services that can be used in a Metro Ethernet service, these are:

**1)** E-Line

**2)** E-LAN

**3)** E-Tree

Think of these services as:

**1)** Point to Point Network (VPWS)

**2)** Multipoint LAN (fully meshed VPLS)

**3)** E-Tree (partially meshed VPLS, like a hub-spoke topology)

These services can further be extended to provide sub-services, for example:

- E-Line Physical P2P for single customer
- E-Line Virtual P2P for multiple customers connecting to the same PE at a given POP/Datacenter

The difference between E-Line and VPWS is not very clear at the moment, but it sounds like just plain 802.1Q VLAN tagging for an E-Line service vs MPLS (with targetted LDP) with VPWS however that isn't to say you can't use MPLS with Metro Ethernet. In fact, if you actually compare the services such as VPWS and E-Line they practically achieve the same thing and that is technically correct.

The MEF actually describes an E-Line as a Service Type that is a basis for a broad range of services based on a P2P EVC (Ethernet Virtual Circuit), an E-LAN as a multipoint to multipoint service and E-Tree as a 'rooted' multipoint service.

### Partially Meshed E-LAN Example
![E-LAN Partial Mesh](/img/2020-04-11-ccnp-sp-metro-ethernet/e-lan-partially-meshed.JPG)

So... what is VPLS and let's compared it to MEF's E-LAN explanation...

Wikipedia: "Virtual Private LAN Service (VPLS) is a way to provide Ethernet-based multipoint to multipoint communication over IP or MPLS networks."

MEF E-LAN: "Any Ethernet Service that has the EVC Type Service Attribute equal to Multipoint-to-Multipoint is classified as an Ethernet LAN (E-LAN) Service Type. "

![u fokin wot m8](/img/2020-04-11-ccnp-sp-metro-ethernet/jc-wtf.JPG)

This concludes my final opinion:

MEF is like that person who asks if you'd like a glass of H 2O whereas IETF is the person that asks you if you'd like a glass of water... (Concept credit to Christa)
(Kidding! but IETF calls it VPLS, MEF calls it E-LAN.. They're the same thing, VPLS sounds better and I've never ever heard anyone reference any Ethernet transport services as Metro Ethernet, so I'm on the blue side and will never refer to E-Line/E-Lan/E-Tree)

What a waste of my study time, happy studying!

Links used:
https://wiki.mef.net/display/CESG/MEF+6.3+-+EVC+Ethernet+Services+Definitions
https://forum.huawei.com/enterprise/en/ethernet-services-e-line-and-e-lan/thread/481187-875
https://en.wikipedia.org/wiki/Metro_Ethernet
https://en.wikipedia.org/wiki/Metropolitan_area
