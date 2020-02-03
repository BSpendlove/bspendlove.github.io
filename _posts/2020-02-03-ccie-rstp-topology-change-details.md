---
layout: post
title: CCIE - RSTP Topology Changes
subtitle: CCIE Enterprise Infrastructure
comments: true
---

1.1.e i PVST+, Rapid PVST+, MST

The topology change operation between traditional 802.1D and 802.1w has been improved and you need to ensure you understand this clearly and know the key details how it's been improved, how it works and when a topology change occurs.

Firstly, what is a topology change notification (TCN)?

A TCN is simply a message used to inform the STP topology that a change has occured and must obey the simple rules of:
- Flush CAM tables (this is different depending on the protocol, 802.1D will set the MAC aging timer to the FWD_DELAY timer and 802.1w flushes out the MAC table almost instantly except MAC addresses on the port the BPDU was received on)
- Send BPDUs with the TC bit set (802.1D will only do this for the MAX_AGE + FWD_DELAY and 802.1w will only use HELLO + 1s which is also called the TC WHILE timer (older RSTP revisions used 2 x HELLO))

Let's take this diagram as a reference for comparing a simple topology change in 802.1D and 802.1w
![STP Topology](/img/2020-02-03-ccie-rstp-topology-change-details/ccie-rstp-basic-topology.JPG)

## 802.1D

A topology change in 802.1D occurs when either a port that is currently in the forwarding state changes to blocking (or even shuts down) or when a port transitions into the forwarding state (such as a port that moves into the forwarding state from the learning state)

The switch who detects the topology change will send a TCN BPDU as shown below:
![STP TCN BPDU Format](/img/2020-02-03-ccie-rstp-topology-change-details/ccie-stp-tcn-bpdu.JPG)

The TCN BPDU is a separate BPDU that is sent upstream on root ports to inform the Root that a topology change has occured. This BPDU will only be sent on root ports and will never be sent to a downstream switch. Below is the TCN Flow Example from SW4:
![STP TCN Flow Example](/img/2020-02-03-ccie-rstp-topology-change-details/ccie-stp-tcn-sent-upstream-example.JPG)

1. An interface goes down (gets unplugged from the switch)
2. SW4 generates a TCN BPDU which will be sent to the root switch via the root port. The TCN will not be sent to any downstream switches. The TCN is actually sent every HELLO timer configured on the local switch (not the HELLO timer set by the root inside the BPDU).
3. The upstream switch will acknowledge the TCN by sending the standard BPDU with the TC Acknowledgement bit set to 1 as shown in the picture below:
![STP TCA Example](/img/2020-02-03-ccie-rstp-topology-change-details/ccie-stp-topology-change-acknowledgement-example.JPG)

In theory, the upstream switch will acknowledge the TCN setting the TCA bit to 1 and the Topology Change bit is only set when the TCN reaches the Root switch. However this process happens very quickly in a small topology and you can see the TC bit set to 1 already.
This process repeats (step 4 and 5) until the TCN reaches the Root switch who will then set the TC flag within the BPDU to 1. BPDUs will be sent with this flag until a timer has expired which consists of the MAX_AGE + FWD_DELAY.

When downstream switches from the Root start receiving the BPDUs with the Topology Change (TC) bit set to 1, it will reduce the CAM tables aging timer from the default 300s to the current FWD_DELAY time (15s default).

PVST+ uses 802.1D standards on a per-instance which follows the same rules. A topology change within a single VLAN (eg. Access port) will only trigger a topology change notification related to that VLAN however the global aging timer is reduced (no matter which VLAN).

Cisco created a feature to be used with Spanning Tree called PortFast. While this feature makes the port state transition process faster (almost instantly into forwarding), it also solves the issues where ports generate TCNs (eg. when a user unplugs their laptop from a hotdesk) and prevents them from being generated when the port goes down or comes up.

## 802.1w

RSTP implements a new port type that changes when a topology changed occurs. This new port type is called 'Edge'
~~~
CSW01(config-if)#do sh spanning-tree int g1/0/23

Vlan                Role Sts Cost      Prio.Nbr Type
------------------- ---- --- --------- -------- --------------------------------
VLAN0224            Desg FWD 19        128.23   P2p Edge
~~~

RSTP improves on current timers with the port transition between different states, integrating a PortFast like feature into the standard itself however, Cisco still implement the PortFast feature and require the PortFast command on an interface for the interface to become an Edge port. Standard 802.1w implementation allows all ports to become an Edge port until a BPDU is received on the interface which causes it to loss it's edge port status and operates normally as a non-edge port type.

If an edge port goes down/comes up then a TCN is not generated (similar to how PortFast works with PVST+ and RPVST+). Without the PortFast command on Cisco equipment, the port will not be allowed to be considered an 'Edge' port.

Therefore, any port other port type is considered a non-edge and will trigger a TCN (however a TCN isn't required anymore in 802.1w). TCNs are a thing of the past with 802.1D. This is because how 802.1w allows switches to operate independently. Remember how RSTP/802.1w allows switches to now generate their own BPDUs and not entirely depend on the root sending BPDUs downstream? This also happens now with topology changes and how a topology change is flooded throughout the network, not depending on reaching to the root bridge to make the decision to set the TC bit to 1.

In the case of a switch detecting a topology change (eg. non-edge port goes down), they will not send a topology change notification. Below is an example of how 802.1w deals with a topology change:
![RSTP TC Example](/img/2020-02-03-ccie-rstp-topology-change-details/ccie-rstp-topology-change-example.JPG)

1. SW2 detects a topology change due to a non-edge port going down (effectively STP state transitions to disabled)
2. SW2 doesn't send a TCN because there is no concept of TCNs in 802.1w. He does however, now start sending BPDUs with the topology change bit set to 1 for HELLO + 1s (3 seconds default) out of non-edge ports + root port. Then the switch will instantly flush the MAC table of all addresses related to this port. During this process, SW1 will receive the BPDU sent from SW2.

When a Cisco device running STP receives the BPDU with the TC bit set to 1, they will perform the following:
- TC While (tcWhile) timer runs which is effectively how long it should send its own BPDUs with the TC bit set to 1 (by default HELLO + 1 second)
- MAC address table will need to be flushed without waiting. There are no timers like 802.1D however this process only occurs on ports except from the port where the original topology change was received on.

A switch will not flush any MAC address information related to the port the original BPDU with the TC flag is to prevent any communication issues...

An important key topic to remember is how a direct failure vs indirect failure affects the amount of time it takes for both 802.1D and 802.1w to converge. It is correct that RSTP converges faster but you would expect a newer, updated protocol to converge faster. Note that when RSTP needs to communicate to an 802.1D device, TCNs are used between the devices. If SW4 in our example was running PVST+, SW2 will acknowledge the TCN but then proceed to send BPDUs with the TC bit set.