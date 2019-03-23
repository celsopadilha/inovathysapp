
import os
import sys
import time
from os import path
from threading import Thread


class Dog(Thread):
    def __init__(self, dao, publisher):
        Thread.__init__(self)
        self.path = path.abspath('/var/tmp/out')  # Unix
        # self.path = os.path.abspath('/Users/ademir/workspace/inovathys/inovathys-gateway') #Ademir
        # self.path = os.path.abspath('c:/var') # Diego

        self.dao = dao
        self.publisher = publisher
        self.last_run = 0
        self.keep_going = True
        print "Dog \t\tCREATED"

    def sleep(self):
        if self.last_run == 0:
            time.sleep(1)
        else:
            time.sleep(0.5)

    def execute(self, command):
        print "dog on_created"
        try:
            result, error, topic = self.dao.setAppliedDeviceCommand(command)

            if result is not None and error is False:
                self.publisher.sendMobileMsg(23, result, topic, error=error)
            else:
                pass
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            print sys.exc_info()

    def get_commands(self):
        return os.listdir(self.path)

    def delete_file(self, file_path):
        if path.exists(file_path):
            os.remove(file_path)

    def stop(self):
        self.keep_going = False

    def run(self):
        while self.keep_going:
            commands = self.get_commands()
            if commands:
                for i in commands:
                    self.execute(i)
                    self.delete_file(path.join(self.path, i))
                self.last_run = len(commands)
            else:
                self.sleep()
