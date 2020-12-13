---
layout: post
title: L3VPNs - Route Target Constraint (RTC)
subtitle: IOS-XR L3VPN quick tips 
comments: true
---

I'll be trying a new approach instead of writing a full detailed blog, each subject that I am going through will be recorded here on my blog without going into too much detail but I will provide screenshots of pcaps/highlight the important areas of the packet that I am talking about. In this blog, we discuss L3VPN scalability at the access sites in terms of thousands of VPN customers.

Here is the topology for the majority of labs in the L3VPN subsection of my quick tips:

![Base Topology](/img/2020-12-13-l3vpn-route-target-constraint/topology.JPG)

Addressing scheme for this lab:

#### P2Ps

IPv4: 10.0.X.Y/24 - Where X = routers on the link, Y = router number (eg. C-3 to C-4 = 10.0.34.3/24)
IPv6: fc00:XXXX::Y/64 - Where X = routers on the link, Y = router number (eg. C-5 to PE-7 = fc00:57::5/64)

#### Loopbacks

10.255.255.X/32 - Where X = router number (eg. PE-10 = 10.255.255.10/32)
fc00:FFFF::X/128 - Where X = router number (eg. RR-2 = fc00:FFFF::2/128)

#### PE to CPE (VRF)

Typically /30s advertised into relevant customers VRF

#### Route Targets and Route Distinguisher

CUS-A (CPE1-1 and CPE1-2) = X.X.X.X:101 - Where X.X.X.X = PE loopback (eg. PE-7 CUS-A VRF = 10.255.255.7:101)
CUS-B (CPE2-1 and CPE2-2) = X.X.X.X:102 - Where X.X.X.X = PE loopback (eg. PE-10 CUS-B VRF = 10.255.255.10:102)


### What is the problem?

As you scale the network to support a larger amount of VPN customers, you need to consider the fact that BGP tables will begin to get so large that your router might start to struggle. If you are pushing full BGP tables of 700/800+k to your access network, you need to also remember that the more customers you support in the L3VPN, your BGP tables grow even further because each customer might be sending 10,000+ or 100,000+ routes to their remote L3VPN sites. You are now supporting 1/2+ million BGP routes because of the BGP global unicast routes but also your customers L3VPN unicast routes.

Let's take a look at the VPNv4 routes on PE-9:

```
RP/0/0/CPU0:PE-9#show bgp vpnv4 unicast | begin Network
Sun Dec 13 13:51:08.279 UTC
   Network            Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 10.255.255.7:101
*>i10.0.0.0/30        10.255.255.7             0    100      0 i
* i                   10.255.255.7             0    100      0 i
*>i10.64.0.0/16       10.255.255.7             0    100      0 i
* i                   10.255.255.7             0    100      0 i
Route Distinguisher: 10.255.255.7:102
*>i10.0.0.0/30        10.255.255.7             0    100      0 i
* i                   10.255.255.7             0    100      0 i
*>i10.64.0.0/16       10.255.255.7             0    100      0 i
* i                   10.255.255.7             0    100      0 i
Route Distinguisher: 10.255.255.8:101
*>i10.0.0.4/30        10.255.255.8             0    100      0 i
* i                   10.255.255.8             0    100      0 i
*>i10.64.0.0/16       10.255.255.8             0    100      0 i
* i                   10.255.255.8             0    100      0 i
Route Distinguisher: 10.255.255.8:102
*>i10.0.0.4/30        10.255.255.8             0    100      0 i
* i                   10.255.255.8             0    100      0 i
*>i10.64.0.0/16       10.255.255.8             0    100      0 i
* i                   10.255.255.8             0    100      0 i
Route Distinguisher: 10.255.255.9:101 (default for vrf CUS-A)
*>i10.0.0.0/30        10.255.255.7             0    100      0 i
*>i10.0.0.4/30        10.255.255.8             0    100      0 i
*> 10.0.0.8/30        0.0.0.0                  0         32768 i
*>i10.64.0.0/16       10.255.255.7             0    100      0 i
* i                   10.255.255.8             0    100      0 i
*>i10.65.0.0/16       10.0.0.10                0    100      0 i
Route Distinguisher: 10.255.255.9:102 (default for vrf CUS-B)
*>i10.0.0.0/30        10.255.255.7             0    100      0 i
*>i10.0.0.4/30        10.255.255.8             0    100      0 i
*> 10.0.0.8/30        0.0.0.0                  0         32768 i
*>i10.64.0.0/16       10.255.255.7             0    100      0 i
* i                   10.255.255.8             0    100      0 i
*>i10.65.0.0/16       10.0.0.10                0    100      0 i
```

