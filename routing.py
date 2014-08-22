import time
import datetime
import os
import logging
import json
from webob import Response
from eventlet import patcher
from eventlet import greenio
native_threading = patcher.original("threading")
native_queue = patcher.original("Queue")

import struct
import netaddr
from ryu.base import app_manager
from ryu.lib import hub
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import (MAIN_DISPATCHER, CONFIG_DISPATCHER)
from ryu.controller import ofp_event
from ryu import topology
from ryu.ofproto import ofproto_v1_0, nx_match
from ryu.ofproto import ether, inet
from ryu.lib.packet import (packet, ethernet, arp, icmp, icmpv6, ipv4, ipv6)
from ryu.lib import mac
from ryu.lib import dpid as dpid_lib
from ryu.lib import port_no as portno_lib
from ryu.lib import ofctl_v1_0
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
import ryu.utils

from switch import Switch
from port import Port
from gateway import Gateway

FORMAT = '%(name)s[%(levelname)s]%(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)

routing_flow_instance_name = 'routing_flow_app'
rest_body_ok = json.dumps({'msg': 'OK'})

class RoutingFlow(app_manager.RyuApp):
    ARP_TIMEOUT = 600

    FLOW_IDLE_TIMEOUT = 60
    FLOW_HARD_TIMEOUT = 600

    def __init__(self, *args, **kwargs):
        super(RoutingFlow, self).__init__(*args, **kwargs)

        # switches[dpid] = Switch
        self.switches = {}

        # Register a restful controller for this module
        wsgi = kwargs['wsgi']
        wsgi.register(RoutingFlowRestController, {routing_flow_instance_name : self})

    @set_ev_cls(topology.event.EventSwitchEnter)
    def switch_enter_handler(self, event):
        """
            event handler triggered when switch enter.
            sometimes triggered before switch_feature_handler,
            create a new Switch instance when KeyError occured.
        """
        dpid = event.switch.dp.id
        logger.info('switch enter (dpid=%s)', dpid_lib.dpid_to_str(dpid))
        try:
            s = self.switches[dpid]
        except KeyError:
            s = Switch(event.switch.dp, self.switches)
            self.switches[dpid] = s

    @set_ev_cls(topology.event.EventSwitchLeave)
    def switch_leave_handler(self, event):
        """
            event handler triggered when switch leave.
            delete the Switch object directly,
            the broadcast thread will be killed by itself when
            exception occured next time.
        """
        dpid = event.switch.dp.id
        logger.info('switch leave (dpid=%s)', dpid_lib.dpid_to_str(dpid))
        try:
            del self.switches[dpid]
        except KeyError:
            pass

    @set_ev_cls(topology.event.EventPortAdd)
    def port_add_handler(self, event):
        """
            event handler triggered when port added.
            get Swtich instance and creat a Port object.
        """
        port = Port(event.port)
        try:
            switch = self.switches[port.dpid]
            switch.ports[port.port_no] = port
            logger.info('port added, port_no=%s (dpid=%s)', portno_lib.port_no_to_str(port.port_no), dpid_lib.dpid_to_str(port.dpid))
        except:
            pass

    @set_ev_cls(topology.event.EventPortDelete)
    def port_delete_handler(self, event):
        """
            event handler triggered when port deleted.
            get Switch instance and delete specific Port object.
        """
        port = Port(event.port)
        logger.info('port deleted, port_no=%s (dpid=%s)', portno_lib.port_no_to_str(port.port_no), dpid_lib.dpid_to_str(port.dpid))
        try:
            switch = self.switches[port.dpid]
            del switch.ports[port.port_no]
        except KeyError:
            pass

    def update_port_link(self, dpid, port):
        """
            Fulfill neighbor information for specific port.
        """
        switch = self.switches[dpid]
        try:
            p = switch.ports[port.port_no]
            p.neighbor_switch_dpid = port.neighbor_switch_dpid
            p.neighbor_port_no = port.neighbor_port_no
        except KeyError:
            switch.ports[port.port_no] = port

        neighbor_switch = self.switches[port.neighbor_switch_dpid]
        switch.neighbors[neighbor_switch] = port.port_no

        logger.info('link connected: %s->%s', dpid_lib.dpid_to_str(switch.dp.id), dpid_lib.dpid_to_str(neighbor_switch.dp.id))

    @set_ev_cls(topology.event.EventLinkAdd)
    def link_add_handler(self, event):
        """
            populate link information from event argument,
            then create bidirectional link between two nodes.
        """
        src_port = Port(port = event.link.src, neighbor = event.link.dst)
        dst_port = Port(port = event.link.dst, neighbor = event.link.src)

        # Create bidirectional link
        self.update_port_link(src_port.dpid, src_port)
        self.update_port_link(dst_port.dpid, dst_port)

    def delete_link(self, port):
        """
            Clear neighbor information for specific port.
        """
        try:
            switch = self.switches[port.dpid]
            p = switch.ports[port.port_no]
        except KeyError:
            return

        p.neighbor_switch_dpid = None
        p.neighbor_port_no = None

    @set_ev_cls(topology.event.EventLinkDelete)
    def link_delete_handler(self, event):
        """
            event handler triggered when link deleted.
            delete corresponding Port object then call delete_link
            to clear neighbor information.
        """
        try:
            switch1 = self.switches[event.link.src.dpid]
            switch2 = self.switches[event.link.dst.dpid]
            del switch1.neighbors[switch2]
            del switch2.neighbors[switch1]
        except KeyError:
            return

        self.delete_link(event.link.src)
        self.delete_link(event.link.dst)
        logger.info('link disconnected: %s->%s', dpid_lib.dpid_to_str(switch1.dp.id), dpid_lib.dpid_to_str(switch2.dp.id))

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, [MAIN_DISPATCHER, CONFIG_DISPATCHER])
    def switch_feature_handler(self, event):
        """
            event handler when receiving feature information
            from switch.
        """
        dpid = event.msg.datapath_id
        try:
            switch = self.switches[dpid]
        except KeyError:
            self.switches[dpid] = Switch(event.msg.datapath, self.switches)
            switch = self.switches[dpid]

        for port_no, port in event.msg.ports.iteritems():
            if port_no not in switch.ports:
                p = Port(port = port, datapath = event.msg.datapath)
                switch.ports[port_no] = p

            p = switch.ports[port_no]

            if port_no == ofproto_v1_0.OFPP_LOCAL:
                switch.name = port.name.rstrip('\x00')

    def find_packet(self, pkt, target):
        """
            try to extract the packet and find for specific
            protocol.
        """
        for packet in pkt.protocols:
            try:
                if packet.protocol_name == target:
                    return packet
            except AttributeError:
                pass
        return None

    def handle_arp_request(self, msg, pkt, arp_pkt):
        """
            called when receiving ARP request from hosts.
            when a host send a request first time,
            it has no MAC address information for its gateway,
            so it will send a ARP request to the switch.
        """
        switch = self.switches[msg.datapath.id]
        in_port_no = msg.in_port
        req_dst_ip = arp_pkt.dst_ip
        req_src_ip = arp_pkt.src_ip
        port = switch.ports[in_port_no]

        logger.info('receive ARP request: who has %s? tell %s (dpid=%s)', str(req_dst_ip), str(req_src_ip), dpid_lib.dpid_to_str(msg.datapath.id))

        # handle ARP request for gateway
        if port.gateway and port.gateway.ipv4 != netaddr.IPAddress(req_dst_ip):
            logger.warning('cannot reply ARP, please check gateway configuration. (dpid=%s)', dpid_lib.dpid_to_str(msg.datapath.id))
            return

        datapath = msg.datapath
        reply_src_mac = str(port.hw_addr)
        ether_layer = self.find_packet(pkt, 'ethernet')

        # pack a ARP reply packet
        e = ethernet.ethernet(dst = ether_layer.src, src = reply_src_mac,
                                ethertype = ether.ETH_TYPE_ARP)
        a = arp.arp(hwtype = arp.ARP_HW_TYPE_ETHERNET,
                    proto = ether.ETH_TYPE_IP,
                    hlen = 6, plen = 4, opcode = arp.ARP_REPLY,
                    src_mac = reply_src_mac, src_ip = req_dst_ip,
                    dst_mac = arp_pkt.src_mac, dst_ip = req_src_ip)
        p = packet.Packet()
        p.add_protocol(e)
        p.add_protocol(a)
        p.serialize()

        datapath.send_packet_out(in_port = ofproto_v1_0.OFPP_NONE,
                actions = [datapath.ofproto_parser.OFPActionOutput(in_port_no)],
                data = p.data)

        logger.info('ARP replied: %s - %s', reply_src_mac, req_dst_ip)

    def handle_arp_reply(self, msg, pkt, arp_pkt):
        """
            called when receiving ARP reply from hosts.
            the host will send their MAC address back to switch.
            (1) save the MAC address information in ARP table.
            (2) try to resend the packet in the buffer.
            (3) remove the sent packet from the buffer queue.
        """
        switch = self.switches[msg.datapath.id]
        in_port_no = msg.in_port
        gateway = switch.ports[in_port_no].gateway
        replied_buffer = []

        logger.info('receive ARP reply: from %s (dpid=%s)', str(arp_pkt.src_ip), dpid_lib.dpid_to_str(msg.datapath.id))

        if gateway and gateway.ipv4 == netaddr.IPAddress(arp_pkt.dst_ip):
            self.update_arp_entry(switch, pkt)
            # try to resend the buffered packets
            for i in xrange(len(switch.msg_buffer)):
                msg, pkt, outport_no = switch.msg_buffer[i]
                if self.deliver_to_host(msg, pkt, outport_no):
                    replied_buffer.append(i)

            replied_buffer.sort(reverse = True)
            for i in replied_buffer:
                switch.msg_buffer.pop(i)

    def update_arp_entry(self, switch, packet):
        """
            update MAC address information in ARP table.
        """
        ether_layer = self.find_packet(packet, 'ethernet')
        
        ip_layer = self.find_packet(packet, 'ipv4')
        if ip_layer is None:
            ip_layer = self.find_packet(packet, 'arp')
            ip_layer.src = ip_layer.src_ip

        logger.info('update ARP entry: %s - %s (dpid=%s)', ether_layer.src, ip_layer.src, dpid_lib.dpid_to_str(switch.dp.id))
        switch.ip_to_mac[netaddr.IPAddress(ip_layer.src)] = (netaddr.EUI(ether_layer.src), time.time())

    def handle_arp(self, msg, pkt, arp_pkt):
        """
            called when receiving ARP packet,
            inspect the opcode then call corresponding methods.
        """
        if arp_pkt.opcode == arp.ARP_REQUEST:
            self.handle_arp_request(msg, pkt, arp_pkt)
        elif arp_pkt.opcode == arp.ARP_REPLY:
            self.handle_arp_reply(msg, pkt, arp_pkt)
        else:
            return

    def send_arp_request(self, datapath, outport_no, dst_ip):
        """
            pack and send ARP request for specific IP address.
        """
        src_mac_addr = str(self.switches[datapath.id].ports[outport_no].hw_addr)
        src_ip = str(self.switches[datapath.id].ports[outport_no].gateway.ipv4)
        dst_ip = str(dst_ip)
        p = packet.Packet()
        e = ethernet.ethernet(dst = mac.BROADCAST_STR,
            src = src_mac_addr, ethertype = ether.ETH_TYPE_ARP)
        p.add_protocol(e)
        a = arp.arp_ip(opcode = arp.ARP_REQUEST, src_mac = src_mac_addr,
                src_ip = src_ip, dst_mac = mac.DONTCARE_STR,
                dst_ip = dst_ip)
        p.add_protocol(a)
        p.serialize()

        datapath.send_packet_out(in_port = ofproto_v1_0.OFPP_NONE,
            actions = [datapath.ofproto_parser.OFPActionOutput(outport_no)],
            data = p.data)

        logger.info('ARP request sent: who has %s? tell %s (dpid=%s)', dst_ip, src_ip, dpid_lib.dpid_to_str(datapath.id))

    def handle_ip(self, msg, pkt, protocol_pkt):
        """
            handler for IP packet (currently not support ipv6)
            (1) drop non-ipv4 packet.
            (2) drop broadcast packet to 255.255.255.255
            (3) try to deliver packet to the host if output port matched.
        """
        if isinstance(protocol_pkt, ipv4.ipv4) == False:
            logger.warning('cannot find ipv4 packet to process')
            return

        src_switch = self.switches[msg.datapath.id]

        ip_layer = self.find_packet(pkt, 'ipv4')

        if str(ip_layer.dst) == '255.255.255.255':
            return

        outport_no = src_switch.find_outport_by_ip(ip_layer.dst)
        if outport_no:
            self.deliver_to_host(msg, pkt, outport_no)
        else:
            logger.warning('cannot find output port for %s (dpid=%s)', str(ip_layer.dst), dpid_lib.dpid_to_str(msg.datapath.id))

    def deliver_to_host(self, msg, pkt, outport_no):
        """
            deliver packet to host if the switch owns that subnet.
            (1) find ARP entry for destination IP address.
                if failed, send ARP request and buffer the packet
            (2) create a FlowMod packet.
            (3) send FlowMod and PacketOut.
        """
        ip_layer = self.find_packet(pkt, 'ipv4')
        dp = msg.datapath
        switch = self.switches[dp.id]
        ipDestAddr = netaddr.IPAddress(ip_layer.dst)

        logger.info('final switch arrived, try to deliver to %s (dpid=%s)', str(ipDestAddr), dpid_lib.dpid_to_str(msg.datapath.id))

        try:
            mac_addr = switch.ip_to_mac[ipDestAddr][0]
        except KeyError:
            logger.info('no ARP entry for %s, packet buffered', str(ipDestAddr))
            self.send_arp_request(msg.datapath, outport_no, ipDestAddr)
            switch.msg_buffer.append((msg, pkt, outport_no))
            return False

        # match by destination IP address
        match = ofctl_v1_0.to_match(dp, {'nw_dst': str(ipDestAddr), 'dl_type': '2048', 'nw_proto': '1'})
        
        # rewrite source MAC address with gateway's MAC address
        # rewrite destination MAC address with host's MAC address
        # set output port
        actions = []
        actions.append(dp.ofproto_parser.OFPActionSetDlSrc(switch.ports[outport_no].hw_addr.packed))
        actions.append(dp.ofproto_parser.OFPActionSetDlDst(mac_addr.packed))
        actions.append(dp.ofproto_parser.OFPActionOutput(outport_no))

        mod = dp.ofproto_parser.OFPFlowMod(
                    datapath = dp, match = match,
                    priority = 1, cookie = 0, actions = actions,
                    command = dp.ofproto.OFPFC_ADD)

        out = dp.ofproto_parser.OFPPacketOut(
            datapath = dp, buffer_id = msg.buffer_id,
            in_port = msg.in_port, actions = actions)

        dp.send_msg(mod)
        dp.send_msg(out)

        logger.info('FlowMod and PacketOut sent, packet delivered to %s', str(ipDestAddr))
        return True

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        """
            event handler triggered when receiving PacketIn from switch,
            extract the packet and call corresponding method.
        """
        data = event.msg.data
        pkt = packet.Packet(data)

        for p in pkt.protocols:
            if isinstance(p, arp.arp):
                self.handle_arp(event.msg, pkt, p)
            elif isinstance(p, ipv4.ipv4):
                self.handle_ip(event.msg, pkt, p)
            elif isinstance(p, ipv6.ipv6):
                # logger.warning('ipv6 is currently not supported.')
                pass
            else:
                pass

