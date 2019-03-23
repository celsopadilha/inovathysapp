from bson.json_util import dumps

class Publisher:

    def __init__(self, mqtt):
        self.mqtt = mqtt
        print 'Publisher \tCREATED'

    def publish(self, topic, message):
        self.mqtt.publish(topic, message, 2, False)

    def sendMobileMsg(self, type, body, topic=None, error=False):
        message = {
            'type': type,
            'body': body,
            'error': error
        }
        message = dumps(message)
        if topic != None:
            self.publish(topic, message)
        else:
            self.publish("system/mobile", message)
