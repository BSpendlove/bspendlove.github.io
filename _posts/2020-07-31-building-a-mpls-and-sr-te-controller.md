---
layout: post
title: Imagine building your own MPLS-TE/SR-TE Controller
subtitle: Sounds pretty cool right?
comments: true
---

Just imagine... Not having to pay $75,000 per year for a controller that is literally built to just steer traffic throughout your MPLS/SR domains? Well, this isn't the place you will find that information... However, you are not here to read a blog where I complain about the different controllers out on the market that can perform some really neat traffic engineering or where I compare the top 3 MPLS-TE/SR-TE controllers. This post is the result of someone that wants to try and set an objective to push MPLS/SR labels into a network for specific prefixes and maintain (to a certain degree) the MPLS-TE/SR-TE network state.

Let's start with the initial idea...

For the past few weeks, I've been looking for a personal project to improve my knowledge around MPLS-TE/Segment Routing and found that you always see the same thing on educational blogs/certification books when someone compares MPLS-TE/RSVP with SR-TE. They begin with the usual statement: "Labels are now propagated via the Link-State protocol which removes the complexity/additional protocols that we don't need in the network" and then shows a few diagrams... But then typically you'll see a single line or very very short paragraph like this:

"RSVP can reserve bandwidth however if you want to do this with SR-TE, you need a controller which typically runs PCEP". So it hit me... While it does seem a bit more convenient to use the existing undering routing protocols already in place to carry the SID information etc... we now need to introduce a complex controller which is probably going to be very expensive, whos job is to simply talk to the network and in the simplest way I can put it, push a label stack to a node and away the traffic goes.

You can read up about RSVP, SIDs, IS-IS TLVs, OSPF LSA Types, PCEP, Offline Computation but I'm trying to take a fairly simple approach to engineer traffic in a lab network with the use of Python, containers and BGP-LS (with a little bit of databases and javascript...)

![Container Setup Diagram](/img/2020-07-31-building-a-mpls-and-sr-te-controller/container-layout.JPG)

Above you can see a very basic example of the intial layout for the project. Let's talk about each component:

ExaBGP - This is a Python application which implements BGP-LS (RFC 7752) which can be used to gather Link State information about the network. At first, I was trying to use FRRouting where I put the FRRouting container in a docker container but had to expose it so the IS-IS neighborship would come up. However as you may read, this isn't an ideal solution. I was prepared to take the IS-IS database and parse it myself which could of taken some time but why make it harder for yourself when BGP-LS is the way to go if you want to grab information from different IGP domains. FRRouting does not currently support BGP-LS. A bonus with ExaBGP is that it can actually encode the BGP Messages received from it's peer so I follow some examples online to parse through and grab the JSON output so I can send it to my flask application (sdncontroller)

exabgpapi - Is simply an application that runs as a process under the exabgp configuration which will send JSON data using the python requests module.
exabgpapi_cli - Listens for input (request driven) to allow you to interact with the exabgpcli commands. This will be useful in the future when we begin to engineering traffic paths.

sdncontroller - This is where the magic will happen. This is simply a Flask app that has already got out of control. It handles the different nlri types for BGP-LS sent by exabgp. Interacts with a local database to keep track of the network state. Generates a TED in JSON format from the database... but it's also where a frontend will be hosted to see the traffic engineering topology.

database - Currently I am just running a simple sqlite database on the same container, using SQLAlchemy to create the data models which I have found fairly interesting and so far, well executed...

### TED / MPLS Topology

![Basic TED Diagram](/img/2020-07-31-building-a-mpls-and-sr-te-controller/basic-gui-network-map.JPG)

Above is a basic example of using the generated TED to build a awful looking topology that uses Vis.js. It currently shows links in both directions (and not the prefix/labels) but it will soon be looking half decent with the ability to interact with the GUI to perform basic TE functions.

Information for nodes are gathered by detecting a "bgpls-node" NLRI message in the BGP JSON format sent from ExaBGP. Each node will be created in the database with a unique ID (node_id) which is the IGP Domain ID + Router-ID, this ensures that in the future if I want to introduce the ability to see the whole TED between different IGP domains, it shouldn't be too hard to implement the logic.

BGPLS-Link information will contain information such as the local-node-descriptor which will have a relationship to the specific node_id. Information includes things like bandwidth reservation, colour, te/igp metrics, SIDs, etc...

A BGPLS-Prefix also includes information that relates to the specific BGPLS-Node therefore, I am able to easily establish relationships on the database part between the different links/prefixes a node has.

Prior to this, I was generating the full TED based on the initial neighborship discovery, waited until the EOR for that specific neighbor was received and build a JSON TED which was just dumped into a database but doing it this way (via database relationships and SQLAlchemy) has allowed me to easily implement a JSON view of the network via the database model. Here is an snippet of the JSON output for the topology showed above:

![Basic TED json](/img/2020-07-31-building-a-mpls-and-sr-te-controller/ted-topology-json.JPG)

While the GUI is very basic, it shows that I am able to build a small network and maintain the state in a database. If withdraws are detected for any NLRI type, the flask application will act eg. Delete the node if a node withdraw comes in... You can even see here a basic example of the Label mappings for every link along with the SID announced for the routers /32 loopback address:
![TED Label Diagram](/img/2020-07-31-building-a-mpls-and-sr-te-controller/labels_gui.JPG)

### What does all this information look like?

{% highlight json linenos %}
{
    "id": 4,
    "node_id": 4,
    "prefix": {
        "ls-nlri-type": "bgpls-prefix-v4",
        "l3-routing-topology": 100,
        "protocol-id": 2,
        "node-descriptors": {
            "autonomous-system": 100,
            "bgp-ls-identifier": "0",
            "router-id": "000000000004"
        },
        "ip-reachability-tlv": "10.255.255.4",
        "ip-reach-prefix": "10.255.255.4/32",
        "nexthop": "192.168.0.249",
        "prefix_attributes": {
            "origin": "igp",
            "local-preference": 100,
            "bgp-ls": {
                "prefix-metric": 0,
                "sr-algorithm": "0",
                "sr-prefix-flags": {
                    "R": 0,
                    "N": 1,
                    "P": 0,
                    "E": 0,
                    "V": 0,
                    "L": 0
                },
                "sids": [
                    13204
                ],
                "sr-prefix-attribute-flags": {
                    "X": 0,
                    "R": 0,
                    "N": 1
                }
            }
        }
    }
}
{% endhighlight %}

The above example is a BGPLS Prefix (v4), this is how it looks when it's pulled out of the database. BGP Attributes are assigned on a per prefix basis which is slightly different to how the UPDATE message arrives to the Flask API.

Any prefixes that share a common set of attributes will fall under the same BGP Update however I think it's easier to keep a local record in the prefix database table so I have direct access when I use the python db.Model classes. For example the above output could of been a SQLAlchemy Object called `link_1`. I can access the SID for example by simply referencing: `print(link_1.sr_sids)`. One thing I do want to point out if you haven't already noticed, this can easily be amended so I can just use it strictly for structing the data and parse it in any other language/application to generate topologies or even perform traffic engineering.

I currently haven't started work on the traffic engineering side of the project yet because I feel like I could/should improve the database/data structure part of the application. Initially starting a project like this, it can get out of hand very quickly and code starts to get messy. If you would like to view more examples or take a look at the project, feel free to visit the github project:

https://github.com/BSpendlove/sr-te-controller