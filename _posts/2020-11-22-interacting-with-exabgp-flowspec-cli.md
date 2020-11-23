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

ExaBGP is running as a docker container and exposing TCP port 179 so we can peer out intended edge/transit devices to the flowspec controller. In our case, we will peer using an XR device which will also be configured as a route-reflector for the flowspec v4 address family, which will reflect the flowspec updates to it's clients (transit 1 and transit 2). The docker-compose file can be found [here](https://github.com/BSpendlove/flowspec-v4-example/blob/master/docker-compose.yml). Some initial configuration has been added to the exabgp.conf which enables the IPv4 unicast and flowspec families towards 10.255.255.1 (loopback of the Route Reflector), also I have attached a process to the exabgp application which is a simple flask app. Currently this app performs no valdiation and allows a simple POST request for a specific URL and attempts to find 2 keywords within the POST body which are, command and neighbor.

Instead of having to update the exabgp.conf with the new rules, ExaBGP listens to the standard input stream on the shell after the "exabgpcli" keyword which allows us to dynamically interact with the ExaBGP process instead of having to update the .conf file and restart the docker container.

#### Route Reflector Configuration
```
router bgp 65100
 address-family ipv4 unicast
 !
 address-family ipv4 flowspec
 !
 neighbor-group FLOWSPEC-RR
  remote-as 65100
  update-source Loopback0
  address-family ipv4 unicast
   route-reflector-client
  !
  address-family ipv4 flowspec
   route-reflector-client
  !
 !
 neighbor 10.255.255.2 ! Transit 1
  use neighbor-group FLOWSPEC-RR
 !
 neighbor 10.255.255.3 ! Transit 2
  use neighbor-group FLOWSPEC-RR
 !
 neighbor 192.168.0.16 ! ExaBGP Container that exposes TCP 179
  use neighbor-group FLOWSPEC-RR
 !
```

#### Transit Configuration
```
! typical BGP configuration with flowspec ipv4 address family enabled
!
flowspec
 local-install interface-all
!
```

You can specifically enable flowspec rules to only be installed for certain interfaces which will need to be configured manually otherwise flowspec rules will be received but not installed.

```
transit-1#show bgp ipv4 flowspec summary 
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.255.255.1    4        65100      21      20        1    0    0 00:12:18        0
```

#### BGP Flowspec rule

A flowspec rule contains certain parameters regarding a flow to match a criteria and then perform an action (if required). Let's focus on the NLRI before we take a look at the syntax for ExaBGP. Here is a simple rule that will drop any IPv4 packets, protocol TCP with a destination port of 1234 destined towards a customer named "Dave" (10.50.100.100/32).

![Base Topology](/img/2020-11-22-interacting-with-exabgp-flowspec-cli/bgp_flowspec_nlri.JPG)

In the packet capture above, you can see within the NLRI, the flowspec NLRI holds the critera/description of the rule, IP packets are inspected and matched against protocol number 6 (TCP). Within the extended communities, no drop action exist, however a traffic-rate will be applied to this rule at 0Mbps (aka drop). This message is the update sent from the flowspec route reflector (as seen by the cluster_list and originator_id that an RR will append to a BGP update). If you want a deeper dive into the packet format, I would recommend reading the RFC to see the different filter types/component types which would be encoded in the flowspec NLRI to describe if the critera is a destination/source prefix, protocol number, port number etc...

```
transit-1#show bgp ipv4 flowspec 
     Network          Next Hop            Metric LocPrf Weight Path
 *>i  Dest:10.50.100.100/32,Proto:=6,DPort:=1234
                      0.0.0.0                       100      0 i
```

```
transit-1#show flowspec ipv4 nlri 
AFI: IPv4
  NLRI (hex)     :0x01200A326464038106059104D2
    Actions      :Traffic-rate: 0 bps  (bgp.1)
```

![NLRI Hex](/img/2020-11-22-interacting-with-exabgp-flowspec-cli/bgp_flowspec_nlri_hex.JPG)

#### Updating BGP Flowspec rules dynamically

