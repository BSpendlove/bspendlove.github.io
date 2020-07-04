---
layout: post
title: IS-IS Multiarea/level SPF Convergence
subtitle: One of the boring (exciting) parts of studying...
comments: true
---

A warning prior reading this blog: There is a lot of output snippets from various show commands...

SPF, we all know what it stands for and the majority of us can describe enough to get by when talking in sense of OSPF and IS-IS. "When link x fails, it will cause the neighbor to tear down the neighbor relationship which will trigger an SPF recalculation" but I wanted to just talk about SPF within a multi-level/area IS-IS design since I feel like the SPF part is easy to understand, but how well can you scale a link-state protocol to 1000+, if not 10,000+ routers?

At first glance, I thought is this it? Comparing how areas work with IS-IS and OSPF makes me feel like I was missing something or maybe didn't understand the differences but think of the reason why OSPF introduced areas?

OSPF areas are deployed to start breaking up the LSDB and prevent too much stress on a device when it needs to perform an SPF recalulcation. It takes CPU and memory resources to perform tasks like this so it starts to become a problem when you have a massive flat area 0 with a large number of devices in the same area. Maybe 10-15 years ago, the hardware deployed in networks would start to struggle with 100+ OSPF nodes in the same area so the next design choice was to chop up the OSPF network into multiple areas, which would decrease the overall size of the LSDBs for the non-backbone areas and then whenever a topology change occured in another area, internal routers in a different non-backbone area wouldn't need to perform a full SPF recalculation. They only need to recompute SPF for the ABR (OSPF technically works like a distance vector at this point because he doesn't actually know LSAs beyond the ABR and trusts as long as the ABR sends a metric to that specific route, then he will trust it...)

When you introduce areas into IS-IS, it won't begin summarizing link-state information between the different areas (which OSPF will do), this is why no one refers to it as multi-area, instead they will refer to it as multi-level since the hierarchy of IS-IS design depends heavily on Level 1 / Level 2. Take the below example:

![IS-IS Multi-level Topology](/img/2020-07-03-ccnp-sp-isis-multiarea-SPF-convergence/isis-spf-topology.JPG)

We have xrv4 running Level 2 only in area 49.0001 connecting to xrv6 (who is a Level 1/2 router in area 49.0011). xrv6 still needs to maintain his Level 2 LSDB even though he is in a different area (this is kind of like an ABR in OSPF that has 1 interface connected to area 0 and another in a non-backbone area). He could also perform some other roles such as BGP route reflection to IS routers in his level 1 domain, or even redistribute L2 /32 loopback addresses into level 1 for technologies such as L3/L2VPN to work properly.

Each router is advertising a loopback address (and the p2p links) into IS-IS as eg xrv1 = 1.1.1.1, vios7 = 7.7.7.7. Let's take a look at the level 2 LSDB on xrv6 and filter it for information propagated via xrv5.

```
IS-IS 1 (Level-2) Link State Database
LSPID                 LSP Seq Num  LSP Checksum  LSP Holdtime  ATT/P/OL
xrv5.00-00            0x00000020   0xe7ab        812             0/0/0
  Area Address:   49.0010
  NLPID:          0xcc
  Hostname:       xrv5
  IP Address:     5.5.5.5
  Metric: 10         IS xrv3.00
  Metric: 0          IP 5.5.5.5/32
  Metric: 10         IP 9.9.9.9/32
  Metric: 10         IP 10.0.35.0/24
  Metric: 10         IP 10.0.57.0/24
  Metric: 10         IP 10.0.59.0/24
  Metric: 20         IP 10.0.79.0/24
  Metric: 20         IP 10.0.107.0/24
  Metric: 20         IP 10.10.10.10/32
```

xrv5 is learning 9.9.9.9 and 10.10.10.10 via level 1 routers in area 49.0010. By default an IS node operating at Level 1/2 will automatically 'redistribute' Level 1 routes (i L1) into L2 without any configuration but not vice versa. However here is where we talk about the SPF part.

If the link between xrv1 and xrv2 goes down, all of the routers apart of the level 2 domain will have to perform a full SPF recalulation for it's level 2 LSDB, this is expected whether the protocol is IS-IS or OSPF. However devices such as vios9, 10, 11 and 12 will not need to perform any full SPF recalulation. In fact with a default configuration, their SPF tree will not be affected because their respective L1/L2 router will be sending a default route because they will not advertise L2 routes into the L1 database.