Don't focus too much on the L3VPN setup itself (eg. RDs, routes, RRs, redundancy, MED/Local Pref). However do imagine that there are much more routes coming from each customers CPE (or that there are many more sites per customer). This example will show you the problem on a small scale (which isn't actually an issue until you scale into thousands of VPN customers, each customer having hundreds/thousands of remote offices/sites).

If we create a new VPN customer on PE-8 called: CUS-C and create the route-target as 10.255.255.8:103. This is a new customer who plans on connecting a site to our PE-10 router in a few weeks time (physically in another PoP in this scenario). This customer also doesn't require any redundancy so will be connected to a single PE.

```
vrf CUS-C
 address-family ipv4 unicast
  export route-target
   10.255.255.8:103

router bgp 65501
 vrf CUS-C
  rd 10.255.255.8:103
  address-family ipv4 unicast
   network 10.0.0.0/30
```

PE-8 now sends this in an UPDATE to it's route reflectors (RR-1 and RR-2) as expected:

![PE-8 CUS-C Advertised](/img/2020-12-13-l3vpn-route-target-constraint/cus-c-sent-to-rr.JPG)

The RR's will now reflect this the clients and PE-9 receives this update (along with all the other PE routers) however, customer "CUS-C" (aka 10.255.255.8:103) is not being imported, therefore the BGP UPDATE is silently discarded as shown here in the BGP vpnv4 debug output:

