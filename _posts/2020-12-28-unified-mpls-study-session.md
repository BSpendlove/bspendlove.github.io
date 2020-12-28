---
layout: post
title: Unified MPLS Study Session
subtitle: CCNP/CCIE Service Provider Exam (v5) - Study with me
comments: true
---

### SPCOR (350-501) objective 3.1.d Unified MPLS

Unified MPLS helps with large scale MPLS deployments by tweaking a few knobs and specifically configuring parts of the network in a certain way which is considered more 'scalable' compared to running a single IGP domain, everyone sharing MPLS labels whether it be LDP/RSVP/Segment Routing. Let's first look at an issue introduced when we start breaking out the network into multiple smaller IGP domains. Take a look at this topology:

![Base Topology](/img/2020-12-28-unified-mpls-study-session/base-topology.JPG)

Note: ABR term is typically only used in OSPF (ABR vs ASBR etc...) however an Area Border Router (ABR) also determines the border of one IGP domain to another when talking about Unified MPLS (whether it be a different ISIS level or OSPF process).

The easiest scenario we can present here is a classic MPLS L3VPN. BGP VPNv4 SAFI is responsible for exchanging VPNv4 routes between PEs (PE1/PE2 and PE3/PE4 in our case) along with a service label tied to that prefix and also a transport label typically derived from the loopback address of the PE router associated with the customers VRF. The service label isn't typically exposed to the network until the last hop with a default configuration, where the last P router will perform the PHP (Penultimate Hop Popping) process and expose the service label before sending traffic to the intended PE.

![PHP Example](/img/2020-12-28-unified-mpls-study-session/php-example-l3vpn.JPG)

In a unified MPLS architecture, we chop up our IGP domains into smaller domains since the IGP itself isn't very scalable when you start pumping 100k+ routes (eg. 50k routers advertising their loopback addresses with a minimum of 2 links for redundancy). The whole chopping up IGP isn't a unified MPLS thing since we are able to scale the IGP by configuring OSPF multi-area, IS-IS multi-area/level, enabling prefix-suppression, summarization and OSPF stub areas. When we start trying to implement MPLS solutions across different inter-domain IGPs, you start to introduce a problem with end to end LSPs and therefore not having full reachability between 2 PEs in different IGP domains.

![Inter-domain Topology Example](/img/2020-12-28-unified-mpls-study-session/inter-domain-example.JPG)

If we are running a different routing process or segregating the IGP domains via IS-IS levels, couldn't we just redistribute the PE loopback addresses so we have reachability/a complete LSP? In this case we could certainly do that however, we are talking about tens/hundreds of thousands of prefixes that may need redistributing and we are back to step 1 in terms of scalability, not to mention that with things like Segment Routing, redistribution from 2 different routing processes is horrible and will cause the router performing redistribution to rewrite the link state information (OSPF LSA, IS-IS LSP) which causes bad label information across the network.

BGP Labelled-Unicast (LU) can be introduced to propagate labels between IGP domains which is considered much more scalable than a single massive IGP domain or performing manual redistribution/IS-IS multi-level propagation. If we introduce this concept in our basic end to end goal (previous picture), it'll look something like this (ABR is a RR in this example):

![BGP-LU Basic Example](/img/2020-12-28-unified-mpls-study-session/bgp-lu-inter-domain.JPG)

The problem that we encounter in this scenario is that how BGP works. When a prefix is advertised into BGP, a specific attribute is also included which is mandatory and is always used during the best path selection and route recursion lookup. If you haven't guessed already it's the NEXT_HOP attribute. In our L3VPN scenario, the PE that originates the VPNv4 route will by default set the NEXT_HOP attribute for the VPNv4 routes to itself (address that is used to peer with the neighbor the update is being sent to). I haven't mentioned it yet, but in a unified MPLS scenario, we would  advertise the PE loopback into BGP for reachability, BGP is much more scalable than an IGP in terms of number of routes. We currently don't have reachability from PE1s loopback address to PE3 loopback address so therefore the BGP route advertised between ABRs and the core RRs are considered invalid because we are not able to perform the recursion lookup on the NEXT_HOP.

![Unified MPLS Unreachable NEXT_HOP BGP Prefix](/img/2020-12-28-unified-mpls-study-session/unified-mpls-next-hop-unreachable.JPG)

