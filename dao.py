import hashlib
import os
import subprocess
import sys
import uuid
from threading import Thread
from time import sleep
from urllib import quote_plus

from bson.json_util import dumps
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import OperationFailure

import acl as AccessControl


class Dao:

    def __init__(self,username,password,host,database):
        uri = "mongodb://%s:%s@%s/%s" %(quote_plus(username),quote_plus(password),quote_plus(host),quote_plus(database)) #use this URI instead
        self.mongo = MongoClient(uri) #TODO remove hardcoded auth params
        #self.mongo = MongoClient()                                        # No Auth
        self.db = self.mongo.test
        self.cache = {}
        print 'Dao \t\tCREATED'

    def invalidate_cache(self):
        self.cache = {}

    def getBlueprint(self, user):
        data = {}

        data['environments'] = []

        if user['admin'] == True:
            data['users'] = []
            print'environments...'
            for env in self.db.environments.find():
                print env
                data['environments'].append(env)
            print'users...'
            for u in self.db.users.find():
                if not u['admin']:
                    data['users'].append(u)
        else:
            print'environments...'
            for env in self.db.environments.find({'users': user['_id']}):
                print env
                data['environments'].append(env)
        data['scenes'] = []
        print'scenes...'
        for scene in self.db.scenes.find({'owner': user['_id']}):
            print scene
            data['scenes'].append(scene)
        self.cache[user['_id']] = (data,user['email'])
        return data


    def getBlueprint_using_id(self,data):
        try:
            if data['id'] in self.cache.keys():
                user = {
                    'email':self.cache[data['id']][1]
                    }
                data = self.cache[data['id']][0]
            else:
                last_id = data['id']

                user = self.db.users.find_one({"_id": data['id']})  
                data = self.getBlueprint(user)

                self.cache[last_id] = (data,user['email'])
            return data, False, "users/"+user['email']
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None


    ''' Environment '''

    def createEnvironment(self, data):
        try:
            env = {
                '_id': str(uuid.uuid4()),
                'name': data['name'],
                'devices': [],
                'users': data['users'] if 'users' in data else []
            }
            insert = self.db.environments.insert_one(env)
            for dev in data['devices']:
                self.db.environments.find_one_and_update({ "_id": insert.inserted_id },
                    { "$addToSet": { "devices":
                        {'_id': str(uuid.uuid4()),
                        'name': dev['name'],
                        'values': dev['values'] if 'values' in data else [0,0,0,0,0,0,0,0,0],
                        'devh': dev['devh'],
                        'devl': dev['devl'],
                        'type': dev['type'],
                        'envId': insert.inserted_id} } })
            env = self.db.environments.find_one({ "_id": insert.inserted_id })
            self.invalidate_cache()
            print 'Environment {} created'.format(env['name'])
            return env, False, None
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb
            import traceback; traceback.print_exc();
            return None, True, None


    def updateEnvironment(self, data):
        try:
            env = {
                'name': data['name'],
                'devices': data['devices'],
                'users': data['users']
            }
            for device in env['devices']:
                device['envId'] = data['id']
            origDevs = [(x['devh'],x['devl']) for x in self.db.environments.find_one({'_id':data['id']})['devices']]
            env = self.db.environments.find_one_and_replace({ "_id": data['id'] },
                env, return_document=ReturnDocument.AFTER)

            newDevs = [(x['devh'],x['devl']) for x in env['devices']]
            removeDevs = []
            
            for i in origDevs:
                if i not in newDevs:
                    removeDevs.append([str(i[0]),str(i[1])])

            self.removeDevScenes(removeDevs)

            self.invalidate_cache()
            print 'Environment {} updated'.format(env['name'])
            return env, False, None
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None


    def removeDevScenes(self,removeDevs):
        print removeDevs
        scenes = self.db.scenes.find({'devices':{"$in":removeDevs}})

        for i in scenes:
            commands = []
            devices = []
            for j in i['commands']:
                if j.split(',')[6:8] not in removeDevs:
                    commands.append(j)
                    devices.append(j.split(',')[6:8])
            i['commands'] = commands
            i['devices'] = devices
            self.db.scenes.find_one_and_replace({'_id':i['_id']},i)
        
        print list(scenes)

    def deleteEnvironment(self, data):
        try:
            env = self.db.environments.find_one_and_delete({ "_id": data['id'] })
            self.invalidate_cache()
            self.removeDevScenes([ [x['devh'],x['devl']] for x in env['devices'] ])
            print 'Environment {} deleted'.format(data['id'])
            return env, False, None
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None


    ''' Device '''


    def createDevice(self, data):
        try:
            device = {
                '_id': str(uuid.uuid4()),
                'name': data['name'],
                'values': data['values'] if 'values' in data else [0,0,0,0,0,0,0,0,0],
                'devh': data['devh'],
                'devl': data['devl'],
                'type': data['type'],
                'envId': data['envId']
                # TODO Commands
            }
            env = self.db.environments.find_one_and_update({ "_id": data['envId'] },
                { "$addToSet": { "devices":device } }, return_document=ReturnDocument.AFTER)
            self.invalidate_cache()
            print 'Device {} created'.format(data['name'])
            return env, False, None
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None


    def updateDevice(self, data):
        try:
            env = self.db.environments.find_one({'devices':{'$elemMatch':{'devh': data['devh'],
                'devl': data['devl']}}})
            for i in range(0, len(env['devices'])):
                if env['devices'][i]['devh'] == data['devh'] and env['devices'][i]['devl'] == data['devl']:
                    env = self.db.environments.find_one_and_update({'devices':{'$elemMatch':{
                        'devh':data['devh'], 'devl':data['devl']}}},
                        {'$set':{'devices.'+str(i)+'.name': data['name']}}, return_document=ReturnDocument.AFTER)
                    break
            self.invalidate_cache()
            print 'Device {} updated'.format(data['name'])
            return env, False, None
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None


    def deleteDevice(self, data):
        try:
            env = self.db.environments.find_one_and_update({"_id": data['envId']} ,
                {"$pull": {'devices':{'$elemMatch':{ data['_id']}}}}, return_document=ReturnDocument.AFTER)
            # TODO remove device commands from scenes
            self.invalidate_cache()
            print 'Device {} deleted'.format(data['_id'])
            return device, False, None
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None


    def applyDeviceCommand(self, data):
        try:
            file = open('/var/tmp/in/'+str(data),"w+")
            file.close()
            return None, False, None
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None


    def setAppliedDeviceCommand(self, data):
        try:
            command = data.split(",")
	    print command
            if int(command[8]) == 250:
                return None, True, 'mobile'
            values = map(int, command[9:18])
            env = self.db.environments.find_one({'devices':{'$elemMatch':{
                'devh':int(command[6]), 'devl':int(command[7])}}})
            print '>>>>', env
            if env:
                for i in range(0, len(env['devices'])):
                    if env['devices'][i]['devh'] == int(command[6]) and env['devices'][i]['devl'] == int(command[7]):
                        self.db.environments.find_one_and_update({'devices':{'$elemMatch':{
                            'devh':int(command[6]), 'devl':int(command[7])}}},
                            {'$set':{'devices.'+str(i)+'.values': values}})
                        break
                env = self.db.environments.find_one({'devices':{'$elemMatch':{
                    'devh':int(command[6]), 'devl':int(command[7])}}})
                self.invalidate_cache()
                return env, False, None
            else:
                self.invalidate_cache()
                return env, True, None
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None


    ''' Scene '''

    def createScene(self, data):
        try:
            devices = []
            for i in data['commands']:
                devices.append(i.split(',')[6:8])
            print devices
            scene = {
                '_id': str(uuid.uuid4()),
                'name': data['name'],
                'devices':devices,
                'value': data['value'] if 'value' in data else 0,
                'owner': data['owner'],
                'commands': data['commands']
            }
            result = self.db.scenes.insert_one(scene)
            insertedScene = self.db.scenes.find_one({ "_id": result.inserted_id })
            self.invalidate_cache()
            print 'Scene {} created'.format(data['name'])
            return insertedScene, False, None
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None


    def updateScene(self, data):
        try:
            scene = {
                'name': data['name'],
                'value': data['value'] if 'value' in data else 0,
                'owner': data['userId'],
                'commands': data['commands']
            }
            scene = self.db.scenes.find_one_and_replace({ "_id": data['id'] }, scene,
                return_document=ReturnDocument.AFTER)
            self.invalidate_cache()
            print 'Scene {} updated'.format(scene['name'])
            return scene, False, None
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None


    def deleteScene(self, data):
        try:
            scene = self.db.scenes.find_one_and_delete({ "_id": data['id'] })
            self.invalidate_cache()
            print 'Scene {} deleted'.format(data['id'])
            return scene, False, None
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None


    def sceneCommandsThread(arg, commands):
        print 'Command Thread'
        for i in range(0, len(commands)):
            print 'Applying command {}'.format(i)
            try:
                file = open('/var/tmp/in/'+str(commands[i]),"w+")
                file.close()
            except:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print exc_type, fname, exc_tb.tb_lineno
                return None, True, None
            sleep(1)


    def applySceneCommands(self, data):
        try:
            print "Applying scene..."
            print data['commands']
            thread = Thread(target = self.sceneCommandsThread, args = [data['commands']])
            thread.start()
            # thread.join()
            print "Scene applied!"
            return None, False, None
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None

    ''' User '''

    def createUser(self, data):
        try:
            userExists = bool(self.db.users.find_one({ "email": data['email'] }))
            if userExists:
                raise OperationFailure('User exists')
            user = {
                '_id': str(uuid.uuid4()),
                'name': data['name'],
                'password': hashlib.md5(data['password']).hexdigest(),
                'email': data['email'],
                'admin': data['admin'] if 'admin' in data else False,
            }
            user = self.db.users.insert_one(user)
            insertedUser = self.db.users.find_one({ "_id": user.inserted_id })
            if 'environments' in data:
                for envId in data['environments']:
                    print envId
                    self.db.environments.update_one({ "_id": envId }, { "$addToSet": { "users": insertedUser['_id'] } })
                    env = self.db.environments.find_one({ "_id": envId })
                    self.invalidate_cache()
            print 'User {} created'.format(data['name'])
            AccessControl.add_user(data['email'],data['password'])
            return insertedUser, False, 'users/admin'
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None


    def updateUser(self, data):
        try:
            updates = {}
            if 'password' in data:
                updates['$set'] = {
                    'name': data['name'],
                    'password': hashlib.md5(data['password']).hexdigest()
                }
            else:
                updates['$set'] = {
                    'name': data['name']
                }
            user = self.db.users.find_one_and_update({ "_id": data['id'] }, updates,
                return_document=ReturnDocument.AFTER)
            del user['password']
            print 'User {} updated'.format(user['name'])
            subprocess.call('sudo mosquitto_passwd -b /etc/mosquitto/passwd '+data['email']+' '+data['password'],shell=True)
            subprocess.call('sudo service mosquitto restart',shell=True)
            return user, False, None
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, 'users/admin'


    def deleteUser(self, data):
        try:
            self.db.scenes.remove({'owner': data['id']})
            self.db.environments.update_many({ "users": { "$in": [data['id']] } }, { "$pull": { "users": data["id"] } } )
            self.invalidate_cache()
            user = self.db.users.find_one_and_delete({ "_id": data['id'] })
            del user['password']
            print 'User {} deleted'.format(user['name'])
            AccessControl.remove_user(user['email'])
            return user, False, 'users/admin'
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None


    def login(self, data):
        try:
            user = self.db.users.find_one({"email": data['username']})   

            if user is None:
                return 'Invalid Credentials!', True, None
            if user['password'] != hashlib.md5(data['password']).hexdigest():
                return "Invalid Password!", True, None

            del user['password']
            print data
            data = {
                'user': user,
                'blueprint': self.getBlueprint(user)
            }

            print 'User {} logged in'.format(user['name'])
            return data, False, "users/"+user['email']
        except OperationFailure as e:
            print e.details
            return None, True, None
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print exc_type, fname, exc_tb.tb_lineno
            return None, True, None