```
RP/0/0/CPU0:xrv1#conf t
Sat Jul  4 00:25:29.874 UTC
RP/0/0/CPU0:xrv1(config)#int g0/0/0/0
RP/0/0/CPU0:xrv1(config-if)#shut
RP/0/0/CPU0:xrv1(config-if)#commit
Sat Jul  4 00:25:39.154 UTC
RP/0/0/CPU0:xrv1(config-if)#end
RP/0/0/CPU0:xrv1#show isis spf-log last 3
Sat Jul  4 00:25:44.793 UTC

   IS-IS 1 Level 2 IPv4 Unicast Route Calculation Log
                    Time Total Trig.
Timestamp    Type   (ms) Nodes Count First Trigger LSP    Triggers
------------ ----- ----- ----- ----- -------------------- -----------------------
--- Sat Jul  4 2020 ---
00:25:11.826  FSPF     0     8     1           xrv2.00-00 LINKGOOD
00:25:12.046  FSPF     0     8     2           xrv1.00-00 NEWADJ LINKGOOD
00:25:39.344  FSPF     0     8     2           xrv1.00-00 DELADJ LINKBAD ! This one is the failure from shutting down the interface, Full SPF required
RP/0/0/CPU0:xrv1#show clock
Sat Jul  4 00:25:47.093 UTC
00:25:47.133 UTC Sat Jul 4 2020
```

```
RP/0/0/CPU0:xrv6#show isis spf-log last 3
Sat Jul  4 00:26:14.371 UTC

   IS-IS 1 Level 1 IPv4 Unicast Route Calculation Log
                    Time Total Trig.
Timestamp    Type   (ms) Nodes Count First Trigger LSP    Triggers
------------ ----- ----- ----- ----- -------------------- -----------------------
--- Sat Jul  4 2020 ---
00:15:23.646  FSPF     0     4     1                      PERIODIC
00:20:56.213   NHC     0     4     2                      NEWADJ DELADJ
00:20:57.193   PRC     0     4     1         vios11.00-00 PREFIXBAD

   IS-IS 1 Level 2 IPv4 Unicast Route Calculation Log
                    Time Total Trig.
Timestamp    Type   (ms) Nodes Count First Trigger LSP    Triggers
------------ ----- ----- ----- ----- -------------------- -----------------------
--- Sat Jul  4 2020 ---
00:25:12.295  FSPF     0     8     2           xrv2.00-00 LINKGOOD
00:25:39.733  FSPF     0     8     2           xrv1.00-00 LINKBAD PREFIXBAD
00:26:00.512  FSPF     0     8     1           xrv2.00-00 LINKBAD             ! This one is the failure from shutting down the interface, Full SPF required
RP/0/0/CPU0:xrv6#show clock
Sat Jul  4 00:26:17.421 UTC
00:26:17.501 UTC Sat Jul 4 2020
```

We see that xrv6 (and all other devices in the L2 domain) had to perform a full SPF recalculation, but let's see vios9:
```
vios9#show isis spf-log 

Tag 1:
   TID 0 level 1 SPF log
  When   Duration  Nodes  Count    First trigger LSP   Triggers
00:40:13       4      4      1                       PERIODIC CLNSBACKUP
00:25:13       3      4      1                       PERIODIC CLNSBACKUP
00:10:13       3      4      1                       PERIODIC CLNSBACKUP
          
vios9#
vios9#show clock
*00:27:31.408 UTC Sat Jul 4 2020
          
```
IOS shows output when the last SPF convergence occured and remember that IS-IS will automatically refresh LSPs every 15 minutes which will trigger a full SPF recalculation. (which is what we see above along with some testing I done 10 minutes ago prior to shutting down the interface...)

I would show an output with OSPF but this is an IS-IS blog, so you'll have to take my word for it that for a default configuration, routes are still sent between inter-areas via the backbone with 0 filtering, so the SPF will need to be recalculated but this is only a partial SPF recalculation towards the ABR. To get similar results like this in OSPF you will need to configure NSSA. IS-IS Level 1/2 with inter-area routing by default acts the same way an OSPF NSSA area does.

What about routers within the layer 2 domain recalculating SPF when a link goes down in another area/level? Let's take a LAN segment for example connected to vios9.
![IS-IS vios9 LAN Segment](/img/2020-07-03-ccnp-sp-isis-multiarea-SPF-convergence/isis-vios9-lan-leaf.JPG)