```
! Update from RR-2
RP/0/0/CPU0:PE-9#RP/0/0/CPU0:Dec 13 14:18:55.365 : bgp[1051]: [default-rtr]: UPDATE from 10.255.255.2 contains nh 10.255.255.8/32, gw_afi 0, flags 0x0, nlri_afi 4
RP/0/0/CPU0:Dec 13 14:18:55.365 : bgp[1051]: [default-rtr]: NH-Validate-Create: addr=10.255.255.8/32, len=12, nlriafi=4, nbr=10.255.255.2, gwafi=0, gwlen=4, gwaddrlen=32::: nhout=0x12638804, validity=1, attrwdrflags=0x00000000
RP/0/0/CPU0:Dec 13 14:18:55.365 : bgp[1051]: [default-rtr]: --bgp4_rcv_attributes--: END: nbr=10.255.255.2:: msg=0x12045bbc/106, updlen=87, attrbl=0x12045bd3/83, ipv4reachlen=0, msginpath=0x3ccebf0, asloopcheck=1, attrwdrfl=0x00000000:: samecluster=0, local_as_prepended=0, attr_wdr_flags 0x00000000, myascount=0:: rcvdata=0x12045c26/0, errptr=0x12045c1f/7
RP/0/0/CPU0:Dec 13 14:18:55.365 : bgp[1051]: [default-rtr] (vpn4u): Received UPDATE from 10.255.255.2 with attributes: 
RP/0/0/CPU0:Dec 13 14:18:55.365 : bgp[1051]: [default-rtr] (vpn4u): nexthop 10.255.255.8/32, origin i, localpref 100, metric 0, originator 10.255.255.8, clusterlist 2.0.0.0, extended community RT:10.255.255.8:103 
RP/0/0/CPU0:Dec 13 14:18:55.365 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.8:103:10.0.0.0/30 (path ID: none) with MPLS label 24008  from neighbor 10.255.255.2
RP/0/0/CPU0:Dec 13 14:18:55.365 : bgp[1051]: [default-rtr] (vpn4u): Prefix v4Addr:10.255.255.8:103:10.0.0.0/30 (path ID: none) received from 10.255.255.2 DENIED RT extended community is not imported locally

! Uppdate from RR-1
RP/0/0/CPU0:Dec 13 14:18:55.365 : bgp[1051]: [default-rtr]: UPDATE from 10.255.255.1 contains nh 10.255.255.8/32, gw_afi 0, flags 0x0, nlri_afi 4
RP/0/0/CPU0:Dec 13 14:18:55.365 : bgp[1051]: [default-rtr]: NH-Validate-Create: addr=10.255.255.8/32, len=12, nlriafi=4, nbr=10.255.255.1, gwafi=0, gwlen=4, gwaddrlen=32::: nhout=0x12638804, validity=1, attrwdrflags=0x00000000
RP/0/0/CPU0:Dec 13 14:18:55.365 : bgp[1051]: [default-rtr]: --bgp4_rcv_attributes--: END: nbr=10.255.255.1:: msg=0x1204588c/106, updlen=87, attrbl=0x120458a3/83, ipv4reachlen=0, msginpath=0x3ccebf0, asloopcheck=1, attrwdrfl=0x00000000:: samecluster=0, local_as_prepended=0, attr_wdr_flags 0x00000000, myascount=0:: rcvdata=0x120458f6/0, errptr=0x120458ef/7
RP/0/0/CPU0:Dec 13 14:18:55.365 : bgp[1051]: [default-rtr] (vpn4u): Received UPDATE from 10.255.255.1 with attributes: 
RP/0/0/CPU0:Dec 13 14:18:55.365 : bgp[1051]: [default-rtr] (vpn4u): nexthop 10.255.255.8/32, origin i, localpref 100, metric 0, originator 10.255.255.8, clusterlist 1.0.0.0, extended community RT:10.255.255.8:103 
RP/0/0/CPU0:Dec 13 14:18:55.365 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.8:103:10.0.0.0/30 (path ID: none) with MPLS label 24008  from neighbor 10.255.255.1
RP/0/0/CPU0:Dec 13 14:18:55.365 : bgp[1051]: [default-rtr] (vpn4u): Prefix v4Addr:10.255.255.8:103:10.0.0.0/30 (path ID: none) received from 10.255.255.1 DENIED RT extended community is not imported locally
```

Noticed this specific output `DENIED RT extended community is not imported locally`. This doesn't seem to be a big problem (or even that much of a problem since it doesn't take much resources to deny a BGP UPDATE), consider this scenario, you have 300 VPN customers and each customer has around 3000 routes in their BGP table. That's 900,000 total VPNv4 routes sent when a PE router is rebooted (even if the PE router only connects 2 of those 300 VPN customers). What if we had 1000 customers where each customer had around 4000-5000 routes per customer? There is one thing we haven't looked at, what happens when a new VRF/customer is introduced on PE-8? I showed the configuration previously but what actually happens when you configure a new VRF and set the RT/BGP configuration? We have a new customer called CUS-D (which I will put looback 104) and configure my export/import policies on the VRF (no BGP configuration).

```
vrf CUS-D
 address-family ipv4 unicast
  import route-target
   10.255.255.10:104
  export route-target
   10.255.255.8:104
```

When we configure an import policy or import a route-target on a VRF, we send a BGP ROUTE-REFRESH which specifically tells our route reflectors that we would like to refresh our BGP table for the SAFI: VPNv4 (128) as shown here:

![PE-8 Route Refresh RR1](/img/2020-12-13-l3vpn-route-target-constraint/pe-8-route-refresh-rr1.JPG)

