import sys
import boto3
import logging
from azure.mgmt.resource import SubscriptionClient
from azure.mgmt.network import NetworkManagementClient
from azure.common.client_factory import get_client_from_auth_file
from xml.etree import ElementTree

logging.basicConfig(level=logging.INFO, format="%(asctime)s :%(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# aws
aws_setting = {
    # ec2Tag is Favorite tag name eg) VPN_AZURE
    'ec2Tag': '<VPN_AZURE>',
    'accessKey': '<ACCESS_KEY>',
    'secretAccessKey': '<SECRET_ACCESS_KEY>',
    'DestinationCidrBlock': '<DESTINATION_CIDR_BLOCK>',
    'VpnGatewayId': '<VPN_GATEWAY_ID>'
}

# azure
azure_setting = {
    "subscriptionId": '<SUBSCRIPTION_ID>',
    "resourceGroupName": '<RESOURCE_GROUP_NAME>',
    "virtualNetworkGatewayConnectionName": '<VIRTUAL_NETWORK_GATEWAY_CONNECTION_NAME>',
    "virtualNetworkGatewayName": '<VIRTUAL_NETWORK_GATEWAY_NAME>',
    "localNetworkGatewayName": '<LOCAL_NETWORK_GATEWAY_NAME>',
    "virtualNetworkGatewayPublicIpName": '<VIRTUAL_NETWORK_GATEWAY_PUBLIC_IP_NAME>',
    # eg) ['10.0.0.0/16']
    "addressPrefixes": ['<ADDRESS_PREFIXES>'],
    # eg) /subscriptions/******/resourceGroups/hogehoge/providers/Microsoft.Network/virtualNetworkGateways/*******
    "virtualNetworkGateway1Id": '<VIRTUAL_NETWORK_GATEWAY1_ID>',
    "localNetworkGateway2Id": '<LOCAL_NETWORK_GATEWAY2_ID>',
    "subnetId": "<SUBNET_ID>",
    "publicIPAddressId": "<PUBLIC_IP_ADDRESS_ID>",
    # eg) Japan East
    "location": '<LOCATION>',
}

def usage_and_exit():
    print("Usage: python3 main.py [enable|disable]")
    exit()

def create_network_clinet():
    return get_client_from_auth_file(NetworkManagementClient, auth_path="../credential.json")

def create_ec2():
    return boto3.client('ec2',
        aws_access_key_id= aws_setting.get('accessKey'),
        aws_secret_access_key= aws_setting.get('secretAccessKey'),
        region_name='ap-northeast-1')

def enable():
    network_client = create_network_clinet()
    ec2 = create_ec2()

    logger.info("Azure Create VPNGateway")
    poller = network_client.virtual_network_gateways.create_or_update(
        azure_setting.get("resourceGroupName"),
        azure_setting.get("virtualNetworkGatewayName"),
        {
            "sku": {
                "name": "Basic",
                "tier": "Basic"
            },
            "gatewayType": "Vpn",
            "vpnType": "RouteBased",
            "ipConfigurations": [
                {
                    "name": azure_setting.get("virtualNetworkGatewayName"),
                    "privateIPAllocationMethod": "Dynamic",
                    "subnet": {
                        "id": azure_setting.get("subnetId"),
                    },
                    "publicIPAddress": {
                        "id": azure_setting.get("publicIPAddressId"),
                    }
                }
            ],
            "location": azure_setting.get("location"),
        })
    azure_vpn_gateway = poller.result()
    logger.info("Azure Create VPNGateway ... complete!")

    logger.info("Azure Get PublicIP")
    publicIpAddresses = network_client.public_ip_addresses.get(
        azure_setting.get("resourceGroupName"),
        azure_setting.get("virtualNetworkGatewayPublicIpName")
    )
    logger.info("Azure Get PublicIP ... complete!")

    azure_ip = publicIpAddresses.ip_address
    logger.info("Get Azure IP: {0}".format(azure_ip))

    logger.info("AWS Create VPNGateway")
    customer_gateway = ec2.create_customer_gateway(
            PublicIp= azure_ip,
            Type= "ipsec.1",
            BgpAsn= 65000)
    logger.info("AWS Create CustomerGateway ... complete!")

    vpn_gateway_id = customer_gateway.get('CustomerGateway').get('CustomerGatewayId')
    logger.info("AWS Get CustomerGatewayId : {0}".format(vpn_gateway_id))

    logger.info("AWS Create VPNConnection")
    vpn_connection = ec2.create_vpn_connection(
            CustomerGatewayId= vpn_gateway_id,
            VpnGatewayId= aws_setting.get('VpnGatewayId'),
            Type= "ipsec.1",
            Options={
                'StaticRoutesOnly': True
            })
    logger.info("AWS Create VPNConnection ... complete!")

    vpn_connection_id = vpn_connection.get('VpnConnection').get('VpnConnectionId')
    logger.info("AWS Get VpnConnectionId : {0}".format(vpn_connection_id))

    logger.info("AWS Create VPNConnection")
    vpn_connection_route = ec2.create_vpn_connection_route(
        DestinationCidrBlock= aws_setting.get('DestinationCidrBlock'),
        VpnConnectionId= vpn_connection_id
    )
    logger.info("AWS Create VPNConnection ... complete!")

    xml = vpn_connection.get('VpnConnection').get('CustomerGatewayConfiguration')
    elem = ElementTree.fromstring(xml)

    ip = elem.find('ipsec_tunnel').find('vpn_gateway').find('tunnel_outside_address').find('ip_address').text
    key = elem.find('ipsec_tunnel').find('ike').find('pre_shared_key').text
    # logger.info("AWS PublicIP: {0}\nAWS SharedKey: {1}".format(ip, key))

    logger.info("AWS Create Tags")
    create_tags = ec2.create_tags(
        Resources= [
            vpn_gateway_id,
            vpn_connection_id
        ],
        Tags= [{
            'Key': 'Name',
            'Value': aws_setting.get('ec2Tag')
        }]
    )
    logger.info("AWS Create Tags ... complete!")

    logger.info("Azure Create LocalNetworkGateway")
    poller = network_client.local_network_gateways.create_or_update(
        azure_setting.get("resourceGroupName"),
        azure_setting.get("localNetworkGatewayName"),
        {
                "gatewayIpAddress": ip,
                "localNetworkAddressSpace": {
                    "addressPrefixes": azure_setting.get("addressPrefixes")
                },
                "location": azure_setting.get("location")
        }
    )
    result = poller.result()
    logger.info("Azure Create LocalNetworkGateway ... complete!")

    logger.info("Azure Create virtualNetworkGatewayConnection")
    poller = network_client.virtual_network_gateway_connections.create_or_update(
        azure_setting.get("resourceGroupName"),
        azure_setting.get("virtualNetworkGatewayConnectionName"),
        {
            "sharedKey": key,
            "virtualNetworkGateway1": {
                "id": azure_setting.get("virtualNetworkGateway1Id")
            },
            "localNetworkGateway2": {
                "id": azure_setting.get("localNetworkGateway2Id"),
            },
            "connectionType2": "IPsec",
            "connectionProtocol": "IKEv2",
            "connectionMode": "Default",
            "location": azure_setting.get("location"),
            "connectionType": "IPsec"
        }
    )
    result = poller.result()
    logger.info("Azure Create virtualNetworkGatewayConnection ... complete!")

    logger.info("all completed !")

def disable():
    network_client = create_network_clinet()
    ec2 = create_ec2()

    logger.info("AWS Get DescribeVpnConnection")
    vpn_connections = ec2.describe_vpn_connections(
        Filters= [{
            'Name': 'tag:Name',
            'Values': [aws_setting.get('ec2Tag')]
        }]
    )
    logger.info("AWS Get DescribeVpnConnection ... complete!")

    logger.info("AWS Delete VPNConnection")
    if len(vpn_connections.get('VpnConnections')) >= 1:
        ec2.delete_vpn_connection(VpnConnectionId= vpn_connections.get('VpnConnections')[0].get('VpnConnectionId'))
        logger.info("AWS Delete VPNConnection ... complete!")
    else:
        logger.info("AWS Skip Delete VPNConnection")

    logger.info("AWS Get DescribeVpnConnection")
    customer_gateways = ec2.describe_customer_gateways(
        Filters= [{
            'Name': 'tag:Name',
            'Values': [aws_setting.get('ec2Tag')]
        }]
    )
    logger.info("AWS Get DescribeVpnConnection ... complete!")

    logger.info("AWS Delete CustomerGateways")
    if len(customer_gateways.get('CustomerGateways')) >= 1:
        ec2.delete_customer_gateway(CustomerGatewayId= customer_gateways.get('CustomerGateways')[0].get('CustomerGatewayId'))
        logger.info("AWS Delete CustomerGateways ... complete!")
    else:
        logger.info("AWS Skip Delete CustomerGateways")

    logger.info("Azure Delete VirtualNetworkGatewayConnection")
    poller = network_client.virtual_network_gateway_connections.delete(
        azure_setting.get("resourceGroupName"),
        azure_setting.get("virtualNetworkGatewayConnectionName"),
    )
    ret = poller.result()
    logger.info("Azure Delete VirtualNetworkGatewayConnection ... complete!")

    logger.info("Azure Delete VirtualNetworkGateway")
    poller = network_client.virtual_network_gateways.delete(
        azure_setting.get("resourceGroupName"),
        azure_setting.get("virtualNetworkGatewayName"),
    )
    poller.result()
    logger.info("Azure Delete VirtualNetworkGateway ... complete!")

    logger.info("Azure Delete LocalNetworkGateway")
    poller = network_client.local_network_gateways.delete(
        azure_setting.get("resourceGroupName"),
        azure_setting.get("localNetworkGatewayName"),
    )
    poller.result()
    logger.info("Azure Delete LocalNetworkGateway ... complete!")
    logger.info("all completed !")

args = sys.argv
if len(args) < 2:
    usage_and_exit()

if args[1] == 'enable':
    enable()
elif args[1] == 'disable':
    disable()
else:
    usage_and_exit()