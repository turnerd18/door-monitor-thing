from datetime import datetime
import pytz
import requests
import boto3


def query_user_and_config(thing_name):
    dynamodb = boto3.resource('dynamodb')
    monitors_table = dynamodb.Table('door_monitors')
    response = monitors_table.get_item(Key={
        'thing_name': thing_name
    })
    monitor_config = response['Item']

    users_table = dynamodb.Table('users')
    response = users_table.get_item(Key={
        'user_id': monitor_config['user_id']
    })
    user = response['Item']

    return user, monitor_config


def check_is_late_at_night(open_late_range, timezone):
    start_hour = open_late_range['start_hour']
    end_hour = open_late_range['end_hour']
    current_hour = datetime.now(timezone).hour
    if start_hour > end_hour:
        return start_hour <= current_hour <= 24 or 0 <= current_hour <= end_hour
    else:
        return start_hour <= current_hour <= end_hour


def lambda_handler(event, context):
    user, monitor_config = query_user_and_config(event['thing_name'])
    timezone = pytz.timezone(user['timezone'])

    is_late_at_night = check_is_late_at_night(monitor_config['open_late_range'], timezone)

    if event['door_is_closed'] is False and is_late_at_night:
        requests.get('https://maker.ifttt.com/trigger/garage_door_open_late/with/key/cIr8nPsCMLjntrNmn2EWEj')
        return 'Door open after hours.'

    return 'Door is closed or open during the day.'