![PE-8 Route Refresh RR2](/img/2020-12-13-l3vpn-route-target-constraint/pe-8-route-refresh-rr2.JPG)

RR-1 and RR-2 will send a complete refresh of the VPNv4 routes (all customers, 101, 102, 103 and 104), this is expected and makes sense since we have these 4 VRFs configured on PE-8. What if we introduce one last customer (CUS-E CPE5-1 105) on PE-7? Remeber that PE-7 does not have CUS-C or CUS-D VRFs, nor will it have any VPNv4 routes for these customers because we also don't have any import policies configured for 10.255.255.8:103 or 10.255.255.8:104.

![PE-7 CPE5-1](/img/2020-12-13-l3vpn-route-target-constraint/cpe5-1-new-customer.JPG)

```
vrf CUS-E
 address-family ipv4 unicast
  import route-target
   10.255.255.10:105 ! CUS-E will also have another site connected to PE-10 so we preconfigure the import policy
  export route-target
   10.255.255.7:105
```

As shown in the previous packet capture, PE-7 will now send a ROUTE-REFRESH message to both RR-1 and RR-2. Here you can see RR-1 sending multiple BGP UPDATEs as a result of the route refresh request.

![PE-7 RR-1 Route Refresh](/img/2020-12-13-l3vpn-route-target-constraint/pe-7-cus-d-route-refresh.JPG)

I've highlighted in red to show the obvious fields:

- RR1 (10.255.255.1) sending BGP UPDATE messages to PE-7 (10.255.255.7)
- RD 10.255.255.8:103 (CUS-C routes) are being sent but these are being discarded which will look similar to the debug output shown above.
- Note that this same refresh has also been sent to RR-2 and because you would typically configure redundant RRs for VPNv4 (whether they are also IPv4 unicast RRs or separate RRs for your VPN services), you'd receive the same updates twice (1 for RR-1 and 1 from RR-2)

Going back to our imagination, can you see the problem arise if stop thinking about 10-20 VPNv4 routes and 4 VPN customers and talk about a real scenario where we have 1000+ VPN customers all with thousands of routes per customer? This is where we start to talk aout RTC (Route Target Constraint) and laugh how I'll come to a conclusion within the next 30 seconds for the end of this blog.

Configuring this requires us to simply add an address-family called "Route Target Filter".
```
!RR Config changes
router bgp 65501
 address-family ipv4 rt-filter

 neighbor-group RR-VPNV4-CLIENTS
  address-family ipv4 rt-filter

!PE-7 Config changes
router bgp 65501
 address-family ipv4 rt-filter

 neighbor 10.255.255.1
  address-family ipv4 rt-filter

 neighbor 10.255.255.2
  address-family ipv4 rt-filter
```

#### What happens behind the scenes?

RR-1 and RR-2 send a BGP UPDATE with AFI (1 = IPv4) and SAFI (132 - Route Target Filter) path attributes which includes a default/wildcard prefix (0.0.0.0/0).

![PE-7 RR-1 Route Refresh](/img/2020-12-13-l3vpn-route-target-constraint/rr-1-rtc-wildcard-pe7.JPG)

The wildcard encoded in the NLRI is just to trigger PE-7 to request which RTs they are interested in receiving routes from. This is determined by the import policies configured under the VRFs along with the BGP VRF RD config which in our case are:

```
RP/0/0/CPU0:PE-7#show run vrf
vrf CUS-A
 address-family ipv4 unicast
  import route-target
   10.255.255.9:101
   10.255.255.10:101

vrf CUS-B
 address-family ipv4 unicast
  import route-target
   10.255.255.9:102
   10.255.255.10:102

vrf CUS-E
 address-family ipv4 unicast
  import route-target
   10.255.255.10:105

rotuer bgp 65501
 vrf CUS-A
  rd 10.255.255.7:101
  address-family ipv4 unicast

 vrf CUS-B
  rd 10.255.255.7:102
  address-family ipv4 unicast

 vrf CUS-E
  rd 10.255.255.7:105
  address-family ipv4 unicast
```

