
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

'''
这个模块保存着网络连接时需要共用的一些常量.
与界面相关的常量, 都位于Config.py.
'''

from bcloud import Config
_ = Config._

BAIDU_URL = 'http://www.baidu.com/'
PASSPORT_BASE = 'https://passport.baidu.com/'
PASSPORT_URL = PASSPORT_BASE + 'v2/api/'
PASSPORT_LOGIN = PASSPORT_BASE + 'v2/api/?login'
REFERER = PASSPORT_BASE + 'v2/?login'
#USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0'
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0 Iceweasel/31.2.0'
PAN_URL = 'http://pan.baidu.com/'
PAN_API_URL = PAN_URL + 'api/'
PAN_REFERER = 'http://pan.baidu.com/disk/home'
SHARE_REFERER = PAN_URL + 'share/manage'

# 一般的服务器名
PCS_URL = 'http://pcs.baidu.com/rest/2.0/pcs/'
# 上传的服务器名
PCS_URL_C = 'http://c.pcs.baidu.com/rest/2.0/pcs/'
PCS_URLS_C = 'https://c.pcs.baidu.com/rest/2.0/pcs/'
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
PC_DEVUID = 'BDIMXV2%2DO%5FFD60326573E54779892088D1378B27C6%2DC%5F0%2DD%5F42563835636437366130302d6662616539362064%2DM%5F08002788772E%2DV%5F0C94CA83'
PC_VERSION = '4.5.0.7'

## HTTP 请求时的一些常量
CONTENT_FORM = 'application/x-www-form-urlencoded'
CONTENT_FORM_UTF8 = CONTENT_FORM + '; charset=UTF-8'
ACCEPT_HTML = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
ACCEPT_JSON = 'application/json, text/javascript, */*; q=0.8'


class State:
    '''下载状态常量'''
    DOWNLOADING = 0
    WAITING = 1
    PAUSED = 2
    FINISHED = 3
    CANCELED = 4
    ERROR = 5

class UploadState:
    UPLOADING = 0
    WAITING = 1
    PAUSED = 2
    FINISHED = 3
    CANCELED = 4
    ERROR = 5

class UploadMode:
    '''上传时, 如果服务器端已存在同名文件时的操作方式'''
    IGNORE = 0
    OVERWRITE = 1
    NEWCOPY = 2

DownloadMode = UploadMode

UPLOAD_ONDUP = ('', 'overwrite', 'newcopy')

# 视图模式
ICON_VIEW, TREE_VIEW = 0, 1

class ValidatePathState:
    '''文件路径检验结果'''
    OK = 0
    LENGTH_ERROR = 1
    CHAR_ERROR2 = 2
    CHAR_ERROR3 = 3

ValidatePathStateText = (
    '',
    _('Max characters in filepath shall no more than 1000'),
    _('Filepath should not contain \\ ? | " > < : *'),
    _('\\r \\n \\t \\0 \\x0B or SPACE should not appear in start or end of filename'),
)


class TargetInfo:
    '''拖放类型编号'''

    URI_LIST = 0
    PLAIN_TEXT = 1
    RAW = 2
    TEXT_JSON = 3


class TargetType:
    '''拖放类型'''

    URI_LIST = 'text/uri-list'
    PLAIN_TEXT = 'text/plain'
    RAW = 'application/octet-stream'
    TEXT_JSON = 'application/json'