iBGP will never modify the NEXT_HOP attribute and is designed this way however a solution to this problem is to change the NEXT_HOP on the ABR by enforcing ibgp modifications using this command:

```
ibgp policy out enforce-modifications
```

If we were to now modify our neighbor statement from the RR (ABR) to PE1 and PE2 to set the next-hop-self for the labeled-unicast SAFI, we will see that the NEXT_HOP attribute will actually be modified. Let's jump back to our original topology and quickly confirm everything we've talked about so far, look at some routing tables and then start advertising labels/loopbacks via BGP.

### PE1 reachability example to PE3

Refer to the base topology (first topology) where PE1 is in IS-IS area 49.0003 and PE3 is in IS-IS area 49.0002. There is no route leaking between the IS-IS areas/levels however I have enabled the loopbacks on each ABR to use both level 1 and level 2. It is much cleaner to have the loopback of the ABR in boths levels vs configuring it only in level 2 (facing the core) and leak it into level 1.

```
route-policy DROP-ALL
  drop
end-policy
!
router isis 1
 address-family ipv4 unicast
  propagate level 1 into level 2 route-policy DROP-ALL
```

IS-IS level 1 by default will propagate prefixes into level 2 so create a DROP-ALL policy to override the default behaviour. The reason why you would want to approach an IS-IS design with multi-level architecture instead of performing redistribution between 2 IS-IS routing processes is to avoid any issues that could occur when you have something like Segment Routing. Loopback addresses will typically have a prefix-sid (label) associated to them and this will not propagate correctly between 2 different routing processes, however it works seamlessly with level 2 to level 1 propagation but as previously mentioned, it's cleaner to just make the loopback in both levels.

Let's take a look at PE1 routing table:
```
C    10.0.15.0/24 is directly connected, 04:25:02, GigabitEthernet0/0/0/0
L    10.0.15.1/32 is directly connected, 04:25:02, GigabitEthernet0/0/0/0
C    10.0.16.0/24 is directly connected, 04:25:02, GigabitEthernet0/0/0/1
L    10.0.16.1/32 is directly connected, 04:25:02, GigabitEthernet0/0/0/1
i L1 10.0.25.0/24 [115/20000] via 10.0.15.5, 03:32:07, GigabitEthernet0/0/0/0
i L1 10.0.26.0/24 [115/20000] via 10.0.16.6, 03:32:04, GigabitEthernet0/0/0/1
L    10.255.255.1/32 is directly connected, 04:25:02, Loopback0
i L1 10.255.255.2/32 [115/20000] via 10.0.15.5, 03:31:55, GigabitEthernet0/0/0/0
                     [115/20000] via 10.0.16.6, 03:31:55, GigabitEthernet0/0/0/1
i L1 10.255.255.5/32 [115/10000] via 10.0.15.5, 03:34:26, GigabitEthernet0/0/0/0
i L1 10.255.255.6/32 [115/10000] via 10.0.16.6, 03:32:04, GigabitEthernet0/0/0/1
```

As previously mentioned, we advertise the loopback addresses from our PEs into BGP which should solve the whole reachability problem since we don't want to redistribute them into the IGPs. Now we run into the NEXT_HOP issue, this example is from the cores perspective (RR13 and RR14) which don't end up reflecting the BGP-LU update to the relevant ABR5/ABR6 because they also can't resolve the NEXT_HOP.

```
RP/0/0/CPU0:RR13#show bgp ipv4 labeled-unicast | begin Network
Mon Dec 28 05:19:47.716 UTC
   Network            Next Hop            Metric LocPrf Weight Path
* i10.255.255.1/32    10.255.255.1             0    100      0 i
* i                   10.255.255.1             0    100      0 i
* i10.255.255.2/32    10.255.255.2             0    100      0 i
* i                   10.255.255.2             0    100      0 i
* i10.255.255.3/32    10.255.255.3             0    100      0 i
* i                   10.255.255.3             0    100      0 i
* i10.255.255.4/32    10.255.255.4             0    100      0 i
* i                   10.255.255.4             0    100      0 i
*>i10.255.255.5/32    10.255.255.5             0    100      0 i
* i                   10.255.255.5             0    100      0 i
*>i10.255.255.6/32    10.255.255.6             0    100      0 i
* i                   10.255.255.6             0    100      0 i
*>i10.255.255.7/32    10.255.255.7             0    100      0 i
* i                   10.255.255.7             0    100      0 i
*>i10.255.255.8/32    10.255.255.8             0    100      0 i
* i                   10.255.255.8             0    100      0 i

RP/0/0/CPU0:RR13#show bgp ipv4 labeled-unicast 10.255.255.3 | include from
Mon Dec 28 05:20:29.513 UTC
  Local, (Received from a RR-client)
    10.255.255.3 (inaccessible) from 10.255.255.7 (10.255.255.3)
  Local, (Received from a RR-client)
    10.255.255.3 (inaccessible) from 10.255.255.8 (10.255.255.3)
```