![PE-7 Route Target Filter NLRI](/img/2020-12-13-l3vpn-route-target-constraint/pe-7-route-target-filter-nlri.JPG)

This will now specifically tell RR-1 (and this same message is sent to RR-2) to only send routes that belong to these customers, since these are the only VRFs PE-7 has configured and doesn't care about CUS-C and CUS-D. (in real scenario, this could be the other 997 VPN customers and prevents us being sent 1-2 million VPNv4 routes). There is some additional configuration on the PE side if you are using Juniper, however this works with no additional configuration on IOS-XR due to how BGP will set the next-hop for the BGP NLRI as itself and your RRs may not be running MPLS (which I am running in this lab but it's irrelevant to the whole concept of Route Target Constraint).

If we now take a look at the debug output for any BGP UPDATEs sent from RR-1 to PE-7, we'll find that we don't discard any irrelevant VPNv4 prefixes because we don't actually receive them and we don't waste any resources in terms of bandwidth or CPU cycles for customers that don't belong on this PE in our L3VPN. The only received prefixes are below (noticed none are being denied)

```
RP/0/0/CPU0:Dec 13 15:47:31.080 : bgp[1051]: [default-rtr] (ipv4rtf): Received prefix 0:0:0:0/0 (path ID: none) from 10.255.255.1
RP/0/0/CPU0:Dec 13 15:47:31.110 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.8:101:10.64.0.0/16 (path ID: none) with MPLS label 24006  from neighbor 10.255.255.1
RP/0/0/CPU0:Dec 13 15:47:31.110 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.8:101:10.0.0.4/30 (path ID: none) with MPLS label 24004  from neighbor 10.255.255.1
RP/0/0/CPU0:Dec 13 15:47:31.110 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.10:101:10.65.0.0/16 (path ID: none) with MPLS label 24006  from neighbor 10.255.255.1
RP/0/0/CPU0:Dec 13 15:47:31.110 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.10:101:10.0.0.12/30 (path ID: none) with MPLS label 24004  from neighbor 10.255.255.1
RP/0/0/CPU0:Dec 13 15:47:31.110 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.9:101:10.65.0.0/16 (path ID: none) with MPLS label 24004  from neighbor 10.255.255.1
RP/0/0/CPU0:Dec 13 15:47:31.110 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.9:101:10.0.0.8/30 (path ID: none) with MPLS label 24003  from neighbor 10.255.255.1
RP/0/0/CPU0:Dec 13 15:47:31.110 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.8:102:10.64.0.0/16 (path ID: none) with MPLS label 24007  from neighbor 10.255.255.1
RP/0/0/CPU0:Dec 13 15:47:31.110 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.8:102:10.0.0.4/30 (path ID: none) with MPLS label 24005  from neighbor 10.255.255.1
RP/0/0/CPU0:Dec 13 15:47:31.110 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.10:102:10.65.0.0/16 (path ID: none) with MPLS label 24007  from neighbor 10.255.255.1
RP/0/0/CPU0:Dec 13 15:47:31.110 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.10:102:10.0.0.12/30 (path ID: none) with MPLS label 24005  from neighbor 10.255.255.1
RP/0/0/CPU0:Dec 13 15:47:31.110 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.9:102:10.0.0.8/30 (path ID: none) with MPLS label 24002  from neighbor 10.255.255.1
RP/0/0/CPU0:Dec 13 15:47:31.110 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.9:102:10.65.0.0/16 (path ID: none) with MPLS label 24005  from neighbor 10.255.255.1
RP/0/0/CPU0:Dec 13 15:47:31.110 : bgp[1051]: [default-rtr] (vpn4u): Received prefix v4Addr:10.255.255.8:103:10.0.0.0/30 (path ID: none) with MPLS label 24008  from neighbor 10.255.255.1
```

I hope you have found this post interesting/useful, please feel free to leave any comments or suggestions.