```
vios9(config)#int g0/2
vios9(config-if)#ip add 10.90.0.1 255.255.255.0
vios9(config-if)#no shut
*Jul  4 00:35:43.190: %LINK-3-UPDOWN: Interface GigabitEthernet0/2, changed state to up
*Jul  4 00:35:44.190: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/2, changed state to up
```

```
*Jul  4 00:35:50.877: ISIS-SPF: L1 LSP 3 (0000.0000.0009.00-00) flagged for recalculation from                      
*Jul  4 00:35:52.876: ISIS-SPF: LSP 3 (0000.0000.0009.00-00) Type STD
*Jul  4 00:35:52.877: ISIS-SPF: spf_result: next_hop_parents:0x114E37EC root_distance:20, parent_count:1, parent_index:2 db_on_paths:1
*Jul  4 00:35:52.877: ISIS-SPF: Calculating routes for L1 LSP 3 (0000.0000.0009.00-00)
*Jul  4 00:35:52.878: ISIS-SPF: lsptype:0, current_lsp(0000.0000.0009.00-00)(3)  current_lsp:0x10DA54C0, lsp_fragment:0x10DA54C0 calling isis_walk_lsp
*Jul  4 00:35:52.880: ISIS-SPF: Aging L1 LSP 3 (0000.0000.0009.00-00), version 24
vios10#
vios10#
vios10#show isis spf-log       

Tag 1:
   TID 0 level 1 SPF log
  When   Duration  Nodes  Count    First trigger LSP   Triggers
04:34:29       4      4      1                       PERIODIC CLNSBACKUP
04:19:29       5      4      1                       PERIODIC CLNSBACKUP
04:04:29       3      4      1                       PERIODIC CLNSBACKUP
03:49:29       4      4      1                       PERIODIC CLNSBACKUP
03:34:29       4      4      1                       PERIODIC CLNSBACKUP
03:19:29       4      4      1                       PERIODIC CLNSBACKUP
03:04:29       4      4      1                       PERIODIC CLNSBACKUP
02:49:29       4      4      1                       PERIODIC CLNSBACKUP
02:34:29       3      4      1                       PERIODIC CLNSBACKUP
02:19:29       3      4      1                       PERIODIC CLNSBACKUP
02:04:28       3      4      1                       PERIODIC CLNSBACKUP
01:49:28       3      4      1                       PERIODIC CLNSBACKUP
01:34:28       3      4      1                       PERIODIC CLNSBACKUP
01:19:28       3      4      1                       PERIODIC CLNSBACKUP
01:04:28       3      4      1                       PERIODIC CLNSBACKUP
00:49:28       4      4      1                       PERIODIC CLNSBACKUP
00:34:28       4      4      1                       PERIODIC CLNSBACKUP
00:19:28       4      4      1                       PERIODIC CLNSBACKUP
00:04:28       3      4      1                       PERIODIC CLNSBACKUP        ! No Full SPF Recalculation here
```

After introducing a new link on vios9, the LSP was sent through the level 1 domain and reached vios10. vios10 performed a partial SPF calculation towards LSP 10.90.0.0/24.