### Why does next-hop-self and ibgp policy out enforce-modifications fix this?

```
RP/0/0/CPU0:RR13#show bgp ipv4 labeled-unicast | begin Network            
Mon Dec 28 05:24:46.386 UTC
   Network            Next Hop            Metric LocPrf Weight Path
*>i10.255.255.1/32    10.255.255.5             0    100      0 i
* i                   10.255.255.6             0    100      0 i
* i                   10.255.255.5             0    100      0 i
*>i10.255.255.2/32    10.255.255.5             0    100      0 i
* i                   10.255.255.6             0    100      0 i
* i                   10.255.255.5             0    100      0 i
*>i10.255.255.3/32    10.255.255.7             0    100      0 i
* i                   10.255.255.8             0    100      0 i
* i                   10.255.255.7             0    100      0 i
*>i10.255.255.4/32    10.255.255.7             0    100      0 i
* i                   10.255.255.8             0    100      0 i
* i                   10.255.255.7             0    100      0 i
*>i10.255.255.5/32    10.255.255.5             0    100      0 i
* i                   10.255.255.5             0    100      0 i
*>i10.255.255.6/32    10.255.255.6             0    100      0 i
* i                   10.255.255.6             0    100      0 i
*>i10.255.255.7/32    10.255.255.7             0    100      0 i
* i                   10.255.255.7             0    100      0 i
*>i10.255.255.8/32    10.255.255.8             0    100      0 i
* i                   10.255.255.8             0    100      0 i
```

The specific route we are concerned about is 10.255.255.3. We've changed the neighbor configuration on both ABR7 and ABR8 to allow ibgp modifications and set the `next-hop-self` towards the core RRs and also this is required for the neighbor configuration facing the PEs. PE1 is still unable to resolve ABR7 or ABR8s loopback address so this will still cause a problem in terms of reachability.

```
RP/0/0/CPU0:PE1#show bgp ipv4 labeled-unicast 10.255.255.3/32
BGP routing table entry for 10.255.255.3/32
Versions:
  Process           bRIB/RIB  SendTblVer
  Speaker                 33          33
    Local Label: 24008
Last Modified: Dec 28 15:51:59.742 for 00:05:42
Paths: (2 available, best #1)
  Not advertised to any peer
  Path #1: Received by speaker 0
  Not advertised to any peer
  Local
    10.255.255.5 (metric 10000) from 10.255.255.5 (10.255.255.3)
      Received Label 24011 
      Origin IGP, metric 0, localpref 100, valid, internal, best, group-best, labeled-unicast
      Received Path ID 0, Local Path ID 0, version 33
      Originator: 10.255.255.3, Cluster list: 10.255.255.5, 10.255.255.13, 10.255.255.7
  Path #2: Received by speaker 0
  Not advertised to any peer
  Local
    10.255.255.6 (metric 10000) from 10.255.255.6 (10.255.255.3)
      Received Label 24013 
      Origin IGP, metric 0, localpref 100, valid, internal, labeled-unicast
      Received Path ID 0, Local Path ID 0, version 0
      Originator: 10.255.255.3, Cluster list: 10.255.255.6, 10.255.255.13, 10.255.255.7
```

The key important part right now is the MPLS label stack, what has happened when we've modified the next-hop self in many different places? Here is a simplified version of the base topology, focusing on the connectivity only between PE1 to PE3.

![PE1 to PE3 simplified topology](/img/2020-12-28-unified-mpls-study-session/pe1-to-pe3-simplified.JPG)