class RoutingFlowRestController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(RoutingFlowRestController, self).__init__(req, link, data, **config)
        self.routing_flow_app = data[routing_flow_instance_name]

    # get all switches
    # GET /routingflow/switch
    @route('routingflow', '/routingflow/switch', methods=['GET'])
    def get_all_switch(self, req, **kwargs):
        body = json.dumps([switch.to_dict() for (dpid, switch) in self.routing_flow_app.switches.items()])
        return Response(content_type='application/json', body=body)

    # get single switch
    # GET /routingflow/switch/{dpid}
    @route('routingflow', '/routingflow/switch/{dpid}', methods=['GET'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_switch(self, req, **kwargs):
        body = json.dumps(self.routing_flow_app.switches[dpid_lib.str_to_dpid(kwargs['dpid'])].to_dict())
        return Response(content_type='application/json', body=body)

    # get arp table of switch
    # GET /routingflow/switch/{dpid}/arp
    @route('routingflow', '/routingflow/switch/{dpid}/arp', methods=['GET'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_switch_arp(self, req, **kwargs):
        body = json.dumps(self.routing_flow_app.switches[dpid_lib.str_to_dpid(kwargs['dpid'])].get_arp_list())
        return Response(content_type='application/json', body=body)

    # add or update ARP entry of switch
    # PUT /routingflow/switch/{dpid}/arp
    @route('routingflow', '/routingflow/switch/{dpid}/arp', methods=['PUT'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def put_switch_arp(self, req, **kwargs):
        try:
            switch = self.routing_flow_app.switches[dpid_lib.str_to_dpid(kwargs['dpid'])]
        except:
            return Response(status=404)

        payload = json.loads(req.body)
        switch.ip_to_mac[netaddr.IPAddress(payload['ip'])] = (payload['hw_addr'], time.time())

        return Response(status=200, body=rest_body_ok)

    # get all ports of switch
    # GET /routingflow/switch/{dpid}/port
    @route('routingflow', '/routingflow/switch/{dpid}/port', methods=['GET'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_switch_port(self, req, **kwargs):
        body = json.dumps([port.to_dict() for (port_no, port) in self.routing_flow_app.switches[dpid_lib.str_to_dpid(kwargs['dpid'])].ports.items()])
        return Response(content_type='application/json', body=body)

    # update gateway info of switch
    # PUT /routingflow/switch/{dpid}/port/{portno}/gateway
    @route('routingflow', '/routingflow/switch/{dpid}/port/{portno}/gateway', methods=['PUT'], requirements={'dpid': dpid_lib.DPID_PATTERN, 'portno': portno_lib.PORT_NO_PATTERN})
    def put_switch_port_gateway(self, req, **kwargs):
        try:
            switch = self.routing_flow_app.switches[dpid_lib.str_to_dpid(kwargs['dpid'])]
        except:
            return Response(status=404)

        payload = json.loads(req.body)

        switch.update_gateway_with_prefixlen(ipv4=payload['ipv4'], ipv4_prefixlen=int(payload['ipv4_prefixlen']),
                                ipv6=payload['ipv6'], ipv6_prefixlen=int(payload['ipv6_prefixlen']), port_no=portno_lib.str_to_port_no(kwargs['portno']))
            
        return Response(status=200, body=rest_body_ok)