Our Level 1/2 router had also performed a partial route calculation as shown below (xrv5): (shut down the interface again a few minutes after bringing it back up from previous example)
```
RP/0/0/CPU0:xrv5#RP/0/0/CPU0:Jul  4 00:42:15.505 : isis[1010]: Standard (IPv4 Unicast) L1 Trigger: Partial Route Calculation requested due to 1 trigger(s) in vios9.00-00 (seq. 0x1f):
RP/0/0/CPU0:Jul  4 00:42:15.505 : isis[1010]: Standard (IPv4 Unicast) L1 Trigger:   PREFIXBAD - Bad news prefix TLV content change (10.90.0.0/24)
RP/0/0/CPU0:Jul  4 00:42:15.505 : isis[1010]: Standard (IPv4 Unicast) L1 Trigger:   Partial Route Calculation scheduled with initial delay of 50ms
RP/0/0/CPU0:Jul  4 00:42:15.565 : isis[1010]: Standard (IPv4 Unicast) L1 PRC: Route calculation starting
RP/0/0/CPU0:Jul  4 00:42:15.565 : isis[1010]: IPv4 Unicast L1 PRC: Route update starting:
RP/0/0/CPU0:Jul  4 00:42:15.565 : isis[1010]: IPv4 Unicast L1 PRC:   Critical priority update starting:
RP/0/0/CPU0:Jul  4 00:42:15.565 : isis[1010]: IPv4 Unicast L1 PRC:   Critical priority update complete:
RP/0/0/CPU0:Jul  4 00:42:15.565 : isis[1010]: IPv4 Unicast L1 PRC:   High priority update starting:
RP/0/0/CPU0:Jul  4 00:42:15.565 : isis[1010]: IPv4 Unicast L1 PRC:   High priority update complete:
RP/0/0/CPU0:Jul  4 00:42:15.565 : isis[1010]: IPv4 Unicast L1 PRC:   Medium priority update starting:
RP/0/0/CPU0:Jul  4 00:42:15.565 : isis[1010]: IPv4 Unicast L1 PRC:   Medium priority update complete:
RP/0/0/CPU0:Jul  4 00:42:15.565 : isis[1010]: IPv4 Unicast L1 PRC:   Low priority update starting:
RP/0/0/CPU0:Jul  4 00:42:15.565 : isis[1010]: IPv4 Unicast L1 PRC:   Low priority update complete:
RP/0/0/CPU0:Jul  4 00:42:15.565 : isis[1010]: IPv4 Unicast L1 PRC: Route update complete:
RP/0/0/CPU0:Jul  4 00:42:15.565 : isis[1010]: Standard (IPv4 Unicast) L1 PRC: Route calculation complete
RP/0/0/CPU0:Jul  4 00:42:17.585 : isis[1010]: Standard (IPv4 Unicast) L2 Trigger: Partial Route Calculation requested due to 1 trigger(s) in vios7.00-00 (seq. 0x23):
RP/0/0/CPU0:Jul  4 00:42:17.585 : isis[1010]: Standard (IPv4 Unicast) L2 Trigger:   PREFIXBAD - Bad news prefix TLV content change (10.90.0.0/24)
RP/0/0/CPU0:Jul  4 00:42:17.585 : isis[1010]: Standard (IPv4 Unicast) L2 Trigger:   Partial Route Calculation scheduled with initial delay of 50ms
RP/0/0/CPU0:Jul  4 00:42:17.655 : isis[1010]: Standard (IPv4 Unicast) L2 PRC: Route calculation starting
RP/0/0/CPU0:Jul  4 00:42:17.655 : isis[1010]: IPv4 Unicast L2 PRC: Route update starting:
RP/0/0/CPU0:Jul  4 00:42:17.655 : isis[1010]: IPv4 Unicast L2 PRC:   Critical priority update starting:
RP/0/0/CPU0:Jul  4 00:42:17.655 : isis[1010]: IPv4 Unicast L2 PRC:   Critical priority update complete:
RP/0/0/CPU0:Jul  4 00:42:17.655 : isis[1010]: IPv4 Unicast L2 PRC:   High priority update starting:
RP/0/0/CPU0:Jul  4 00:42:17.655 : isis[1010]: IPv4 Unicast L2 PRC:   High priority update complete:
RP/0/0/CPU0:Jul  4 00:42:17.655 : isis[1010]: IPv4 Unicast L2 PRC:   Medium priority update starting:
RP/0/0/CPU0:Jul  4 00:42:17.655 : isis[1010]: IPv4 Unicast L2 PRC:   Medium priority update complete:
RP/0/0/CPU0:Jul  4 00:42:17.655 : isis[1010]: IPv4 Unicast L2 PRC:   Low priority update starting:
RP/0/0/CPU0:Jul  4 00:42:17.655 : isis[1010]: IPv4 Unicast L2 PRC:   Low priority update complete:
RP/0/0/CPU0:Jul  4 00:42:17.655 : isis[1010]: IPv4 Unicast L2 PRC: Route update complete:
RP/0/0/CPU0:Jul  4 00:42:17.655 : isis[1010]: Standard (IPv4 Unicast) L2 PRC: Route calculation complete
```

OSPF on the other hand, the ABR would have to perform a full SPF recalculation for that specific prefix/LSA and propagate that via the network. IS-IS will consider this prefix a leaf within the SPF tree and therefore does not trigger a full SPF recalculation when a trigger occurs for that prefix. OSPF has a similar concept with leafs in the SPF graph however only treats prefixes such as redistributed networks as a leaf within the SPF tree and will only perform a partial SPF recalculation on those prefixes.

