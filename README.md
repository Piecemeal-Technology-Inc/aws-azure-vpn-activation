# aws-azure-vpn-activation

This is a sample script to activate an AWS and Azure VPN Gateway.

# Environment (confirmed operation)

* Python 3.8.2

# Setup

\* The following is an example on Windows 10 WSL 2.0</br>

##  Installation Modules
```
python -m pip install boto3
python -m pip install azure-mgmt-storage
```

> Azure SDK for Python
https://docs.microsoft.com/ja-jp/azure/developer/python/azure-sdk-install

> AWS SDK for Python
https://aws.amazon.com/jp/sdk-for-python/


## Rewrite the source

Rewrite to the values of your Azure and AWS environment.
```
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
```

### Usage

To Enable
```
python3 ./main.py enable
```

To Disable
```
python3 ./main.py disable
```