Remember that RR13 in our case is simply a route reflector.

![PE3 NHS](/img/2020-12-28-unified-mpls-study-session/pe3-nhs.JPG)

How ABR7 sees the BGP Update
```
RP/0/0/CPU0:ABR7#show bgp ipv4 labeled-unicast | include 10.255.255.3/32
*>i10.255.255.3/32    10.255.255.3             0    100      0 i
```

How ABR5 sees the BGP Update
```
RP/0/0/CPU0:ABR5#show bgp ipv4 labeled-unicast | include 10.255.255.3/32
*>i10.255.255.3/32    10.255.255.7             0    100      0 i
```

How PE1 sees the BGP Update
```
RP/0/0/CPU0:PE1#show bgp ipv4 labeled-unicast | include 10.255.255.3/32
*>i10.255.255.3/32    10.255.255.5             0    100      0 i
```

You can see that the NEXT_HOP attribute has changed along the path but how does this fix the reachability issue? PE1 can reach ABR5 (10.255.255.5) already via its local IGP using LDP. This is where the fun begins, the MPLS label stack is now extremely important to ensure end to end connectivty for the LSP. Along with a service label (not present in this current example), we will see 2 other labels in most cases. PE1 is actually informed of an implict null action due to it only being 1 hop away from ABR5 but let's assume PE1 is a few routers away from ABR5.

You'll see an MPLS label stack similar to this:

![PE1 to PE3 Label Stack Example](/img/2020-12-28-unified-mpls-study-session/unified-mpls-label-stack-example.JPG)

ABR5 24011 Label
```
RP/0/0/CPU0:ABR5#show mpls forwarding labels 24011
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes       
Label  Label       or ID              Interface                    Switched    
------ ----------- ------------------ ------------ --------------- ------------
24011  24011       10.255.255.3/32                 10.255.255.7    520             
```

I've ran into a few issues with XRv and MPLS labels not being installed properly (with the use of BGP-LU) with Segment Routing however it works perfectly fine using LDP/RSVP. This is a known bug where the BGP-LU label is already assosicated with an sr-adj and is unable to fix itself (states that there is already a label assigned, even if it's not within the SRGB range) so just a note, this lab was using purely LDP across each IGP domain.

The underlying service label will not change end to end. Other labels are specifically used to identify how to reach the remote PE/other IGP domain. For troubleshooting purposes, you can typically send the segment routing SID in the BGP-LU update if you're using SR so that new labels are not generated.

Let's demonstrate this with a service label (eg. CPE1-1 and CPE1-2 in a VRF).

PE1 VRF CEF Recursion
```
RP/0/0/CPU0:PE1#show cef vrf CUS-A 10.0.0.4/30 detail
10.0.0.4/30, version 4, internal 0x5000001 0x0 (ptr 0xa12d430c) [1], 0x0 (0x0), 0x208 (0xa155b208)
 Updated Dec 28 16:25:26.803
 Prefix Len 30, traffic index 0, precedence n/a, priority 3
  gateway array (0xa121dd34) reference count 1, flags 0x2038, source rib (7), 0 backups
                [1 type 1 flags 0x48441 (0xa1575320) ext 0x0 (0x0)]
  LW-LDI[type=0, refc=0, ptr=0x0, sh-ldi=0x0]
  gateway array update type-time 1 Dec 28 16:25:26.803
 LDI Update time Dec 28 16:25:26.803
   via 10.255.255.3/32, 3 dependencies, recursive [flags 0x6000]
    path-idx 0 NHID 0x0 [0xa15c353c 0x0]
    recursion-via-/32
    next hop VRF - 'default', table - 0xe0000000
    next hop 10.255.255.3/32 via 24008/0/21
     next hop 10.0.15.5/32 Gi0/0/0/0    labels imposed {ImplNull 24011 24000}


    Load distribution: 0 (refcount 1)

    Hash  OK  Interface                 Address
    0     Y   Unknown                   24008/0  
```

ABR5
```
RP/0/0/CPU0:ABR5#show mpls forwarding labels 24011
Mon Dec 28 16:41:41.676 UTC
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes       
Label  Label       or ID              Interface                    Switched    
------ ----------- ------------------ ------------ --------------- ------------
24011  24011       10.255.255.3/32                 10.255.255.7    1080   
```