![IS-IS SPF Node tree](/img/2020-07-03-ccnp-sp-isis-multiarea-SPF-convergence/isis-spf-node-tree.JPG)

You can see a basic example of the SPF node tree (excluding things like metric values), let's just take a quick look how OSPF would act in this scenario where vios9 has a link failure for the LAN segment 10.90.0.0/24 and see how vios10 would react. In the OSPF example, I am using the same topology but Level 2 only is area 0, with xrv5 and vios7 being ABRs for area 0 and area 10. vios9 and vios10 only belong to area 10.

```
*Jul  4 10:14:03.291: %SYS-5-CONFIG_I: Configured from console by console
Enter configuration commands, one per line.  End with CNTL/Z.
vios9(config)#int g0/2
vios9(config-if)#shut
vios9(config-if)#
```

```
vios10#show ip ospf statistics detail
SPF 5 executed 00:00:03 ago, SPF type Full
  SPF calculation time (in msec):
  SPT    Intra  D-Intr Summ   D-Summ Ext7   D-Ext7 Total
  1      2      2      3      1      0      0      8
  LSIDs processed R:4 N:4 Stub:2 SN:15 SA:0 X7:0
  Change record 0x0
  LSIDs changed 1
  Changed LSAs. Recorded is LS ID and LS type:
  9.9.9.9(R)

vios10#show clock
*10:14:37.851 UTC Sat Jul 4 2020
```

xrv5 would also need to perform a full SPF recalculation and ensure that the LSDB for area 10 is synced with other nodes in the same area, but remember that LSA type 1/2s will not be sent between areas. OSPF multiarea introduces the summary LSA (type 3) which essentially summarizes the LSAs (not the routes!). Therefore xrv3, when informed about the LSA, it would only need to perform a partial SPF calculation to the ABR (xrv5 and vios7 in our topology) for that specific prefix/link. The reason why I am focusing on OSPF now is to demonstrate to the reader that the area concept in IS-IS is NOT the same as OSPF. However a combination of both multi-level and multi-area is somewhat very similar to OSPF without the need of performing full SPF recalculations within the local area unless it's a link connecting 2 IS nodes. 10.90.0.0/24 is considered a leaf of the SPF tree in both protocol implementations however, IS-IS only performs a partial SPF whether the leaf goes down in the same area/level or in a different area/level. The same concept applies with IS-IS when xrv3 tries to recalculate SPF towards 10.90.0.0/24, it only needs to perform it against xrv5/vios7 (which you could argue a L1/L2 IS router is almost similar to an ABR)

```
RP/0/0/CPU0:xrv3#debug ospf 1 spf inter 
RP/0/0/CPU0:Jul  4 10:17:19.953 : ospf[1018]:  db remove spf links type 3 dest 10.90.0.0 255.255.255.0, adv rtr 5.5.5.5
RP/0/0/CPU0:Jul  4 10:17:22.143 : ospf[1018]:  process summary: rtrid 7.7.7.7 (1)
RP/0/0/CPU0:Jul  4 10:17:22.143 : ospf[1018]:  process partial summary: type 3, lsid 10.90.0.0
RP/0/0/CPU0:Jul  4 10:17:22.143 : ospf[1018]:  Start processing Summary LSA 10.90.0.0, mask 255.255.255.0, adv 7.7.7.7, age 3600, seq 0x80000002 (Area 0)
RP/0/0/CPU0:Jul  4 10:17:22.143 : ospf[1018]:  OSPF: ospf_gen_asbr_sum_all_areas
RP/0/0/CPU0:Jul  4 10:17:24.183 : ospf[1018]:  db remove spf links type 3 dest 10.90.0.0 255.255.255.0, adv rtr 7.7.7.7
```

What if we start doing some more complex tasks such as leak all the IS-IS loopback addresses from Level 2 at xrv6/vios8 into the level 1 domain so that vios11/vios12 have more specific /32 routes towards the rest of the network instead of just a default route? Take this poorly designed example below:

![IS-IS Redistribute loopbacks](/img/2020-07-03-ccnp-sp-isis-multiarea-SPF-convergence/isis-loopback-level2-to-level1.JPG)

