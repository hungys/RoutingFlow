from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.node import RemoteController
from functools import partial

class TestingTopology(Topo):
    def __init__(self):
        Topo.__init__( self )

        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')

        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')

        self.addLink(s1, s2)
        self.addLink(s2, s3)
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s3)
        self.addLink(h4, s3)

def start_net():
    topo = TestingTopology()
    net = Mininet(topo=topo, controller=partial(RemoteController, ip='127.0.0.1', port=6633))
    net.start()

    h1 = net.get('h1')
    h2 = net.get('h2')
    h3 = net.get('h3')
    h4 = net.get('h4')

    h1.setIP('10.0.1.10/24')
    h2.setIP('10.0.2.10/24')
    h3.setIP('10.0.3.10/24')
    h4.setIP('10.0.4.10/24')

    h1.cmd('route add default gw 10.0.1.1')
    h2.cmd('route add default gw 10.0.2.1')
    h3.cmd('route add default gw 10.0.3.1')
    h4.cmd('route add default gw 10.0.4.1')

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    start_net()