---
layout: post
title: Automating basic BGP Flowspec rules with Python and ExaBGP
subtitle: Well, it isn't completely "automated".
comments: true
---

BGP - Border Gateway Protocol. You've heard of it, I've heard of it, we've all configured it in a lab or in production using our favorite terminal emulator over SSH, heck even Telnet if you're a mad man, or even Netconf if you're too cool for the CLI.

I gather the reader is not currently here to learn what BGP is, how BGP isn't a "routing protocol" (but it is, change my mind... RFC doesn't state it's an application protocol and you don't call RIP an application protocol so stop calling BGP an application protocol you bunch of hippies). However, BGP Flowspec caught your attention because it allows you to ["rapidly deploy and propagate filtering and policing functionaility"](https://www.cisco.com/c/en/us/td/docs/routers/asr9000/software/asr9k_r5-2/routing/configuration/guide/b_routing_cg52xasr9k/b_routing_cg52xasr9k_chapter_011.html#concept_DA7D34FDE3084BB395A3372CDF57689A).

Let's talk about pre-flowspec mitigation techniques, specifically RBTH (remotely triggered blackhole). The problem that we encounter with RBTH is that the configuration required will be applied/triggered against a specific IP address, configuration will also need to be applied after a DDoS attack has occured, which can be automated, however the main problem is that RBTH only allows blackholing an IP address based on a source address. If you want to block traffic based on a combination of a source IP address and port or destination address/port, you can apply ACLs on your edge devices. The problem with this approach is:

1) Manual ACL configuration on few/all edge devices, either via CLI or a script.
2) Vendor compatibility with ACL configuration (either manual ACL config via SSH scraping or Netconf will require different syntax/yang models).
3) Maintainence of multiple (if more than 1 vendor) device types and keeping track of ACL configurations.
4) Manual ACLs are messy... If you want to dynamically update it then good luck finding a nice way to do that with simple string slicing and CLI scrapping (if you are updating ACLs between multiple DDoS attacks then all the best to you with CLI scrapping).

If your devices support flowspec, then you already have a handy central management for your ACL configurations. Instead of manually deploying ACLs via SSH scripts, Netconf scripts or via typing commands into the CLI, you can use BGP Flowspec which is a more neutral approach to a multi-vendor environment. You don't have to worry about handling the correct vendors syntax or using the specific vendors Netconf yang model to deploy ACLs. Flowspec will now handle the control plane of propagating your ACLs (which are encoded in the BGP UPDATE messages, more specifically encoded in the NLRI and the action is encoded as an extended community). A device can be the flowspec "controller" where edge/transit routers are peering with it, waiting to receive flowspec updates which will technically be the same as applying an ACL to an interface. Cisco for example, can match a specific destination IPv4 address with a specific port and perform actions such as drop traffic, set DSCP values or redirect the flow to a different VRF.

You can explore the implementation for *insert x vendor here* but it typically comes down to the vendor implementing the RFC which defines the flowspec NLRI (RFC 5575), the components that make up the NLRI are the same things you had seen a few seconds ago, source/destination prefixes, IP protocol number, source/destination ports and also other components such as ICMP type, DSCP, packet length and TCP flags. Let's explore the lab topology and get some basics setup prior to moving onto the initial "automation" part.

![Base Topology](/img/2020-11-22-interacting-with-exabgp-flowspec-cli/base_topology.JPG)

### Important
If you are extremely new to flowspec, feel free to read the below 2 scenarios otherwise please skip until the next header.

Taking the above picture, there are many DDoS clients that are sourcing their attack from multiple IP addresses. This could be a dedicated service that people offer to be able to use DDoS clients (which have been installed to random computers around the internet due to things such as malware etc), a subscriber would pay a fee to use an amount of bandwidth to target a public IP address, in our case someone got angry with Dave because he is just naturally better at Call of Duty multiplayer compared to the attacker. Take RBTH as the first scenario, forget the "flowspec controller" and just think about pre-flowspec mitigation techniques. We've detected an anomaly through our monitoring solution and decide to blackhole traffic that is destined to Dave. With plain old RBTH, we've effectively prevented Dave being attacked from the DDoS clients but however because we are blackholing any traffic towards Dave, he can no longer reach the Call of Duty servers and still play online, or look at his Facebook feed simply because we are blackholing all traffic destined towards Dave. The initial problem was just many DDoS clients were trying to reach Daves public IP address on TCP port 80 but we are now preventing him using the internet.

Here is a 2nd scenario:

We magically see that a lot of traffic is destined to Dave on TCP port 80, sourcing from many multiple IP addresses so we can't block traffic based on source IP. Dave is having a hard time because the many DDoS botnet clients that are trying to reach his IP address on this port (even though it might not be open on his router/forwarding to a HTTP server) are saturating his internet bandwidth. The ISP decides to push out a manual flowspec rule through the CLI which is propagated throughout the network to the network transit/edge routers, these routers are able to decode the BGP flowspec NLRI messages and install a local rule which states:

"If any flows are coming in from the internet towards Dave (destination IP) on TCP port 80 (destination port), then I want you to drop the packet".

Dave might have a web server or some other service running on TCP port 80 that he exposes to his friends over the internet however he is still able to continue playing his games and browse facebook because traffic inbound is only blocked on TCP 80. It's almost like BGP flowspec just automatically setup an ACL to prevent TCP traffic on port 80 reaching Dave which means his connection is no longer saturated.

### Lab Configuration

(upload unfished due to me wanting to see the formatting of the post)
TO BE CONTINUED...