import netaddr

class Gateway(object):
    def __init__(self, name='', ipv4='', ipv4_prefixlen='', 
            ipv6='', ipv6_prefixlen='', port_no=''):
        self.name = name
        self.ipv4 = netaddr.IPAddress(ipv4)
        self.ipv4_subnet = netaddr.IPNetwork(ipv4 + '/' + str(ipv4_prefixlen))
        self.ipv6 = netaddr.IPAddress(ipv6)
        self.ipv6_subnet = netaddr.IPNetwork(ipv6 + '/' + str(ipv6_prefixlen))
        self.port_no = port_no

    def __str__(self):
        return 'Gateway<name=%s, ipv4=%s, ipv6=%s, port_no=%s>'\
            % (self.name, str(self.ipv4), str(self.ipv6), self.port_no)

    def to_dict(self):
        return {'ipv4': str(self.ipv4),
                'ipv4_netmask': str(self.ipv4_subnet.netmask),
                'ipv6': str(self.ipv6),
                'ipv6_netmask': str(self.ipv6_subnet.netmask)}

        return d