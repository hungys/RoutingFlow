import netaddr
import logging

from ryu.topology import switches
from ryu.topology.switches import Port as Port_type
from ryu.lib.dpid import dpid_to_str
from ryu.lib.port_no import port_no_to_str
from ryu.ofproto.ofproto_v1_0_parser import OFPPhyPort

logger = logging.getLogger(__name__)

class Port(switches.Port):
    def __init__(self, port, neighbor=None, datapath=None):
        self.neighbor_switch_dpid = None
        self.neighbor_port_no = None
        self.gateway = None

        if isinstance(port, Port_type): # port to neighbor switch
            self.dpid = port.dpid
            self._ofproto = port._ofproto
            self._config = port._config
            self._state = port._state
            self.port_no = port.port_no
            self.hw_addr = netaddr.EUI(port.hw_addr)
            self.name = port.name

            if neighbor:
                self.neighbor_switch_dpid = neighbor.dpid
                self.neighbor_port_no = neighbor.port_no
        elif isinstance(port, OFPPhyPort): # ofp_phy_port
            self.dpid = datapath.id 
            self._ofproto = datapath.ofproto
            self._config = port.config
            self._state = port.state
            self.port_no = port.port_no
            self.hw_addr = netaddr.EUI(port.hw_addr)
            self.name = port.name
        else:
            raise AttributeError

    def to_dict(self):
        d = {'port_no': port_no_to_str(self.port_no),
             'hw_addr': str(self.hw_addr),
             'name': self.name.rstrip('\0')}

        if self.gateway:
            d['gateway'] = self.gateway.to_dict()
        else:
            d['gateway'] = {}

        if self.neighbor_switch_dpid:
            d['neighbor_switch_dpid'] = dpid_to_str(self.neighbor_switch_dpid)
            d['neighbor_port_no'] = port_no_to_str(self.neighbor_port_no)
        else:
            d['neighbor_switch_dpid'] = ''
            d['neighbor_port_no'] = ''

        return d