import boto3


def lambda_handler(event, context):
    client = boto3.client('iot-data')
    client.publish(
        topic='door_monitor/state/request',
        qos=0,
        payload='{}'
    )

    return 'Requesting monitor states.'