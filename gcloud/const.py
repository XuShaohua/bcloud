
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

'''
这个模块保存着网络连接时需要共用的一些常量.
与界面相关的常量, 都位于Config.py.
'''

BAIDU_URL = 'http://www.baidu.com/'
PASSPORT_URL = 'https://passport.baidu.com/v2/api/'
REFERER = 'https://passport.baidu.com/v2/?login'
USER_AGENT = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0;'
PAN_URL = 'http://pan.baidu.com/'
PAN_API_URL = PAN_URL + 'api/'
PAN_REFERER = 'http://pan.baidu.com/disk/home'
SHARE_REFERER = PAN_URL + 'share/manage'

# 一般的服务器名
PCS_URL = 'http://pcs.baidu.com/rest/2.0/pcs/'
# 上传的服务器名
PCS_URL_C = 'http://c.pcs.baidu.com/rest/2.0/pcs/'
# 下载的服务器名
PCS_URL_D = 'http://d.pcs.baidu.com/rest/2.0/pcs/'

## 以下常量是模拟的PC客户端的参数.
CHANNEL_URL = 'https://channel.api.duapp.com/rest/2.0/channel/channel?'
PC_USER_AGENT = 'netdisk;4.5.0.7;PC;PC-Windows;5.1.2600;WindowsBaiduYunGuanJia'
PC_DEVICE_ID = '08002788772E'
PC_DEVICE_NAME = '08002788772E'
PC_DEVICE_TYPE = '2'
PC_CLIENT_TYPE = '8'
PC_APP_ID = '1981342'
PC_DEVUID = ('BDIMXV2%2DO%5FFD60326573E54779892088D1378B27C6%2DC%5F0%2DD' +
             '%5F42563835636437366130302d6662616539362064%2DM%5F08002788' +
             '772E%2DV%5F0C94CA83')
PC_VERSION = '4.5.0.7'

## HTTP 请求时的一些常量
CONTENT_FORM = 'application/x-www-form-urlencoded'
CONTENT_FORM_UTF8 = CONTENT_FORM + '; charset=UTF-8'
ACCEPT_HTML = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
ACCEPT_JSON = 'application/json, text/javascript, */*; q=0.01'


class State:
    '''下载状态常量'''
    DOWNLOADING = 0
    WAITING = 1
    PAUSED = 2
    FINISHED = 3
    CANCELED = 4
    ERROR = 5