With a bit of tweaking, you can pull this [Github repo](https://github.com/BSpendlove/flowspec-v4-example) and start running an ExaBGP flowspec lab in EVE-NG/GNS3/CML. I have created a simple python flask application that will write the command to stdin and return any results that may be returned from exabgpcli (such as bad formatting of cli command). However the flowspec rule will never be withdrawn from the network unless you manually withdraw the route via the exabgpcli or if the peering session is torn down. Now we need to think about being able to automate the process of an API that interacts with ExaBGP and automatically announces/withdraws these flowspec rules, we need a way to be able to obtain information about the flow and create policies that match a certain critera. Eg. after 1Gbps of traffic within a minute period towards TCP port 1234, we want to be able to push the flowspec rule to drop this traffic or potentially redirect it to another VRF which will further perform inspection/analysis and determine if this is legitimate traffic.

There was a hint in the above paragraph since if we would like to create policies based on traffic flows to specific destinations and gather details such as specific destination/source ports, we need to use some monitoring/traffic analytics which monitors the network flow through the transit routers interfaces. A great example would be NetFlow. Netflow can collect flow patterns and describe parameters of a flow such as the source/destination IP, type of traffic and rate of traffic.

![Policy Server](/img/2020-11-22-interacting-with-exabgp-flowspec-cli/bgp_flowspec_policy_server.JPG)

The idea of the policy server is to implement policies based on the requirements of the service provider. This application can be apart of the Netflow collector and act upon thresholds that are configured in a user-defined policy which allows the flowspec rules to be automatically sent to ExaBGP if eg. TCP/UDP Traffic to port 80 has exceeded 2Gbps over 30 seconds. Creating the application with user-defined policies in mind gives them more flexibility instead of hardcoding pre-defined policies that can't be tweaked since every service provider is different. The policy server will interact with the ExaBGP CLI api and correctly format the syntax of the command required to match that specific policy. A slight problem is that the ExaBGP CLI api doesn't actually expose a HTTP/Rest API and purely depends on stdin commands which introduces a problem for those who are just learning to code, modelling the cli format so that when you build a policy, the correct CLI command is sent. Here is an example of the CLI command entered in the simple flask API to push a flowspec rule that matches a specific destination + port and drops the traffic.

```json
{
    "neighbor": "10.255.255.1",
    "command": "announce flow route { match { destination 10.50.100.100/32; destination-port 1234; protocol tcp; } then { discard; } }"
}
```

The flask application will append these two key values and create the full command below:

```
exabgpcli neighbor 10.255.255.1 'announce flow route { match { destination 10.50.100.100/32; destination-port 1234; protocol tcp; } then { discard; } }'
```

To withdraw the flowspec rule:
```
exabgpcli neighbor 10.255.255.1 'withdraw flow route { match { destination 10.50.100.100/32; destination-port 1234; protocol tcp; } then { discard; } }'
```

While I haven't implemented the policy server part of this project yet, it would be interesting to see how you can ingest netflow data and perform actions based on the flow policies and how to ensure speed in your code when matching netflow data against configured policies. Here is a rough example of how I would approach this type of project:

![Project idea](/img/2020-11-22-interacting-with-exabgp-flowspec-cli/flowspec_policy_server_poc.JPG)

The collector would store NetFlow data in a database so a separate worker application can poll the data and proceed to run through the policies configured (which can also be stored in the database). If any traffic patterns are exceeding a threshold configured for a specific policy, it can proceed to generate the flowspec rule if configured in the policy. The configuration on ExaBGP side could simply be a redundant pair of flowspec route reflectors which the application will push the rule out to both neighbors because either the worker or a separate process can be responsible for the actual BGP sessions.

I would like to expand on this blog or create a new blog post in the future if I ever get time to work on a policy server however it seems that ExaBGP may get a new API in the next major version which will solve the CLI syntax issues that could arise in code without having to create your own encoder that takes a policy and formats it to a exabgpcli command. If they rework their API, I might actually stop being lazy and make a start on this project. You can view [ExaBGP](https://github.com/Exa-Networks/exabgp) (created by [Exa-Networks](https://github.com/Exa-Networks))