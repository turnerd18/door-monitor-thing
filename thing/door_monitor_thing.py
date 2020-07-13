from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient, AWSIoTMQTTClient
from thing_settings import THING_NAME
import RPi.GPIO as GPIO
import logging
import json
import signal
import sys
import time

DEFAULT_STATE = {
    'request_door_state_topic': 'door_monitor/state/request',
    'send_door_state_topic': 'door_monitor/state/send'
}


def get_serial_number():
    # Extract serial from cpuinfo file
    cpuserial = None
    try:
        f = open('/proc/cpuinfo', 'r')
        for line in f:
            if line[0:6] == 'Serial':
                cpuserial = line[10:26]
        f.close()
    except:
        cpuserial = 'ERROR000000000'

    return cpuserial


def check_door_is_closed():
    return not GPIO.input(DOOR_SENSOR_PIN)


def make_shadow_json(desired_state):
    return json.dumps({'state': {'reported': desired_state}})


def update_callback(payload, response_status, token):
    if response_status != 'accepted':
        print('FAILED to update shadow state')


def delta_callback(payload, response_status, token):
    shadow = json.loads(payload)['state']
    did_update = False
    for key, value in shadow.items():
        if key in DEFAULT_STATE:
            if key == 'request_door_state_topic':
                mqtt_connection.unsubscribe(current_state[key])
                mqtt_connection.subscribe(value, 0, on_request_door_state)

            current_state[key] = value
            did_update = True

    if did_update:
        device_shadow_handler.shadowUpdate(make_shadow_json(current_state), update_callback, 5)


def on_request_door_state(client, userdata, message):
    print('%s | %s | %s' % (client, userdata, message))
    payload = json.dumps({'thing_name': THING_NAME, 'door_is_closed': check_door_is_closed()})
    mqtt_connection = shadow_client.getMQTTConnection()
    mqtt_connection.publish(current_state['send_door_state_topic'], payload, 0)


# Clean up when the user exits with keyboard interrupt
def cleanup_lights(signal, frame):
    GPIO.cleanup()
    sys.exit(0)


# Set Broadcom mode so we can address GPIO pins by number.
GPIO.setmode(GPIO.BCM)

# This is the GPIO pin number we have one of the door sensor
# wires attached to, the other should be attached to a ground pin.
DOOR_SENSOR_PIN = 18

# Set up the door sensor pin.
GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Set the cleanup handler for when user hits Ctrl-C to exit
signal.signal(signal.SIGINT, cleanup_lights)

logger = logging.getLogger('AWSIoTPythonSDK.core')
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

client_id = get_serial_number()
host = 'ar4m4s6ca3abs.iot.us-west-2.amazonaws.com'

shadow_client = AWSIoTMQTTShadowClient("basicShadowUpdater")

shadow_client.configureEndpoint(host, 8883)
shadow_client.configureCredentials('/deviceSDK/root-CA.crt', '/deviceSDK/%s.private.key' % THING_NAME, '/deviceSDK/%s.cert.pem' % THING_NAME)

shadow_client.configureAutoReconnectBackoffTime(1, 32, 20)
shadow_client.configureConnectDisconnectTimeout(10)  # 10 sec
shadow_client.configureMQTTOperationTimeout(5)  # 5 sec

shadow_client.connect()

device_shadow_handler = shadow_client.createShadowHandlerWithName(THING_NAME, True)

device_shadow_handler.shadowRegisterDeltaCallback(delta_callback)
current_state = {
    **DEFAULT_STATE,
    'door_is_closed': check_door_is_closed()
}
mqtt_connection = shadow_client.getMQTTConnection()
mqtt_connection.subscribe(current_state['request_door_state_topic'], 0, on_request_door_state)

device_shadow_handler.shadowUpdate(make_shadow_json(current_state), update_callback, 5)

c = AWSIoTMQTTClient()
c.configureIAMCredentials()


# Main loop
is_closed = None
while True:
    time.sleep(1)

    old_is_closed = is_closed
    is_closed = check_door_is_closed()
    if is_closed != old_is_closed:
        print('Space is occupied!' if is_closed else 'Space is unoccupied!')
        current_state['door_is_closed'] = is_closed
        device_shadow_handler.shadowUpdate(make_shadow_json(current_state), update_callback, 5)
