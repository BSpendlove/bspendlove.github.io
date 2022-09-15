---
layout: post
title: EVPN Distributed Anycast Gateway for VM/MAC mobility
subtitle: VM mobility makes life easy
comments: true
---

VM mobility (or MAC mobility, you'll find different names around from various vendors) essentially allows us to move a device connected to a single device to another device within the network without having to perform configuration changes on the device itself, for example take the below topology where we have virtual machines located in different data centers with segmented by layer 3, each VM being in a different layer 3 network along with different gateways configured on the underlying operating system:

![Hosts in multiple DCs with different subnets/gateways](/img/2022-09-15-evpn-distributed-anycast-gateway/poor_mobility.PNG)

Without going into a whole history lesson on why people shouldn't extend layer 2, its 2022 and assuming the reader has a basic understanding on EVPN itself, we essentially carry MAC addresses within BGP using new address families and no longer need to flood the data plane across multiple datacenters and rely heavily on the control plane to program the relevant tables to make the data plane work, we're now technically routing mac addresses using the underlying technologies which in this case we will focus on Segment Routing + EVPN-MPLS (not VxLAN) in this post. Be ready to reprogram your brain because extending layer 2 is perfectly fine as long as you're not literally extending it using VLANs and Spanning Tree Protocol.

If I want to perform maintenance on DC1 and want to move the VM from a hypervisor, you might want to just move it to another hypervisor in the same DC which is within the same layer 2 domain however in this scenario our only option is to move the VM to another DC, however the network details will need to be reconfigured which could also cause issues for other services, maybe there are DNS records pointing to this specific IP? Maybe there is BGP sessions setup with this VM so they will need to be reconfigured? How do we keep the services on the VM running as expected without touching the underlying network configuration when migrating to a different physical host located in another data center?

One easy solution that doesn't require any EVPN magic and is supported on 99% of platforms (within reason) is to just run BGP with every single server which advertises a /32 and use that as the IP address to host services on. When a VM is moved to another data center, the underlying network configuration and some BGP neighbor statements will be required however the /32 IP (or /128 IPv6) addresses tied to the service can move around the network with minimal configuration, however if we still want 0 involvement with the OS configuration we can use distributed anycast gateway. The whole concept of this technology is that you have the VM gateway at each data center, but the MAC address of each device within your EVPN domain will be advertised to other data centers (or PEs, in this case each DC can be considered a PE router).

![EVPN Type 2 Route](/img/2022-09-15-evpn-distributed-anycast-gateway/type_2_advertised.PNG)

If DC1 doesn't already know about the 10.0.0.11 device, typical data plane learning that goes on (eg. DHCP and ARP) will act as normal but then this IP + MAC address can be advertised to other PE routers (in our case, the other 3 data centers) and this is called a Type 2 [which is defined in RFC 7432](https://www.rfc-editor.org/rfc/rfc7432.html#section-7.2) section 7.2. Like a lot of other technologies, BGP is extended yet again to support the advertisement of the MAC addresses which allows the other routers to kind of act like a proxy arp for any devices trying to reach the specific IP, this is explained in the diagram below:

![EVPN PE responds for the ARP locally](/img/2022-09-15-evpn-distributed-anycast-gateway/evpn_proxy.PNG)

Step 1: The Device in DC2 (10.0.0.12) sends out an ARP request for 10.0.0.11, note that DC2 already has this information due to DC1 advertising this MAC+IP using the type 2 route we just found out about

Step 2: DC2 router responds saying that 10.0.0.11 is at AA:AA:AA:11:11:11, kind of like how proxy arp works... This is actually proxy ARP technically and is mentioned in the EVPN RFC, "the PE SHOULD perform ARP proxy by responding to the ARP Request.". However what would happen if DC2 didn't have this information? Depending on the vendor, typically ARP suppression is implemented by default to prevent the flooding of ARP across the EVPN domain. (this is also relevant for v6 neighbor discovery)

Step 3: The Device in DC2 (10.0.0.12) receives an ARP reply from DC2 which acted on 10.0.0.11s behalf, with this information the device can now build its layer 2 ethernet header destination MAC address and begin to send out ICMP echos to 10.0.0.11.

Step 4: Depending on the configuration of the vendor, in our case, DC2 has forwarding path installed for the VRF to get traffic to 10.0.0.11, here is an example from a Cisco IOS-XR device with that forwarding information:

```
10.0.0.11/32, version 120, internal 0x5000001 0x30 (ptr 0x933a72a8) [1], 0x0 (0x0), 0xa08 (0x981bac48)
 Updated Jun 21 22:51:17.184
 Prefix Len 32, traffic index 0, precedence n/a, priority 3
  gateway array (0x92def2a0) reference count 17, flags 0x2038, source rib (7), 0 backups
                [1 type 1 flags 0x40441 (0x9821cb98) ext 0x0 (0x0)]
  LW-LDI[type=0, refc=0, ptr=0x0, sh-ldi=0x0]
  gateway array update type-time 1 Jun 20 14:27:45.519
 LDI Update time Aug 19 23:34:46.489
   via 10.255.255.1/32, 9 dependencies, recursive [flags 0x6000]
    path-idx 0 NHID 0x0 [0x9831d578 0x0]
    recursion-via-/32
    next hop VRF - 'default', table - 0xe0000000
    next hop 10.255.255.1/32 via 22002/0/21
     next hop 10.255.254.89/32 Hu0/0/0/7    labels imposed {22002 24023}

    Load distribution: 0 (refcount 1)

    Hash  OK  Interface                 Address
    0     Y   recursive                 22002/0
```

![MPLS Label Stack for LSP](/img/2022-09-15-evpn-distributed-anycast-gateway/mpls_label_stack.PNG)

Step 5: Our original ICMP echo gets to DC1, labels are all stripped and from the inner VPN label (24023) as per below output

```
show mpls forwarding labels 24023 
Thu Sep 15 01:36:44.385 UTC
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes       
Label  Label       or ID              Interface                    Switched    
------ ----------- ------------------ ------------ --------------- ------------
24023  Aggregate   VRF-IRB-MGMT: Per-VRF Aggr[V]   \
                                      VRF-IRB-MGMT                 0 
```

Based on this Inner VPN label, the router can push the traffic into our VRF, note that I haven't spoke about VRFs too much yet but EVPN distributed anycast gateway ties in the layer 2 (EVI) and layer 3 (VRF) together with the anycast functionality which we will finally explore shortly. The ICMP can now be forwarded to our 10.0.0.11 device and everything repeats in reverse for the ICMP echo reply that 10.0.0.11 should send back to 10.0.0.12.

Now that we have explored some EVPN basics, let's dive into the anycast functionality before discussing the VM mobility/mac moving between different PEs.

1. Create the EVPN EVI

```
evpn
 evi 1
  bgp
   rd 10.255.255.1:41000
   route-target import 12345:41000
   route-target export 12345:41000
  !
  control-word-disable
  advertise-mac
  !
  unknown-unicast-suppression
```

2. Create the VRF, here we will just enable ipv4

```
vrf VRF-IRB-MGMT
 address-family ipv4 unicast
  import route-target
   12345:41000
  !
  export route-target
   12345:41000
```

3. Create the BVI which will act as our Layer 3 termination for the VM, this will be the anycast IP address configured at every data center

```
interface BVI13
 host-routing
 vrf VRF-IRB-MGMT
 ipv4 address 10.0.0.1 255.255.255.0
!
```

4. Create the bridge domain and tie the relevant interfaces connected to the VM/hypervisor + EVI + VRF

```
l2vpn
 bridge group EVPN-BVIS
  bridge-domain BD-13
   interface Bundle-Ether12345.13
   !
   routed interface BVI13
   !
   evi 1
```

5. Enable VPNv4 and l2vpn evpn families in the BGP configuration and between both PE routers via neighbor statements (or in your neighbor-group)

```
router bgp 12345
 address-family vpnv4 unicast
 !
 address-family l2vpn evpn
 !
 neighbor 10.255.255.2
  remote-as 12345
  update-source Loopback0
  !
  address-family vpnv4 unicast
  !
  address-family l2vpn evpn
  !
```

6. Verify BGP/EVPN tables

```
#show evpn evi vpn-id 1 mac aaaa.aa11.1111

VPN-ID     Encap      MAC address    IP address                               Nexthop                                 Label   
---------- ---------- -------------- ---------------------------------------- --------------------------------------- --------
1          MPLS       aaaa.aa11.1111 10.0.0.12                                10.255.255.2                            24018
```

```
#show bgp l2vpn evpn rd 12345:41000 [2][0][48][aaaa.aa11.1111][32][10.0.0.12]/136 detail

BGP routing table entry for [2][0][48][aaaa.aa11.1111][32][10.0.0.12]/136, Route Distinguisher: 12345:41000
Versions:
  Process           bRIB/RIB  SendTblVer
  Speaker            2384727     2384727
    Flags: 0x00041001+0x00010000; 
Last Modified: Sep  7 13:40:00.085 for 1w0d
Paths: (3 available, best #2)
  Advertised to update-groups (with more than one peer):
    0.3 0.4 
  Path #2: Received by speaker 0
  Flags: 0x2000020085060205, import: 0x9f, EVPN: 0x3
  Advertised to update-groups (with more than one peer):
    0.3 0.4 
  Local, (Received from a RR-client)
    10.255.255.2 (metric 33) from 10.255.255.2 (10.255.255.2), if-handle 0x00000000
      Received Label 24018, Second Label 24023
      Origin IGP, localpref 100, valid, internal, best, group-best, import-candidate, imported, rib-install
      Received Path ID 0, Local Path ID 1, version 18941
      Extended community: Flags 0x1e: SoO:10.255.255.2:1 EVPN MAC Mobility:0x00:3 0x060e:0000.0000.000d RT:12345:41000 
      EVPN ESI: 0000.0000.0000.0000.0000
      Source AFI: L2VPN EVPN, Source VRF: BD-13, Source Route Distinguisher: 12345:41000
```

7. Verify forwarding information

```
#show route vrf VRF-IRB-MGMT 10.0.0.12/32 detail

Routing entry for 10.0.0.12/32
  Known via "bgp 12345", distance 200, metric 0, type internal
  Routing Descriptor Blocks
    10.255.255.2, from 10.255.255.2
      Nexthop in Vrf: "default", Table: "default", IPv4 Unicast, Table Id: 0xe0000000
      Route metric is 0
      Label: 0x5dd7 (24023)
      Tunnel ID: None
      Binding Label: None
      Extended communities count: 1
        SoO:10.255.255.2:1
      NHID:0x0(Ref:0)
      MPLS eid:0xffffffffffffffff
  Route version is 0x11 (17)
  No local label
  IP Precedence: Not Set
  QoS Group ID: Not Set
  Flow-tag: Not Set
  Fwd-class: Not Set
  Route Priority: RIB_PRIORITY_RECURSIVE (12) SVD Type RIB_SVD_TYPE_REMOTE
  Download Priority 3, Download Version 120
  No advertising protos.

#show cef vrf VRF-IRB-MGMT 10.0.0.12/32
10.0.0.12/32, version 120, internal 0x5000001 0x30 (ptr 0x933a72a8) [1], 0x0 (0x0), 0xa08 (0x981bac48)
 Prefix Len 32, traffic index 0, precedence n/a, priority 3
  gateway array (0x92def2a0) reference count 17, flags 0x2038, source rib (7), 0 backups
                [1 type 1 flags 0x40441 (0x9821cb98) ext 0x0 (0x0)]
  LW-LDI[type=0, refc=0, ptr=0x0, sh-ldi=0x0]
   via 10.255.255.2/32, 9 dependencies, recursive [flags 0x6000]
    path-idx 0 NHID 0x0 [0x9831d578 0x0]
    recursion-via-/32
    next hop VRF - 'default', table - 0xe0000000
    next hop 10.255.255.2/32 via 20502/0/21
     next hop 10.255.254.89/32 Hu0/0/0/7    labels imposed {22002 24023}

    Load distribution: 0 (refcount 1)

    Hash  OK  Interface                 Address
    0     Y   recursive                 22002/0
```

Now that we have a base configuration for our anycast distributed gateway, lets talk about MAC mobility, MAC move or VM mobility... How do we ensure that when we move a device to another PE (another data center), this MAC address advertised back into the network is preferred and that no PE will attempt to forward data to the old PE (DC1). This is also defined within the same RFC mentioned earlier under section 15 "MAC mobility". An extended community attribute is added which contains a sequence number, this sequence number essentially allows us to determine which MAC+IP route is "newer" and more preferred therefore we can determine the MAC address has moved from 1 PE to another and the route with a higher sequence number should be installed into the forwarding plane. If you take a look at step 6 above, a specific line states this extended attribute `EVPN MAC Mobility:0x00:3` under the BGP route.

![MAC Mobility Sequence incrementing](/img/2022-09-15-evpn-distributed-anycast-gateway/mac_mobility.PNG)

Moving the 10.0.0.11 device in this scenario, requires 0 reconfiguration on the OS itself and after some basic data plane learning that occurs on DC2 device (eg. 10.0.0.11 sending out ARP or trying to initiate a conversation), DC2 will learnt the MAC address locally and create a new type 2 MAC route, in this case the original update sent from DC1 could potentially be withdrawn before this whole process occurs but this is simply to demonstrate the concept of sequence numbers incrementing within the BGP mac mobility extended community.


If you've found this blog useful or have any comments, feel free to connect with me on LinkedIn or leave a comment below! Stick around if you want to see more posts like this!