import subprocess
from multiprocessing import Process

path = "/etc/mosquitto/accControl"

def open_arq(mode):
    global path
    return open(path,mode)

def get_lines():
    arq = open_arq('r')
    lines = arq.readlines()
    close_arq(arq)
    return lines

def close_arq(arq):
    arq.close()

def check_if_user_exists(username):
    lines = get_lines()
    for i in lines:
        if username in i:
            return True
    return False

def add_user(username,password):
    print 'adding user mqtt',
    if check_if_user_exists(username):
        return False
    else:
        arq = open_arq('a')
        arq.write("user "+username+"\ntopic write system/gateway\ntopic read system/mobile\ntopic read users/"+username+"\n\n")
        arq.close()
    print subprocess.call('sudo mosquitto_passwd -b /etc/mosquitto/passwd '+username+' '+password,shell=True),
    print subprocess.call('sudo service mosquitto restart',shell=True)

def remove_user(username):
    print 'removing user mqtt',
    if check_if_user_exists(username):
        lines = get_lines()
        print lines
        try:
            user_index_stop = user_index_start = lines.index("user "+username+"\n")
            while lines[user_index_stop] != '\n':
                user_index_stop += 1
                if user_index_stop >= len(lines)-1:
                    break
            print user_index_start,user_index_stop
            lines = lines[0:user_index_start-1] + lines[user_index_stop:]
            arq = open_arq('w')
            for i in lines:
                arq.write(i)
            arq.close()
        except Exception as e:
            print e
            try:
                arq.close()
            except Exception as e:
                print e
            return False
    else:
        return False
    print subprocess.call('sudo mosquitto_passwd -D /etc/mosquitto/passwd '+username,shell=True),
    print subprocess.call('sudo service mosquitto restart',shell=True)

