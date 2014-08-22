curl 127.0.0.1:8080/routingflow/switch/0000000000000001/port/00000002/gateway -X PUT -i -H "Content-Type:application/json" -d '{"ipv4": "10.0.1.1", "ipv4_prefixlen": 24, "ipv6": "10::1:1", "ipv6_prefixlen": 24}'

echo '\ngateway of h1 has been set to 10.0.1.1\n'

curl 127.0.0.1:8080/routingflow/switch/0000000000000001/port/00000003/gateway -X PUT -i -H "Content-Type:application/json" -d '{"ipv4": "10.0.2.1", "ipv4_prefixlen": 24, "ipv6": "10::2:1", "ipv6_prefixlen": 24}'

echo '\ngateway of h2 has been set to 10.0.2.1\n'

curl 127.0.0.1:8080/routingflow/switch/0000000000000003/port/00000002/gateway -X PUT -i -H "Content-Type:application/json" -d '{"ipv4": "10.0.3.1", "ipv4_prefixlen": 24, "ipv6": "10::3:1", "ipv6_prefixlen": 24}'

echo '\ngateway of h3 has been set to 10.0.3.1\n'

curl 127.0.0.1:8080/routingflow/switch/0000000000000003/port/00000003/gateway -X PUT -i -H "Content-Type:application/json" -d '{"ipv4": "10.0.4.1", "ipv4_prefixlen": 24, "ipv6": "10::4:1", "ipv6_prefixlen": 24}'

echo '\ngateway of h4 has been set to 10.0.4.1\n'
