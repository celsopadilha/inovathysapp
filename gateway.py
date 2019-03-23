import hashlib
import json
import os
import sys
import time

from paho.mqtt.client import Client as MQTTClient

from dao import Dao
from dog import Dog
from publisher import Publisher


class InovaGateway:

    def __init__(self, mqtt, dao, publisher):
        self.mqtt = mqtt
        self.publisher = publisher
        self.dao = dao
        self.dog = Dog(self.dao, self.publisher)
        self.mqttClients = dict()

        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_message = self.on_message

        self.actions = {
            0:  self.dao.getBlueprint_using_id,
            #
            10: self.dao.createEnvironment,
            11: self.dao.updateEnvironment,
            12: self.dao.deleteEnvironment,
            #
            23: self.dao.applyDeviceCommand,
            24: self.dao.setAppliedDeviceCommand,
            #
            30: self.dao.createScene,
            31: self.dao.updateScene,
            32: self.dao.deleteScene,
            33: self.dao.applySceneCommands,
            #
            40: self.dao.createUser,
            41: self.dao.updateUser,
            42: self.dao.deleteUser,
            43: self.dao.login,
        }

    def on_connect(self, client, userdata, flags, rc):
        print "MQTTClient \tCONNECTED"
        client.subscribe('system/gateway', 2)
        client.subscribe('system/admin', 2)

    def on_message(self, client, userdata, msg):
        try:
            millis = time.time()*1000
            receivedMsg = json.loads(msg.payload)
            code = receivedMsg['type']
            if msg.topic != 'system/admin' and code not in [40, 41, 42]:
                result, error, topic = self.actions[code](receivedMsg['body'])
                print result, error, topic
                self.publisher.sendMobileMsg(code, result, topic, error=error)
            elif msg.topic == 'system/admin' and code in [40, 41, 42]:
                result, error, topic = self.actions[code](receivedMsg['body'])
                print result, error, topic
                self.publisher.sendMobileMsg(code, result, topic, error=error)
            else:
                print "code 40,41,42 should be in channel system/admin"
            print str(code)+" took "+str(time.time()*1000-millis)+" ms"
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno

    def start(self):
        print "Gateway \tSTARTED"
        self.mqtt.connect('localhost')
        self.mqtt.loop_start()
        self.dog.start()
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            self.dog.stop()


# ##################################################################################################
# Main
# ##################################################################################################
if __name__ == '__main__':
    # get config
    conf_path = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'server.conf')
    config = json.load(open(conf_path))
    mqtt = MQTTClient()
    mqtt.username_pw_set(
        username=config['mqtt']['user'], password=config['mqtt']['password'])
    print 'MQTTClient \tCREATED'
    publisher = Publisher(mqtt)
    dao = Dao(username=config['mongodb']['user'], password=config['mongodb']['password'],
              host=config['mongodb']['host'], database=config['mongodb']['database'])
    InovaGateway(mqtt, dao, publisher).start()