ABR7
```
RP/0/0/CPU0:ABR7#show mpls forwarding labels 24011
Mon Dec 28 16:42:02.264 UTC
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes       
Label  Label       or ID              Interface                    Switched    
------ ----------- ------------------ ------------ --------------- ------------
24011  Pop         10.255.255.3/32    Gi0/0/0/3    10.0.37.3       18260    
```

The diagram below demonstrates the end to end LSP and label stack what it would look like (if we didn't have the PE 1 hop away from the ABRs, eg. Label X):

![PE1 to PE3 End to End LSP](/img/2020-12-28-unified-mpls-study-session/unified-mpls-end-to-end-lsp.JPG)

Label X and Y are labels that allow traffic to traverse the NEXT_HOP recursion to the respective ABR whom has the ibgp enforce modifications enabled. Label 24011 (PE3) is the label learned via BGP-LU that allows us to specifcally reach PE3 in the other IGP domain, remember that we are able to reach it because of the modified NEXT_HOP attribute on the ABR so the BGP route is a valid route and is installed into the RIB/CEF.

Label 24000 (VRF-A) is an end to end label that was assosicated with VRF-A in the VPNv4 updates. The next hop does not need to be set for these routes since we are able to successfully perform a recursive lookup on the NEXT_HOP which will be the loopback address of the PE router (which we have learned via a combination of BGP-LU and next-hop-self).

```
RP/0/0/CPU0:PE1#show bgp vpnv4 unicast rd 10.255.255.3:101 10.0.0.4/30 detail | include "Label|Originator"
Mon Dec 28 16:48:43.807 UTC
      Received Label 24000 
      Originator: 10.255.255.3, Cluster list: 10.255.255.5, 10.255.255.13, 10.255.255.7
```

We have an end-to-end fully functional LSP:
```
RP/0/0/CPU0:PE1#sh run int g0/0/0/2
Mon Dec 28 16:50:03.381 UTC
interface GigabitEthernet0/0/0/2
 vrf CUS-A
 ipv4 address 10.0.0.1 255.255.255.252
!
RP/0/0/CPU0:PE1#traceroute vrf CUS-A 10.0.0.5 source g0/0/0/2
Mon Dec 28 16:49:30.613 UTC

Type escape sequence to abort.
Tracing the route to 10.0.0.5

 1  10.0.15.5 [MPLS: Labels 24011/24000 Exp 0] 29 msec  19 msec  19 msec
 2  10.0.59.9 [MPLS: Labels 24010/24011/24000 Exp 0] 39 msec  19 msec  19 msec 
 3  10.0.149.14 [MPLS: Labels 24017/24011/24000 Exp 0] 29 msec  19 msec  19 msec 
 4  10.0.114.11 [MPLS: Labels 24008/24011/24000 Exp 0] 29 msec  19 msec  19 msec 
 5  10.0.117.7 [MPLS: Labels 24011/24000 Exp 0] 29 msec  19 msec  19 msec 
```

Diagrams may include more labels than presented in the traceroute/show command output but that is only to demonstrate a scenario where the PE isn't always 1 hop away from the ABR and doesn't need to push an MPLS label so that transport will work in the local MPLS/IGP domain. Remember that the bottom most label will typically reference the service/VRF and on a default Cisco configuration, this label is exposed 1 hop away from the intended destination due to PHP. The top most label is typically used only for transport within the local IGP/MPLS domain (unless it is popped and exposes the next label which will allow reachability to the remote PE).

Thank you for taking the time to read this short post and please feel free to leave a comment if you have found this post interesting or useful. Some very useful resources that I've found helpful during my studies are: 

1) ![Configure Unified MPLS in Cisco IOS XR](https://www.cisco.com/c/en/us/support/docs/multiprotocol-label-switching-mpls/multiprotocol-label-switching-mpls/119191-config-unified-mpls-00.html)
2) ![MPLS in the SDN Era](https://www.oreilly.com/library/view/mpls-in-the/9781491905449/)
3) ![Unified MPLS Functionality, Features, and Configuration Example](https://www.cisco.com/c/en/us/support/docs/multiprotocol-label-switching-mpls/mpls/118846-config-mpls-00.html)