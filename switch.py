import netaddr
import logging
import time
import datetime
from threading import Thread

from ryu.topology import switches
from ryu.topology.switches import Port as Port_type
from ryu.lib.dpid import dpid_to_str
from ryu.lib.port_no import port_no_to_str
from ryu.lib import hub
from ryu.ofproto.ofproto_v1_0_parser import OFPPhyPort
from ryu.lib import ofctl_v1_0

from rip import RIPRoutingTable as RoutingTable
from rip import RIPRoutingEntry as RoutingEntry
from gateway import Gateway

logger = logging.getLogger(__name__)

FLOW_IDLE_TIMEOUT = 60
FLOW_HARD_TIMEOUT = 600

class Switch(switches.Switch):
    def __init__(self, dp, s):
        super(Switch, self).__init__(dp)

        self.name = None

        # switches[dpid] = Switch
        # reference to routing.py
        self.switches = s
        
        # neigbors[Switch] = port_no
        self.neighbors = {}

        # ports[port_no] = Port
        # overshadow super.ports
        self.ports = {}

        # ARP table
        # ip_to_mac[ip_addr] = (mac_addr, time_stamp)
        self.ip_to_mac = {}

        # temporarily store packets without ARP entry
        self.msg_buffer = []

        self.queue = hub.Queue()
        self.tbl = RoutingTable(self.dp.id)

        self.init_thread()

    def init_thread(self):
        logger.info('broadcast thread start with interval %ds (dpid=%s)', self.tbl.advertise_interval, dpid_to_str(self.dp.id))
        broadcast_thread = Thread(target=self.broadcast_thread)
        broadcast_thread.setDaemon(True)
        broadcast_thread.start()

    def broadcast_thread(self):
        while True:
            logger.info('broadcast routing table (dpid=%s)', dpid_to_str(self.dp.id))
            for port_no, port in self.ports.items():
                if port.neighbor_switch_dpid:
                    self.switches[port.neighbor_switch_dpid].add_to_queue((port, self.tbl))
                    self.switches[port.neighbor_switch_dpid].trigger_update()
            time.sleep(self.tbl.advertise_interval)

    def process_queued_msg(self):
        while not self.queue.empty():
            port, tbl = self.queue.get()
            reveived_port = self.switches[port.neighbor_switch_dpid].ports[port.neighbor_port_no]
            self.tbl.update_by_neighbor(reveived_port, port, tbl)
        self.deploy_routing_table()

    def add_to_queue(self, msg):
        if not self.queue.full():
            self.queue.put(msg)

    def trigger_update(self):
        update_thread = Thread(target=self.process_queued_msg)
        update_thread.setDaemon(True)
        update_thread.start()

    def get_arp_list(self):
        arp_list = []
        for ip, value in self.ip_to_mac.items():
            arp_list.append({'ip': str(ip),
                             'hw_addr': str(value[0]),
                             'last_update': datetime.datetime.fromtimestamp(value[1]).strftime('%Y-%m-%d %H:%M:%S')})

        return arp_list

    def get_routing_table(self):
        routing_tbl = []
        for subnet, entry in self.tbl.items():
            d = entry.to_dict()
            d['subnet'] = str(subnet)
            routing_tbl.append(d)

        return routing_tbl

    def deploy_routing_table(self):
        for subnet, entry in self.tbl.items():
            if entry.neighbor_port:
                self.deploy_flow_entry(subnet=subnet, outport=entry.receive_port, dstport=entry.neighbor_port)

    def deploy_flow_entry(self, subnet, outport, dstport):
        if outport is None:
            logger.warning('fail to deploy flow entry, cant find output port for %s', str(subnet))
            return

        match = ofctl_v1_0.to_match(self.dp, {'nw_dst': str(subnet), 'dl_type': '2048', 'nw_proto': '1'})
        actions = []
        actions.append(self.dp.ofproto_parser.OFPActionSetDlSrc(outport.hw_addr.packed))
        actions.append(self.dp.ofproto_parser.OFPActionSetDlDst(dstport.hw_addr.packed))
        actions.append(self.dp.ofproto_parser.OFPActionOutput(outport.port_no))

        mod = self.dp.ofproto_parser.OFPFlowMod(
                    datapath = self.dp, match = match,
                    priority = 1, cookie = 0, actions = actions,
                    command = self.dp.ofproto.OFPFC_ADD)

        self.dp.send_msg(mod)

    def find_outport_by_subnet(self, subnet):
        for port_no, port in self.ports.items():
            if port.gateway and port.gateway.ipv4_subnet == subnet:
                return port_no
        return None

    def find_outport_by_ip(self, dst_ip):
        for port_no, port in self.ports.items():
            if port.gateway and dst_ip in port.gateway.ipv4_subnet:
                return port_no
        return None

    def update_gateway_with_prefixlen(self, ipv4='', ipv4_prefixlen=0, 
                                ipv6='', ipv6_prefixlen=0, port_no=''):
        port = self.ports[port_no]

        if port.gateway is None:
            port.gateway = Gateway(name=port.name, port_no=port.port_no,
                                ipv4=ipv4, ipv4_prefixlen=ipv4_prefixlen,
                                ipv6=ipv6, ipv6_prefixlen=ipv6_prefixlen)
        else:
            port.gateway.name = port.name
            port.gateway.ipv4 = netaddr.IPAddress(ipv4)
            port.gateway.ipv4_subnet = netaddr.IPNetwork(ipv4 + '/' + str(ipv4_prefixlen))
            port.gateway.ipv6 = netaddr.IPAddress(ipv6)
            port.gateway.ipv6_subnet = netaddr.IPNetwork(ipv6 + '/' + str(ipv6_prefixlen))
            port.gateway.port_no = port.port_no

        self.tbl.update_entry(subnet=port.gateway.ipv4_subnet, receive_port=port, metric=0)

    def to_dict(self):
        return {'dpid': dpid_to_str(self.dp.id),
                'name': self.name,
                'neighbors': [dpid_to_str(switch.dp.id) for switch in self.neighbors],
                'ports': [port.to_dict() for (port_no, port) in self.ports.items()],
                'arp_table': self.get_arp_list(),
                'routing_table': self.get_routing_table()}

    def __eq__(self, s):
        try:
            if self.dp.id == s.dp.id:
                return True
        except:
            return False
        return False

    def __str__(self):
        return '<Switch: %s>' % self.name


