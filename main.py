#!/usr/bin/python3
from uuid import UUID
import requests
import time
from client import Client
import logging
import subprocess
import json
import os
import signal

def kill_proc(proc):
    commands = "ps aux| grep '%s'|grep -v grep " % proc
    out = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE)
    infos = out.stdout.read().splitlines()
    pid_list = []
    if len(infos) >= 1:
        for k in infos:
            proc_id = k.split()[1]
            if proc_id not in pid_list:
                os.kill(int(proc_id.decode()), 1)
    time.sleep(3)

def handle(sig, frame):
    kill_proc('v2ray')
    exit(sig)
    return frame



def get_config(urls):
    # config info
    config = None
    n = 0
    while n < 3:
        try:
            config = requests.get(urls)
            break
        except requests.exceptions.ConnectionError as f:
            logging.warning(f.args[0].reason)
            time.sleep(5)
            n += 1
    if config and config.status_code == 200:
        config_dict = json.loads(config.text)
        return config_dict
    elif config.status_code < 500:
        logging.error(json.loads(config.text)['message'])
        return None
    else:
        logging.error("Cannot sync config.json with V2Board. Please check your web server's networking.")
        return None


def add_users(user_list):
    for usr in user_list:
        user = usr['v2ray_user']
        conn.add_user('proxy', UUID(user['uuid']).hex, user['email'], user['level'],
                      user['alter_id'])
        localUserInfo.append(usr)
        logging.info("Added user: ID={0}, VmessID={1}, Email={2}".format(usr['id'], user['uuid'],
                                                                                 usr['email']))
    return


def get_user_info(urls):
    users = None
    i = 0
    while i < 3:
        try:
            users = requests.get(urls)
            break
        except requests.exceptions.ConnectionError as e:
            logging.warning(e.args[0].reason)
            i += 1
            time.sleep(5)
    if users.status_code == 200:
        users_info = users.json()
        if users_info['msg'] != "ok":
            logging.fatal(users_info['msg'])
            return None
        else:
            return users_info
    else:
        return None


# 使用 cfg.json 作为配置文件
with open(file='cfg.json', encoding='UTF-8') as cfg:
    configs = json.loads(cfg.read())
url = configs['url']
token = configs['token']
nodeID = configs['nodeID']
localPort = configs['localPort']
checkRate = configs['checkRate']
loglevel = configs['loglevel']

# 定义静态变量
localIP = "127.0.0.1"
version = "v1.0.0"
loglevelDict = {'CRITICAL': 50, 'ERROR': 40, 'WARNING': 30, 'INFO': 20, 'DEBUG': 10, }

logging.basicConfig(level=loglevelDict[loglevel.upper()],
                    format='%(asctime)s [%(levelname)s] V2Board Plugin: %(message)s',
                    datefmt='%Y/%m/%d %H:%M:%S')
print("V2Board Plugin %s by Senis" % version)

# 定义api url
getConfig_Url = '{0}/api/v1/server/deepbwork/config?local_port={1}&node_id={2}&token={3}'.\
    format(url, localPort, nodeID, token)
getUserInfo_Url = '{0}/api/v1/server/deepbwork/user?node_id={1}&token={2}'.format(url, nodeID, token)
submit_Url = '{0}/api/v1/server/deepbwork/submit?node_id={1}&token={2}'.format(url, nodeID, token)
# 清理残余v2ray进程
kill_proc('v2ray')
signal.signal(2, handle)
signal.signal(1, handle)
# 获取远程配置信息
fetch = get_config(getConfig_Url)
if not fetch:
    logging.critical('Initial config.json failure, Aborting start.')
    exit()
# 启动V2Ray服务
logging.info("Starting v2ray service")
getCwd = os.path.abspath(os.path.dirname(__file__))
with open('config.json', 'w', encoding='UTF-8') as file:
    file.write(json.dumps(fetch))
rc = subprocess.Popen([getCwd + "/v2ray/v2ray", "-config", getCwd + "/config.json"])
time.sleep(5)

# 下面进入循环
localUserInfo = []
while True:
    conn = Client(localIP, localPort)
    # 取得用户信息
    users_json = get_user_info(getUserInfo_Url)
    # 比较本地和远程配置文件
    remote_config = get_config(getConfig_Url)
    if remote_config:
        with open('config.json', 'r', encoding='UTF-8') as file:
            current_config = str(json.loads(file.read()))
        if str(remote_config) != current_config:
            logging.info("The config.json have been changed. Updating the local config.json.")
            rc.kill()
            with open('config.json', 'w', encoding='UTF-8') as file:
                file.write(json.dumps(remote_config))
            rc = subprocess.Popen([getCwd + "/v2ray/v2ray", "-config", getCwd + '/config.json'])
            time.sleep(5)
            add_users(users_json['data'])
    if rc.poll() is not None:
        logging.warning("V2ray terminated abnormally, Now restarting.")
        rc = subprocess.Popen([getCwd + "/v2ray/v2ray", "-config", getCwd + '/config.json'])
        time.sleep(5)
        add_users(users_json['data'])

    # 开始用户信息操作
    addUserList = []
    delUserList = []
    userInfo = []
    if users_json:
        userInfo = users_json['data']
        remoteUUIDList = []
        localUUIDList = []
        for uuid in userInfo:
            remoteUUIDList.append(uuid['v2ray_user']['uuid'])
        for uuid in localUserInfo:
            localUUIDList.append(uuid['v2ray_user']['uuid'])
        # 获取需删除用户信息
        for data in localUserInfo:
            if data['v2ray_user']['uuid'] not in remoteUUIDList:
                delUserList.append(data)
        # 获取需增加用户信息
        for data in userInfo:
            if data['v2ray_user']['uuid'] not in localUUIDList:
                addUserList.append(data)
        # 同步用户信息
        for data in delUserList:
            v2ray_user = data['v2ray_user']
            conn.remove_user('proxy', v2ray_user['email'])
            localUserInfo.remove(data)
            logging.info("Removed user: ID={0}, VmessID={1}, Email={2}".format(data['id'], v2ray_user['uuid'],
                                                                                       data['email']))
        add_users(addUserList)

    # 统计用户流量信息
    conn = Client(localIP, localPort)
    traffic = []
    for data in localUserInfo:
        u = conn.get_user_traffic_uplink(data['v2ray_user']['email'])
        d = conn.get_user_traffic_downlink(data['v2ray_user']['email'])
        if u or d:
            traffic.append({'user_id': data['id'], 'u': u, 'd': d})
    if traffic:
        post = requests.post(submit_Url, json=traffic)
        if post.status_code == 200:
            post_json = post.json()
            if post_json['msg'] == 'ok':
                for data in localUserInfo:
                    u = conn.get_user_traffic_uplink(data['v2ray_user']['email'], reset=True)
                    d = conn.get_user_traffic_downlink(data['v2ray_user']['email'], reset=True)
            else:
                logging.error(post_json['msg'])
        else:
            logging.error("Cannot sync traffic information with V2Board. Please check your web server's networking.")
    logging.info("+ {0} users, - {1} users, V2Ray PID = {2}".format(len(addUserList), len(delUserList), rc.pid))
    time.sleep(checkRate)
