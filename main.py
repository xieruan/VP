#!/usr/bin/python3
from uuid import UUID
import requests
import time
from client import Client
import logging
import subprocess
import json
import os


def get_pid(proc):
    commands = "ps aux| grep '%s'|grep -v grep " % proc
    logging.info(commands)
    out = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE)
    infos = out.stdout.read().splitlines()
    pid_list = []
    if len(infos) >= 1:
        for k in infos:
            proc_id = k.split()[1]
            if proc_id not in pid_list:
                pid_list.append(int(proc_id.decode()))
        return pid_list
    else:
        return None


def format_traffic(integer):
    if integer:
        if integer <= 1024:
            return str(integer) + " B"
        elif integer <= 1024 * 1024:
            return str('%.2f' % (integer / 1024)) + " KB"
        else:
            return str('%.2f' % (integer / 1024 ** 2)) + " MB"
    else:
        return None


def update_config(in_url, local_port, node_id, access_token):
    # config info
    config = None
    n = 0
    while n < 3:
        try:
            config = requests.get(
                '{0}/api/v1/server/deepbwork/config?local_port={1}&node_id={2}&token={3}'.format(
                    in_url, local_port, node_id, access_token))
            break
        except requests.exceptions.ConnectionError as f:
            logging.warning(f)
            time.sleep(5)
            n += 1
    config_json = config.json()
    if config:
        return config_json['msg'], config_json['data']
    else:
        return config_json['msg'], None


def add_users(user_list):
    for usr in user_list:
        user = usr['v2ray_user']
        conn.add_user('proxy', UUID(user['uuid']).hex, user['email'], user['level'],
                      user['alter_id'])
        localUserInfo.append(usr)
        logging.info(title + "Added user: ID={0}, VmessID={1}, Email={2}".format(usr['id'], user['uuid'],
                                                                                 usr['email']))
    return


# 使用 cfg.json 作为配置文件
with open(file='cfg.json', encoding='UTF-8') as cfg:
    configs = json.loads(cfg.read())
url = configs['url']
token = configs['token']
nodeID = configs['nodeID']
localPort = configs['localPort']
checkRate = configs['checkRate']
loglevel = configs['loglevel']

localIP = "127.0.0.1"
version = "v1.0.0"
title = "V2Board Plugin: "
loglevelDict = {'CRITICAL': 50, 'ERROR': 40, 'WARNING': 30, 'INFO': 20, 'DEBUG': 10, }
logging.basicConfig(level=loglevelDict[loglevel.upper()])
print(title + "Welcome to use the V2Board Plugin %s by Senis" % version)
# 清理之前的进程
v2rayProcess = get_pid("v2ray")
if v2rayProcess:
    for v2rayProc in v2rayProcess:
        os.kill(v2rayProc, 1)
    time.sleep(3)
# 获取远程配置信息
fetch = update_config(url, localPort, nodeID, token)
rc = None
if fetch[0] == "ok":
    logging.info("Starting v2ray service")
    get_config = json.dumps(fetch[1])
    with open('config.json', 'w', encoding='UTF-8') as file:
        file.write(get_config)
    rc = subprocess.Popen([os.getcwd() + "/v2ray/v2ray", "-config", os.getcwd() + "/config.json"])
    time.sleep(5)
else:
    logging.error(fetch[0] + ", Please check your WebAPI values is correct.")
    exit()

# 下面进入循环
localUserInfo = []
while True:
    # 取得用户信息
    conn = Client(localIP, localPort)
    users = None
    i = 0
    while i < 3:
        try:
            users = requests.get('{0}/api/v1/server/deepbwork/user?node_id={1}&token={2}'.format(url, nodeID, token))
            break
        except requests.exceptions.ConnectionError as e:
            logging.warning(e)
            i += 1
            time.sleep(5)
    users_json = None
    if users.status_code == 200:
        users_json = users.json()
        if users_json['msg'] != "ok":
            logging.fatal(users_json['msg'])
    else:
        logging.error(title + "Cannot connecting V2Board WebAPI. Please check your web server.")
    # 比较本地和远程配置文件
    remote_config = update_config(url, localPort, nodeID, token)[1]
    with open('config.json', 'r', encoding='UTF-8') as file:
        cur_config = str(json.loads(file.read()))
    if str(remote_config) != cur_config:
        logging.info("The config.json have been changed. Updating the local config.json.")
        rc.kill()
        with open('config.json', 'w', encoding='UTF-8') as file:
            file.write(json.dumps(remote_config))
        rc = subprocess.Popen([os.getcwd() + "/v2ray/v2ray", "-config", os.getcwd() + '/config.json'])
        time.sleep(5)
        add_users(users_json['data'])
    if rc.poll() is not None:
        logging.warning("V2ray terminated abnormally, Now restarting")
        rc = subprocess.Popen([os.getcwd() + "/v2ray/v2ray", "-config", os.getcwd() + '/config.json'])
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
            logging.info(title + "Removed user: ID={0}, VmessID={1}, Email={2}".format(data['id'], v2ray_user['uuid'],
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
        post = requests.post('{0}/api/v1/server/deepbwork/submit?node_id={1}&token={2}'.format(url, nodeID, token),
                             json=traffic)
        if post.status_code == 200:
            post_json = post.json()
            if post_json['msg'] == 'ok':
                for data in localUserInfo:
                    u = conn.get_user_traffic_uplink(data['v2ray_user']['email'], reset=True)
                    d = conn.get_user_traffic_downlink(data['v2ray_user']['email'], reset=True)
            else:
                logging.error(post_json['msg'])
        else:
            logging.fatal(title + "Cannot connecting V2Board WebAPI. Please check your web server.")
    logging.info(title + "+ {0} users, - {1} users, V2Ray PID = {2}".format(len(addUserList), len(delUserList), rc.pid))
    time.sleep(checkRate)