IOS-XR (xrv6)
```
prefix-set ISIS-L2-TO-L1-LEAK
  0.0.0.0/0 ge 32 ! Ideally you would have a loopback range to permit otherwise any /32 in IS-IS level 2 will be reidstributed
end-set

route-policy RPL-ISIS-LEVEL2-TO-LEVEL1-LEAK
  if destination in ISIS-L2-TO-L1-LEAK then
    pass
  endif
end-policy

router isis 1
 address-family ipv4 unicast
  propagate level 2 into level 1 route-policy RPL-ISIS-LEVEL2-TO-LEVEL1-LEAK
```

IOS-XE (vios8)
```
ip prefix-list PFX-ISIS-LOOPBACKS permit 0.0.0.0/0 ge 32

route-map ISIS-L2-TO-L1-LEAK permit 10
 match ip address prefix-list PFX-ISIS-LOOPBACKS

router isis 1
 redistribute isis ip level-2 into level-1 route-map ISIS-L2-TO-L1-LEAK
```

```
vios11#show ip route isis | include i ia
i ia     1.1.1.1 [115/40] via 10.0.116.6, 00:30:27, GigabitEthernet0/0
i ia     2.2.2.2 [115/30] via 10.0.116.6, 00:30:27, GigabitEthernet0/0
i ia     3.3.3.3 [115/30] via 10.0.116.6, 00:30:27, GigabitEthernet0/0
i ia     4.4.4.4 [115/20] via 10.0.116.6, 00:30:31, GigabitEthernet0/0
i ia     5.5.5.5 [115/40] via 10.0.116.6, 00:30:27, GigabitEthernet0/0
i ia     6.6.6.6 [115/10] via 10.0.116.6, 00:30:31, GigabitEthernet0/0
i ia     7.7.7.7 [115/40] via 10.0.116.6, 00:30:27, GigabitEthernet0/0
i ia     8.8.8.8 [115/20] via 10.0.116.6, 00:30:27, GigabitEthernet0/0
i ia     9.9.9.9 [115/50] via 10.0.116.6, 00:30:27, GigabitEthernet0/0
i ia     10.10.10.10/32 [115/60] via 10.0.116.6, 00:28:22, GigabitEthernet0/0
```

inter-area IS-IS routes are considered a leaf in the IS-IS spf tree. vios11 will see something like this:
![IS-IS xrv6 LSP sent to vios11](/img/2020-07-03-ccnp-sp-isis-multiarea-SPF-convergence/isis-xrv6-lsp.JPG)

The LSP that vios11 receives from xrv6 describes 'important' links and IS nodes apart of his LSDB, but also interarea routes (level 2 redistributed into level 1) and as mentioned previously, all these networks are considered a leaf of the SPF tree for the level 1 LSDB (for both vios11 and xrv6). xrv6 obviously also maintains his level 2 LSDB which some of these loopbacks are in other areas (such as routes leaked from level 1 area 49.0010 into level 2 area 49.0001 like 9.9.9.9 and 10.10.10.10, these networks are also considered leafs from Level 2 perspective for xrv6... even xrv1 and they will only need to perform partial SPF calculations towards xrv5 and vios7 which is the same concept in OSPF).

Can you now see that while you can get a bit more complicated with the overall IS-IS design in a network, maintaining a well designed hierarchy can scale the LSDB problems that can occur when you are talking about very large networks. Previously, people would stick a number on the number of routers allowed in OSPF's area 0 or in the flat IS-IS level 2 domain such as 50-60 routers but you can design flat networks (as in just 1 area/level, not a flat /16 ipv4 network...) with 150-200+ routers before you start running into issues if the network is stable.

OSPF LSAs and IS-IS LSPs are one of the triggers that cause full/partial SPF recalculations and there are many knobs and buttons (cli commands) to tweak to perform things like LSA/LSP throttling, extending the time between calculations for a full or partial SPF calculation, setting overload bits, summarizing networks so SPF won't be triggered if a prefix of a summarization goes down or just using OSPF stub area types/IS-IS multi-level/area to meet the requirements of the network design.

If you'd like to read more on IS-IS throttling for LSPs and SPF calculations, Cisco have some good documentation (Juniper probably does too) on their IOS configuration guide here:
[Configuring Integrated IS-IS](https://www.cisco.com/c/en/us/td/docs/ios/12_2/ip/configuration/guide/1cfisis.html#wp1009159)