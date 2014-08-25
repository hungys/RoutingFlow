# What's RoutingFlow?

RoutingFlow is a project inspired by RouteFlow, aims to implement legacy and distributed routing protocol in a OpenFlow network. Currently, Routing Flow is built as a controller app for Ryu Controller and provides a basic framework and interface to implement routing protocols such as RIP, OSPF on Ryu.

Compared with the well-known open source project, RouteFlow, RoutingFlow doesn't depend on existed routing software such as Quagga and run a VM for each network nodes, but provide a interface to simulate each switch as a thread to decline the hardware resource usage.

You can learn more about RouteFlow in their
[page in GitHub](http://routeflow.github.io/RouteFlow/), in the
[wiki](https://github.com/routeflow/RouteFlow/wiki) and in their 
[website](https://sites.google.com/site/routeflow/).

# Requirements

* Python 2.7+: Noticed that Ryu was built under Python 2.7 but not Python 3+
* Ryu SDN Framework: I encourage you to download the latest distribution in their [repository in GitHub](https://github.com/osrg/ryu)
* (optional) mininet: A software to help you create virtual network topology in single machine, learn more informations in their [official website](http://mininet.org/)

# Building

1. Install Ryu SDN Framework
  * Using pip command is the easiest option:
  
    ```
    % pip install ryu
    ```
  * If you prefer to install from the source code:
  
    ```
    % git clone git://github.com/osrg/ryu.git 
    % cd ryu; python ./setup.py install 
    ```
    
2. (optional) Run the python script to build sample topogloty, it will run the mininet and generate a network topology with 3 switches and 4 hosts.

  ```
  sudo python test/sample_topology.py
  ```

3. Run the RoutingFlow app using ryu-manager
  
  Noticed that **ryu.topology.switches** is a required module to dicover the network topology for RoutingFlow.

  ```
  sudo ryu-manager --verbose --observe-links --default-log-level 20   ryu.topology.switches ryu.app.rest_topology ryu.app.ofctl_rest /home/user/  RoutingFlow/routing.py
  ```

4. Run the shell script to send HTTP request for gateway settings modification

  ```
  sh set_gateway.sh
  ``` 

5. RoutingFlow will triggered by topology changed event and start to advertise routing information with their neighbors, you can use `pingall` command in mininet CLI to test the connectivity between all nodes.

# Protocol Implementation

If you want to build your own routing protocol on RoutingFlow, you can write your custom RoutingTable and RoutingEntry class by inherit the class in `base/rib.py`, there include some basic definitions and methods required for a routing table.

```
def update_entry(self, subnet, receive_port, neighbor_port=None, metric=0):
    raise NotImplementedError

def update_by_neighbor(self, receive_port, neighbor_port, tbl):
    raise NotImplementedError
```

For more information, you can refer `rip.py`, it's a basic implementation of Routing Information Protocol.

# REST Interface

## Get Switch Information

### Get all switches

endpoint: `GET /routingflow/switches`

response:

```
[ { "arp_table" : [ { "hw_addr" : "42-39-5F-21-B9-17",
          "ip" : "10.0.2.10",
          "last_update" : "2014-08-24 19:07:46"
        },
        { "hw_addr" : "66-EA-27-83-C0-4D",
          "ip" : "10.0.1.10",
          "last_update" : "2014-08-24 19:07:46"
        }
      ],
    "dpid" : "0000000000000001",
    "name" : "s1",
    "neighbors" : [ "0000000000000002" ],
    "ports" : [ { "gateway" : {  },
          "hw_addr" : "72-39-60-20-77-3D",
          "name" : "s1-eth1",
          "neighbor_port_no" : "00000001",
          "neighbor_switch_dpid" : "0000000000000002",
          "port_no" : "00000001"
        },
        { "gateway" : { "ipv4" : "10.0.1.1",
              "ipv4_netmask" : "255.255.255.0",
              "ipv6" : "10::1:1",
              "ipv6_netmask" : "ffff:ff00::"
            },
          "hw_addr" : "CA-AD-65-8C-28-B4",
          "name" : "s1-eth2",
          "neighbor_port_no" : "",
          "neighbor_switch_dpid" : "",
          "port_no" : "00000002"
        },
        { "gateway" : { "ipv4" : "10.0.2.1",
              "ipv4_netmask" : "255.255.255.0",
              "ipv6" : "10::2:1",
              "ipv6_netmask" : "ffff:ff00::"
            },
          "hw_addr" : "92-BD-24-38-48-9A",
          "name" : "s1-eth3",
          "neighbor_port_no" : "",
          "neighbor_switch_dpid" : "",
          "port_no" : "00000003"
        },
        { "gateway" : {  },
          "hw_addr" : "1E-23-0D-CD-01-49",
          "name" : "s1",
          "neighbor_port_no" : "",
          "neighbor_switch_dpid" : "",
          "port_no" : "0000fffe"
        }
      ],
    "routing_table" : [ { "last_update" : "2014-08-24 19:07:25",
          "metric" : 2,
          "next_hop" : "0000000000000002",
          "out_port" : "00000001",
          "subnet" : "10.0.3.1/24"
        },
        { "last_update" : "2014-08-24 19:07:25",
          "metric" : 0,
          "out_port" : "00000003",
          "subnet" : "10.0.2.1/24"
        },
        { "last_update" : "2014-08-24 19:07:25",
          "metric" : 0,
          "out_port" : "00000002",
          "subnet" : "10.0.1.1/24"
        },
        { "last_update" : "2014-08-24 19:07:25",
          "metric" : 2,
          "next_hop" : "0000000000000002",
          "out_port" : "00000001",
          "subnet" : "10.0.4.1/24"
        }
      ]
  },
  { "arp_table" : [  ],
    "dpid" : "0000000000000002",
    "name" : "s2",
    "neighbors" : [ "0000000000000001",
        "0000000000000003"
      ],
    "ports" : [ { "gateway" : {  },
          "hw_addr" : "96-F3-07-7B-41-5F",
          "name" : "s2-eth1",
          "neighbor_port_no" : "00000001",
          "neighbor_switch_dpid" : "0000000000000001",
          "port_no" : "00000001"
        },
        { "gateway" : {  },
          "hw_addr" : "A2-A1-B5-FC-7A-0C",
          "name" : "s2-eth2",
          "neighbor_port_no" : "00000001",
          "neighbor_switch_dpid" : "0000000000000003",
          "port_no" : "00000002"
        },
        { "gateway" : {  },
          "hw_addr" : "7E-DC-89-83-1C-4E",
          "name" : "s2",
          "neighbor_port_no" : "",
          "neighbor_switch_dpid" : "",
          "port_no" : "0000fffe"
        }
      ],
    "routing_table" : [ { "last_update" : "2014-08-24 19:07:36",
          "metric" : 1,
          "next_hop" : "0000000000000001",
          "out_port" : "00000001",
          "subnet" : "10.0.1.1/24"
        },
        { "last_update" : "2014-08-24 19:07:36",
          "metric" : 1,
          "next_hop" : "0000000000000001",
          "out_port" : "00000001",
          "subnet" : "10.0.2.1/24"
        },
        { "last_update" : "2014-08-24 19:07:36",
          "metric" : 1,
          "next_hop" : "0000000000000003",
          "out_port" : "00000002",
          "subnet" : "10.0.3.1/24"
        },
        { "last_update" : "2014-08-24 19:07:36",
          "metric" : 1,
          "next_hop" : "0000000000000003",
          "out_port" : "00000002",
          "subnet" : "10.0.4.1/24"
        }
      ]
  },
  { "arp_table" : [ { "hw_addr" : "3A-49-5A-07-8C-4A",
          "ip" : "10.0.3.10",
          "last_update" : "2014-08-24 19:07:46"
        },
        { "hw_addr" : "66-97-3C-DB-62-CE",
          "ip" : "10.0.4.10",
          "last_update" : "2014-08-24 19:07:46"
        }
      ],
    "dpid" : "0000000000000003",
    "name" : "s3",
    "neighbors" : [ "0000000000000002" ],
    "ports" : [ { "gateway" : {  },
          "hw_addr" : "EE-BF-9C-E7-E3-1B",
          "name" : "s3-eth1",
          "neighbor_port_no" : "00000002",
          "neighbor_switch_dpid" : "0000000000000002",
          "port_no" : "00000001"
        },
        { "gateway" : { "ipv4" : "10.0.3.1",
              "ipv4_netmask" : "255.255.255.0",
              "ipv6" : "10::3:1",
              "ipv6_netmask" : "ffff:ff00::"
            },
          "hw_addr" : "1A-CF-70-28-57-37",
          "name" : "s3-eth2",
          "neighbor_port_no" : "",
          "neighbor_switch_dpid" : "",
          "port_no" : "00000002"
        },
        { "gateway" : { "ipv4" : "10.0.4.1",
              "ipv4_netmask" : "255.255.255.0",
              "ipv6" : "10::4:1",
              "ipv6_netmask" : "ffff:ff00::"
            },
          "hw_addr" : "B2-97-A8-07-6A-1E",
          "name" : "s3-eth3",
          "neighbor_port_no" : "",
          "neighbor_switch_dpid" : "",
          "port_no" : "00000003"
        },
        { "gateway" : {  },
          "hw_addr" : "8E-01-10-0C-2C-4A",
          "name" : "s3",
          "neighbor_port_no" : "",
          "neighbor_switch_dpid" : "",
          "port_no" : "0000fffe"
        }
      ],
    "routing_table" : [ { "last_update" : "2014-08-24 19:07:25",
          "metric" : 2,
          "next_hop" : "0000000000000002",
          "out_port" : "00000001",
          "subnet" : "10.0.2.1/24"
        },
        { "last_update" : "2014-08-24 19:07:25",
          "metric" : 2,
          "next_hop" : "0000000000000002",
          "out_port" : "00000001",
          "subnet" : "10.0.1.1/24"
        },
        { "last_update" : "2014-08-24 19:07:25",
          "metric" : 0,
          "out_port" : "00000003",
          "subnet" : "10.0.4.1/24"
        },
        { "last_update" : "2014-08-24 19:07:25",
          "metric" : 0,
          "out_port" : "00000002",
          "subnet" : "10.0.3.1/24"
        }
      ]
  }
]
```

### Get single switch

endpoint: `GET /routingflow/switch/<dpid>`

response:

```
{ "arp_table" : [ { "hw_addr" : "42-39-5F-21-B9-17",
        "ip" : "10.0.2.10",
        "last_update" : "2014-08-24 19:07:46"
      },
      { "hw_addr" : "66-EA-27-83-C0-4D",
        "ip" : "10.0.1.10",
        "last_update" : "2014-08-24 19:07:46"
      }
    ],
  "dpid" : "0000000000000001",
  "name" : "s1",
  "neighbors" : [ "0000000000000002" ],
  "ports" : [ { "gateway" : {  },
        "hw_addr" : "72-39-60-20-77-3D",
        "name" : "s1-eth1",
        "neighbor_port_no" : "00000001",
        "neighbor_switch_dpid" : "0000000000000002",
        "port_no" : "00000001"
      },
      { "gateway" : { "ipv4" : "10.0.1.1",
            "ipv4_netmask" : "255.255.255.0",
            "ipv6" : "10::1:1",
            "ipv6_netmask" : "ffff:ff00::"
          },
        "hw_addr" : "CA-AD-65-8C-28-B4",
        "name" : "s1-eth2",
        "neighbor_port_no" : "",
        "neighbor_switch_dpid" : "",
        "port_no" : "00000002"
      },
      { "gateway" : { "ipv4" : "10.0.2.1",
            "ipv4_netmask" : "255.255.255.0",
            "ipv6" : "10::2:1",
            "ipv6_netmask" : "ffff:ff00::"
          },
        "hw_addr" : "92-BD-24-38-48-9A",
        "name" : "s1-eth3",
        "neighbor_port_no" : "",
        "neighbor_switch_dpid" : "",
        "port_no" : "00000003"
      },
      { "gateway" : {  },
        "hw_addr" : "1E-23-0D-CD-01-49",
        "name" : "s1",
        "neighbor_port_no" : "",
        "neighbor_switch_dpid" : "",
        "port_no" : "0000fffe"
      }
    ],
  "routing_table" : [ { "last_update" : "2014-08-24 19:09:45",
        "metric" : 2,
        "next_hop" : "0000000000000002",
        "out_port" : "00000001",
        "subnet" : "10.0.3.1/24"
      },
      { "last_update" : "2014-08-24 19:09:45",
        "metric" : 0,
        "out_port" : "00000003",
        "subnet" : "10.0.2.1/24"
      },
      { "last_update" : "2014-08-24 19:09:45",
        "metric" : 0,
        "out_port" : "00000002",
        "subnet" : "10.0.1.1/24"
      },
      { "last_update" : "2014-08-24 19:09:45",
        "metric" : 2,
        "next_hop" : "0000000000000002",
        "out_port" : "00000001",
        "subnet" : "10.0.4.1/24"
      }
    ]
}
```

### Get ARP table of a switch

endpoint: `GET /routingflow/switch/<dpid>/arp`

response:

```
[ { "hw_addr" : "42-39-5F-21-B9-17",
    "ip" : "10.0.2.10",
    "last_update" : "2014-08-24 19:07:46"
  },
  { "hw_addr" : "66-EA-27-83-C0-4D",
    "ip" : "10.0.1.10",
    "last_update" : "2014-08-24 19:07:46"
  }
]
```

### Get all ports of a switch

endpoint: `GET /routingflow/switch/<dpid>/port`

response:

```
[ { "gateway" : {  },
    "hw_addr" : "72-39-60-20-77-3D",
    "name" : "s1-eth1",
    "neighbor_port_no" : "00000001",
    "neighbor_switch_dpid" : "0000000000000002",
    "port_no" : "00000001"
  },
  { "gateway" : { "ipv4" : "10.0.1.1",
        "ipv4_netmask" : "255.255.255.0",
        "ipv6" : "10::1:1",
        "ipv6_netmask" : "ffff:ff00::"
      },
    "hw_addr" : "CA-AD-65-8C-28-B4",
    "name" : "s1-eth2",
    "neighbor_port_no" : "",
    "neighbor_switch_dpid" : "",
    "port_no" : "00000002"
  },
  { "gateway" : { "ipv4" : "10.0.2.1",
        "ipv4_netmask" : "255.255.255.0",
        "ipv6" : "10::2:1",
        "ipv6_netmask" : "ffff:ff00::"
      },
    "hw_addr" : "92-BD-24-38-48-9A",
    "name" : "s1-eth3",
    "neighbor_port_no" : "",
    "neighbor_switch_dpid" : "",
    "port_no" : "00000003"
  },
  { "gateway" : {  },
    "hw_addr" : "1E-23-0D-CD-01-49",
    "name" : "s1",
    "neighbor_port_no" : "",
    "neighbor_switch_dpid" : "",
    "port_no" : "0000fffe"
  }
]
```

## Switch configuration

### Set gateway address of a port

endpoint: `PUT /routingflow/switch/<dpid>/port/<portno>/gateway`

body:

```
{ "ipv4" : "10.0.1.1",
  "ipv4_prefixlen" : 24,
  "ipv6" : "10::1:1",
  "ipv6_prefixlen" : 24
}
```

response:

```
{ "msg" : "OK" }
```

### Update ARP entry of a switch

endpoint: `PUT /routingflow/switch/<dpid>/arp`

body:

```
{ "hw_addr" : "42-39-5F-21-B9-17",
  "ip" : "10.0.2.10",
  "last_update" : "2014-08-24 19:07:46"
}
```
response:

```
{ "msg" : "OK" }
```

# Known Issues (To-Do)

* Slow convergence time of RIP when link down -> Implement Split Horizon to resolve it

# Contact

I am a newbie in SDN development, feel free to fork the project and make it better. If you want to know more or need to contact me regarding the project for 
anything, you can just send me a mail: [hungys@hotmail.com](mailto:hungys@hotmail.com)

This is a undergraduated CS project created by **Yu-Hsin Hung** from Electrical Engineering and Computer Science Undergraduate Honors Program,
National Chiao-Tung Universiry, Hsinchu 300, Taiwan.