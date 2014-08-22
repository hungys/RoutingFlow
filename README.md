# What's RoutingFlow?

![Ryu SDN Framework](http://osrg.github.io/ryu/css/images/LogoSet02.png =250x)

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

5. RoutingFlow will triggered by topology changed event and start to advertise routing information with their neighbors, you can use ```pingall``` command in mininet CLI to test the connectivity between all nodes.

# Protocol Implementation

If you want to build your own routing protocol on RoutingFlow, you can write your custom RoutingTable and RoutingEntry class by inherit the class in ```base/rib.py```, there include some basic definitions and methods required for a routing table.

```
def update_entry(self, subnet, receive_port, neighbor_port=None, metric=0):
    raise NotImplementedError

def update_by_neighbor(self, receive_port, neighbor_port, tbl):
    raise NotImplementedError
```

For more information, you can refer ```rip.py```, it's a basic implementation of Routing Information Protocol.

# Support

I am a newbie in SDN development, feel free to fork the project and make it better. If you want to know more or need to contact me regarding the project for 
anything, you can just send me a mail: [hungys@hotmail.com](mailto:hungys@hotmail.com)

This is a undergraduated CS project created by **Yu-Hsin Hung** from Electrical Engineering and Computer Science Undergraduate Honors Program,
National Chiao-Tung Universiry, Hsinchu 300, Taiwan.