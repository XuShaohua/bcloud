
# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

'''
这个模块主要是网盘的文件操作接口.
'''

import json
import os
import re

from lxml import html
from lxml.cssselect import CSSSelector as CSS

from bcloud import auth
from bcloud import const
from bcloud import encoder
from bcloud import hasher
from bcloud.log import logger
from bcloud import net
from bcloud.RequestCookie import RequestCookie
from bcloud import util

RAPIDUPLOAD_THRESHOLD = 256 * 1024  # 256K


def get_quota(cookie, tokens):
    '''获取当前的存储空间的容量信息.'''
    url = ''.join([
        const.PAN_API_URL,
        'quota?channel=chunlei&clienttype=0&web=1',
        '&t=', util.timestamp(),
    ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def get_user_uk(cookie, tokens):
    '''获取用户的uk'''
    url = 'http://yun.baidu.com'
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data.decode()
        match = re.findall('/share/home\?uk=(\d+)" target=', content)
        if len(match) == 1:
            return match[0]
        else:
            logger.warn('pcs.get_user_uk(), failed to parse uk, %s' % url)
    return None

def get_user_info(tokens, uk):
    '''获取用户的部分信息.

    比如头像, 用户名, 自我介绍, 粉丝数等.
    这个接口可用于查询任何用户的信息, 只要知道他/她的uk.
    '''
    url = ''.join([
        const.PAN_URL,
        'pcloud/user/getinfo?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        '&query_uk=', uk,
        '&t=', util.timestamp(),
    ])
    req = net.urlopen(url)
    if req:
        info = json.loads(req.data.decode())
        if info and info['errno'] == 0:
            return info['user_info']
    return None

def list_share(cookie, tokens, uk, page=1):
    '''获取用户已经共享的所有文件的信息

    uk   - user key
    page - 页数, 默认为第一页.
    num  - 一次性获取的共享文件的数量, 默认为100个.
    '''
    num = 100
    start = 100 * (page - 1)
    url = ''.join([
        const.PAN_URL,
        'pcloud/feed/getsharelist?',
        '&t=', util.timestamp(),
        '&categor=0&auth_type=1&request_location=share_home',
        '&start=', str(start),
        '&limit=', str(num),
        '&query_uk=', str(uk),
        '&channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
    ])
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Referer': const.SHARE_REFERER,
    })
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def list_share_files(cookie, tokens, uk, shareid, dirname, page=1):
    '''列举出用户共享的某一个目录中的文件信息

    这个对所有用户都有效
    uk       - user key
    shareid - 共享文件的ID值
    dirname  - 共享目录, 如果dirname为None, 说明这有可能是一个单独共享的文件,
               这里, 需要调用list_share_single_file()
    '''
    if not dirname:
        return list_share_single_file(cookie, tokens, uk, shareid)
    url = ''.join([
        const.PAN_URL,
        'share/list?channel=chunlei&clienttype=0&web=1&num=50',
        '&t=', util.timestamp(),
        '&page=', str(page),
        '&dir=', encoder.encode_uri_component(dirname),
        '&t=', util.latency(),
        '&shareid=', shareid,
        '&order=time&desc=1',
        '&uk=', uk,
        '&_=', util.timestamp(),
        '&bdstoken=', tokens['bdstoken'],
    ])
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Referer': const.SHARE_REFERER,
    })
    if req:
        content = req.data
        info = json.loads(content.decode())
        if info['errno'] == 0:
            return info['list']
    return list_share_single_file(cookie, tokens, uk, shareid)

def list_share_single_file(cookie, tokens, uk, shareid):
    '''获取单独共享出来的文件.

    目前支持的链接格式有:
      * http://pan.baidu.com/wap/link?uk=202032639&shareid=420754&third=0
      * http://pan.baidu.com/share/link?uk=202032639&shareid=420754
    '''
    def parse_share_page(content):
        tree = html.fromstring(content)
        script_sel = CSS('script')
        scripts = script_sel(tree)
        for script in scripts:
            if (script.text and (script.text.find('viewsingle_param') > -1 or
                script.text.find('mpan.viewlist_param') > -1)):
                break
        else:
            logger.warn('pcs.parse_share_page: failed to get filelist, %s', url)
            return None
        start = script.text.find('viewsingle_param.list=JSON.parse(')
        end = script.text.find(');mpan.viewsingle_param.username')
        if start == -1 or end == -1:
            start = script.text.find('listArr:JSON.parse(')
            end = script.text.find('),rootPath:')
            if start == -1 or end == -1:
                return None
            else:
                json_str = script.text[start+19:end]
        else:
            json_str = script.text[start+33:end]
        try:
            return json.loads(json.loads(json_str))
        except ValueError:
            logger.warn(traceback.format_exc())
            return None

    url = ''.join([
        const.PAN_URL, 'wap/link',
        '?shareid=', shareid,
        '&uk=', uk,
        '&third=0',
    ])
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Referer': const.SHARE_REFERER,
    })
    if req:
        return parse_share_page(req.data.decode())
    else:
        return None

def enable_share(cookie, tokens, fid_list):
    '''建立新的分享.

    fid_list - 是一个list, 里面的每一条都是一个文件的fs_id
    一次可以分享同一个目录下的多个文件/目录, 它们会会打包为一个分享链接,
    这个分享链接还有一个对应的shareid. 我们可以用uk与shareid来在百度网盘里
    面定位到这个分享内容.
    @return - 会返回分享链接和shareid.
    '''
    url = ''.join([
        const.PAN_URL,
        'share/set?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
    ])
    data = encoder.encode_uri(
            'fid_list={0}&schannel=0&channel_list=[]'.format(fid_list))
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def disable_share(cookie, tokens, shareid_list):
    '''取消分享.

    shareid_list 是一个list, 每一项都是一个shareid
    '''
    url = ''.join([
        const.PAN_URL,
        'share/cancel?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
    ])
    data = 'shareid_list=' + encoder.encode_uri(json.dumps(shareid_list))
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def enable_private_share(cookie, tokens, fid_list):
    '''建立新的私密分享.

    密码是在本地生成的, 然后上传到服务器.
    '''
    print('enable private share:', fid_list, cookie, tokens)
    url = ''.join([
        const.PAN_URL,
        'share/set?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        '&channel=chunlei&clienttype=0&web=1',
        '&appid=250528',
    ])
    print('url:', url)
    passwd = 'dmlg'
    data = encoder.encode_uri(''.join([
        'fid_list=[', str(fid_list), ']',
        '&schannel=4&channel_list=[]',
        '&pwd=', passwd,
        ]))
    print('data:', data)
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode()), passwd
    else:
        return None, passwd

def verify_share_password(uk, shareid, pwd, vcode=''):
    '''验证共享文件的密码.

    如果密码正确, 会在返回的请求头里加入一个cookie: BDCLND
    
    pwd - 四位的明文密码
    vcode - 验证码; 目前还不支持
    '''
    url = ''.join([
        const.PAN_URL,
        'share/verify?&clienttype=0&web=1&channel=chunlei',
        '&shareid=', shareid,
        '&uk=', uk,
    ])
    data = 'pwd={0}&vcode={1}'.format(pwd, vcode)

    req = net.urlopen(url, data=data.encode())
    if req:
        content = req.data.decode()
        info = json.loads(content)
        errno = info.get('errno', 1)
        if errno == 0:
            return req.headers.get_all('Set-Cookie')
        elif errno in (-19, -62, -63):
            pass  # TODO: need verify code
    return None

def get_share_uk_and_shareid(cookie, url):
    '''从共享链接中提示uk和shareid.

    如果共享文件需要输入密码, 就会将need_pwd设为True
    如果成功, 返回(need_pwd, uk, shareid)
    如果失败, 就返回None

    目前支持的链接格式有:
      * http://pan.baidu.com/wap/link?uk=202032639&shareid=420754&third=0
      * http://pan.baidu.com/share/link?uk=202032639&shareid=420754
      * http://pan.baidu.com/s/1i3iQY48
    '''
    def parse_share_uk(content):
        '''代码片段如下:

        yunData.SHARE_ID = "677200861";
        yunData.SHARE_UK = "1295729848";
        '''
        uk_reg = re.compile('yunData.SHARE_UK\s*=\s*"(\d+)"')
        shareid_reg = re.compile('yunData.SHARE_ID\s*=\s*"(\d+)"')
        uk_match = uk_reg.search(content)
        shareid_match = shareid_reg.search(content)
        if uk_match and shareid_match:
            return False, uk_match.group(1), shareid_match.group(1)
        else:
            return None

    def parse_uk_from_url(url):
        uk_reg = re.compile('uk=(\d+)')
        uk_match = uk_reg.search(url)
        shareid_reg = re.compile('shareid=(\d+)')
        shareid_match = shareid_reg.search(url)
        if not uk_match or not shareid_match:
            return '', ''
        uk = uk_match.group(1)
        shareid = shareid_match.group(1)
        return uk, shareid

    # 识别加密链接
    req = net.urlopen_without_redirect(url, headers={
        'Cookie': cookie.header_output(),
    })
    if req and req.headers.get('Location'):
        init_url = req.headers.get('Location')
        if init_url.find('share/init') > -1:
            uk, shareid = parse_uk_from_url(init_url)
            return True, uk, shareid

    # 处理短链接
    if url.startswith('http://pan.baidu.com/s/'):
        req = net.urlopen(url, headers={
            'Cookie': cookie.header_output(),
        })
        if req:
            return parse_share_uk(req.data.decode())
    # 处理正常链接
    uk, shareid = parse_uk_from_url(url)
    return False, uk, shareid

def get_share_dirname(url):
    '''从url中提取出当前的目录'''
    dirname_match = re.search('(dir|path)=([^&]+)',
                              encoder.decode_uri_component(url))
    if dirname_match:
        return dirname_match.group(2)
    else:
        return None

def get_share_url_with_dirname(uk, shareid, dirname):
    '''得到共享目录的链接'''
    return ''.join([
           const.PAN_URL, 'wap/link',
           '?shareid=', shareid,
           '&uk=', uk,
           '&dir=', encoder.encode_uri_component(dirname),
           '&third=0',
        ])

def share_transfer(cookie, tokens, shareid, uk, filelist, dest, upload_mode):
    '''
    将其他用户的文件保存到自己网盘里.

    uk - 其他用户的uk
    filelist - 要转移文件的列表, 是绝对路径
    '''
    ondup = const.UPLOAD_ONDUP[upload_mode]
    url = ''.join([
        const.PAN_URL,
        'share/transfer?app_id=250528&channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        '&from=', uk,
        '&shareid=', shareid,
        '&ondup=', ondup,
        '&async=1',
    ])
    data = ''.join([
        'path=', encoder.encode_uri_component(dest),
        '&filelist=', encoder.encode_uri_component(json.dumps(filelist))
    ])

    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-Type': const.CONTENT_FORM_UTF8
    }, data=data.encode())
    if req:
        content = req.data.decode()
        return json.loads(content)
    else:
        return None


def list_inbox(cookie, tokens, start=0, limit=20):
    '''获取收件箱里的文件信息.'''
    url = ''.join([
        const.PAN_URL,
        'inbox/object/list?type=1',
        '&start=', str(start),
        '&limit=', str(limit),
        '&_=', util.timestamp(),
        '&channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
    ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def list_trash(cookie, tokens, path='/', page=1, num=100):
    '''获取回收站的信息.

    path - 目录的绝对路径, 默认是根目录
    page - 页码, 默认是第一页
    num - 每页有多少个文件, 默认是100个.
    回收站里面的文件会被保存10天, 10天后会自动被清空.
    回收站里面的文件不占用用户的存储空间.
    '''
    url = ''.join([
        const.PAN_API_URL,
        'recycle/list?channel=chunlei&clienttype=0&web=1',
        '&num=', str(num),
        '&t=', util.timestamp(),
        '&dir=', encoder.encode_uri_component(path),
        '&t=', util.latency(),
        '&order=time&desc=1',
        '&_=', util.timestamp(),
        '&bdstoken=', tokens['bdstoken'],
    ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def restore_trash(cookie, tokens, fidlist):
    '''从回收站中还原文件/目录.

    fildlist - 要还原的文件/目录列表, fs_id.
    '''
    url = ''.join([
        const.PAN_API_URL,
        'recycle/restore?channel=chunlei&clienttype=0&web=1',
        '&t=', util.timestamp(),
        '&bdstoken=', tokens['bdstoken'],
    ])
    data = 'fidlist=' + encoder.encode_uri_component(json.dumps(fidlist))
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def delete_trash(cookie, tokens, fidlist):
    '''批量将文件从回收站中删除, 这一步不可还原!'

    fidlist - 待删除的目录/文件的fs_id 列表.

    如果有一个文件的fs_id在回收站中不存在, 就会报错, 并返回.
    '''
    url = ''.join([
        const.PAN_API_URL,
        'recycle/delete?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
    ])
    data = 'fidlist=' + encoder.encode_uri_component(json.dumps(fidlist))
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def clear_trash(cookie, tokens):
    '''清空回收站, 将里面的所有文件都删除.'''
    url = ''.join([
        const.PAN_API_URL,
        'recycle/clear?channel=chunlei&clienttype=0&web=1',
        '&t=', util.timestamp(),
        '&bdstoken=', tokens['bdstoken'],
    ])
    # 使用POST方式发送命令, 但data为空.
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        }, data=''.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def list_dir_all(cookie, tokens, path):
    '''得到一个目录中所有文件的信息, 并返回它的文件列表'''
    pcs_files = []
    page = 1
    while True:
        content = list_dir(cookie, tokens, path, page)
        if not content:
            return (path, None)
        if not content['list']:
            return (path, pcs_files)
        pcs_files.extend(content['list'])
        page = page + 1

def list_dir(cookie, tokens, path, page=1, num=100):
    '''得到一个目录中的所有文件的信息(最多100条记录).'''
    timestamp = util.timestamp()
    url = ''.join([
        const.PAN_API_URL,
        'list?channel=chunlei&clienttype=0&web=1',
        '&num=', str(num),
        '&t=', timestamp,
        '&page=', str(page),
        '&dir=', encoder.encode_uri_component(path),
        '&t=', util.latency(),
        '&order=time&desc=1',
        '&_=', timestamp,
        '&bdstoken=', tokens['bdstoken'],
    ])
    req = net.urlopen(url, headers={
        'Content-type': const.CONTENT_FORM_UTF8,
        'Cookie': cookie.sub_output('BAIDUID', 'BDUSS', 'PANWEB', 'cflag'),
    })
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def mkdir(cookie, tokens, path):
    '''创建一个目录.

    path 目录名, 绝对路径.
    @return 返回一个dict, 里面包含了fs_id, ctime等信息.
    '''
    url = ''.join([
        const.PAN_API_URL, 
        'create?a=commit&channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
    ])
    data = ''.join([
        'path=', encoder.encode_uri_component(path),
        '&isdir=1&size=&block_list=%5B%5D&method=post',
    ])
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def delete_files(cookie, tokens, filelist):
    '''批量删除文件/目录.

    filelist - 待删除的文件/目录列表, 绝对路径
    '''
    url = ''.join([
        const.PAN_API_URL,
        'filemanager?channel=chunlei&clienttype=0&web=1&opera=delete',
        '&bdstoken=', tokens['bdstoken'],
    ])
    data = 'filelist=' + encoder.encode_uri_component(json.dumps(filelist))
    req = net.urlopen(url, headers={
        'Content-type': const.CONTENT_FORM_UTF8,
        'Cookie': cookie.header_output(),
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def rename(cookie, tokens, filelist):
    '''批量重命名目录/文件.

    只能修改文件名, 不能修改它所在的目录.

    filelist 是一个list, 里面的每一项都是一个dict, 每个dict包含两部分:
    path - 文件的绝对路径, 包含文件名.
    newname - 新名称.
    '''
    url = ''.join([
        const.PAN_API_URL,
        'filemanager?channel=chunlei&clienttype=0&web=1&opera=rename',
        '&bdstoken=', tokens['bdstoken'],
    ])
    data = 'filelist=' + encoder.encode_uri_component(json.dumps(filelist))
    req = net.urlopen(url, headers={
        'Content-type': const.CONTENT_FORM_UTF8,
        'Cookie': cookie.header_output(),
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def move(cookie, tokens, filelist):
    '''移动文件/目录到新的位置.

    filelist 是一个list, 里面包含至少一个dict, 每个dict都有以下几项:
    path - 文件的当前的绝对路径, 包括文件名.
    dest - 文件的目标绝对路径, 不包括文件名.
    newname - 文件的新名称; 可以与保持原来的文件名一致, 也可以给一个新名称.
    '''
    url = ''.join([
        const.PAN_API_URL,
        'filemanager?channel=chunlei&clienttype=0&web=1&opera=move',
        '&bdstoken=', tokens['bdstoken'],
    ])
    data = 'filelist=' + encoder.encode_uri_component(json.dumps(filelist))
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def copy(cookie, tokens, filelist):
    '''复制文件/目录到新位置.

    filelist 是一个list, 里面的每一项都是一个dict, 每个dict都有这几项:
    path - 文件/目录的当前的绝对路径, 包含文件名
    dest - 要复制到的目的路径, 不包含文件名
    newname - 文件/目录的新名称; 可以保持与当前名称一致.
    '''
    url = ''.join([
        const.PAN_API_URL,
        'filemanager?channel=chunlei&clienttype=0&web=1&opera=copy',
        '&bdstoken=', tokens['bdstoken'],
    ])
    data = 'filelist=' + encoder.encode_uri_component(json.dumps(filelist))
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None


def get_category(cookie, tokens, category, page=1):
    '''获取一个分类中的所有文件信息, 比如音乐/图片

    目前的有分类有:
      视频 - 1
      音乐 - 2
      图片 - 3
      文档 - 4
      应用 - 5
      其它 - 6
      BT种子 - 7
    '''
    timestamp = util.timestamp()
    url = ''.join([
        const.PAN_API_URL,
        'categorylist?channel=chunlei&clienttype=0&web=1',
        '&category=', str(category),
        '&pri=-1&num=100',
        '&t=', timestamp,
        '&page=', str(page),
        '&order=time&desc=1',
        '&_=', timestamp,
        '&bdstoken=', cookie.get('STOKEN').value,
    ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def get_download_link(cookie, tokens, path):
    '''在下载之前, 要先获取最终的下载链接.

    path - 一个文件的绝对路径.

    @return red_url, red_url 是重定向后的URL, 如果获取失败,
            就返回原来的dlink;
    '''
    metas = get_metas(cookie, tokens, path)
    if (not metas or metas.get('errno', -1) != 0 or
            'info' not in metas or len(metas['info']) != 1):
        logger.error('pcs.get_download_link(): %s' % metas)
        return None
    dlink = metas['info'][0]['dlink']
    url = '{0}&cflg={1}'.format(dlink, cookie.get('cflag').value)
    req = net.urlopen_without_redirect(url, headers={
        'Cookie': cookie.sub_output('BAIDUID', 'BDUSS', 'cflag'),
        'Accept': const.ACCEPT_HTML,
    })
    if not req:
        return url
    else:
        return req.getheader('Location', url)

def stream_download(cookie, tokens, path):
    '''下载流媒体文件.

    path - 流文件的绝对路径.
    '''
    url = ''.join([
        const.PCS_URL_D,
        'file?method=download',
        '&path=', encoder.encode_uri_component(path),
        '&app_id=250528',
    ])
    req = net.urlopen_without_redirect(url, headers=
            {'Cookie': cookie.header_output()})
    if req:
        return req
    else:
        return None

def get_streaming_playlist(cookie, path, video_type='M3U8_AUTO_480'):
    '''获取流媒体(通常是视频)的播放列表.

    默认得到的是m3u8格式的播放列表, 因为它最通用.
    path       - 视频的绝对路径
    video_type - 视频格式, 可以根据网速及片源, 选择不同的格式.
    '''
    url = ''.join([
        const.PCS_URL,
        'file?method=streaming',
        '&path=', encoder.encode_uri_component(path),
        '&type=', video_type,
        '&app_id=250528',
    ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        return req.data
    else:
        return None


#def upload_option(cookie, path):
#    '''上传之前的检查.
#
#    path   - 准备在服务器上放到的绝对路径.
#    '''
#    dir_name, file_name = os.path.split(path)
#    url = ''.join([
#        const.PCS_URL_C,
#        'file?method=upload&app_id=250528&ondup=newcopy',
#        '&dir=', encoder.encode_uri_component(dir_name),
#        '&filename=', encoder.encode_uri_component(file_name),
#        '&', cookie.sub_output('BDUSS'),
#    ])
#    resp = net.urloption(url, headers={'Accept': const.ACCEPT_HTML})
#    if resp:
#        return resp.getheaders()
#    else:
#        return None

def upload(cookie, source_path, path, upload_mode):
    '''上传一个文件.

    这个是使用的网页中的上传接口.
    upload_mode - const.UploadMode, 如果文件已在服务器上存在:
      * overwrite, 直接将其重写.
      * newcopy, 保留原先的文件, 并在新上传的文件名尾部加上当前时间戳.
    '''
    ondup = const.UPLOAD_ONDUP[upload_mode]
    dir_name, file_name = os.path.split(path)
    url = ''.join([
        const.PCS_URL_C,
        'file?method=upload&app_id=250528',
        '&ondup=', ondup,
        '&dir=', encoder.encode_uri_component(dir_name),
        '&filename=', encoder.encode_uri_component(file_name),
        '&', cookie.sub_output('BDUSS'),
    ])
    with open(source_path, 'rb') as fh:
        data = fh.read()
    fields = []
    files = [('file', file_name, data)]
    headers = {'Accept': const.ACCEPT_HTML, 'Origin': const.PAN_URL}
    req = net.post_multipart(url, headers, fields, files)
    if req:
        return json.loads(req.data.decode())
    else:
        return None

def rapid_upload(cookie, tokens, source_path, path, upload_mode):
    '''快速上传'''
    ondup = const.UPLOAD_ONDUP[upload_mode]
    content_length = os.path.getsize(source_path)
    assert content_length > RAPIDUPLOAD_THRESHOLD, 'file size is not satisfied!'
    dir_name, file_name = os.path.split(path)
    content_md5 = hasher.md5(source_path)
    slice_md5 = hasher.md5(source_path, 0, RAPIDUPLOAD_THRESHOLD)
    url = ''.join([
        const.PCS_URL_C,
        'file?method=rapidupload&app_id=250528',
        '&ondup=', ondup,
        '&dir=', encoder.encode_uri_component(dir_name),
        '&filename=', encoder.encode_uri_component(file_name),
        '&content-length=', str(content_length),
        '&content-md5=', content_md5,
        '&slice-md5=', slice_md5,
        '&path=', encoder.encode_uri_component(path),
        '&', cookie.sub_output('BDUSS'),
        '&bdstoken=', tokens['bdstoken'],
    ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        return json.loads(req.data.decode())
    else:
        return None

def slice_upload(cookie, data):
    '''分片上传一个大文件
    
    分片上传完成后, 会返回这个分片的MD5, 用于最终的文件合并.
    如果上传失败, 需要重新上传.
    不需要指定上传路径, 上传后的数据会被存储在服务器的临时目录里.
    data - 这个文件分片的数据.
    '''
    url = ''.join([
        const.PCS_URL_C,
        'file?method=upload&type=tmpfile&app_id=250528',
        '&', cookie.sub_output('BDUSS'),
    ])
    fields = []
    files = [('file', ' ', data)]
    headers = {'Accept': const.ACCEPT_HTML,'Origin': const.PAN_URL}
    req = net.post_multipart(url, headers, fields, files)
    if req:
        return json.loads(req.data.decode())
    else:
        return None

def create_superfile(cookie, path, block_list):
    '''合并slice_upload()中产生的临时文件

    path       - 文件在服务器上的绝对路径
    block_list - 这些文件分片的MD5列表
    返回完整的文件pcs信息.
    '''
    url = ''.join([
        const.PCS_URL_C,
        'file?method=createsuperfile&app_id=250528',
        '&path=', encoder.encode_uri_component(path),
        '&', cookie.sub_output('BDUSS'),
    ])
    param = {'block_list': block_list}
    data = 'param=' + json.dumps(param)
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()},
                      data=data.encode())
    if req:
        return json.loads(req.data.decode())
    else:
        return None


def get_metas(cookie, tokens, filelist, dlink=True):
    '''获取多个文件的metadata.

    filelist - 一个list, 里面是每个文件的绝对路径.
               也可以是一个字符串, 只包含一个文件的绝对路径.
    dlink    - 是否包含下载链接, 默认为True, 包含.

    @return 包含了文件的下载链接dlink, 通过它可以得到最终的下载链接.
    '''
    if isinstance(filelist, str):
        filelist = [filelist, ]
    url = ''.join([
        const.PAN_API_URL,
        'filemetas?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
    ])
    if dlink:
        data = ('dlink=1&target=' +
                encoder.encode_uri_component(json.dumps(filelist)))
    else:
        data = ('dlink=0&target=' +
                encoder.encode_uri_component(json.dumps(filelist)))
    req = net.urlopen(url, headers={
        'Cookie': cookie.sub_output('BDUSS'),
        'Content-type': const.CONTENT_FORM,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def search(cookie, tokens, key, path='/'):
    '''搜索全部文件, 根据文件名.

    key - 搜索的关键词
    path - 如果指定目录名的话, 只搜索本目录及其子目录里的文件名.
    '''
    url = ''.join([
        const.PAN_API_URL,
        'search?channel=chunlei&clienttype=0&web=1',
        '&dir=', path,
        '&key=', key,
        '&recursion',
        '&timeStamp=', util.latency(),
        '&bdstoken=', tokens['bdstoken'],
    ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_add_link_task(cookie, tokens, source_url, save_path,
                        vcode='', vcode_input=''):
    '''新建离线下载任务.
    
    source_url - 可以是http/https/ftp等一般的链接
                 可以是eMule这样的链接
    path       - 要保存到哪个目录, 比如 /Music/, 以/开头, 以/结尾的绝对路径.
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
    ])
    type_ = ''
    if source_url.startswith('ed2k'):
        type_ = '&type=3'
    if not save_path.endswith('/'):
        save_path = save_path + '/'
    data = [
        'method=add_task&app_id=250528',
        '&source_url=', encoder.encode_uri_component(source_url),
        '&save_path=', encoder.encode_uri_component(save_path),
        '&type=', type_,
    ]
    if vcode:
        data.append('&input=')
        data.append(vcode_input)
        data.append('&vcode=')
        data.append(vcode)
    data = ''.join(data)
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()},
                      data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_add_bt_task(cookie, tokens, source_url, save_path, selected_idx,
                      file_sha1='', vcode='', vcode_input=''):
    '''新建一个BT类的离线下载任务, 包括magent磁链.

    source_path  - BT种子所在的绝对路径
    save_path    - 下载的文件要存放到的目录
    selected_idx - BT种子中, 包含若干个文件, 这里, 来指定要下载哪些文件,
                   从1开始计数.
    file_sha1    - BT种子的sha1值, 如果是magent的话, 这个sha1值可以为空
    vcode        - 验证码的vcode
    vcode_input  - 用户输入的四位验证码
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
    ])
    type_ = '2'
    url_type = 'source_path'
    if source_url.startswith('magnet:'):
        type_ = '4'
        url_type = 'source_url'
    if not save_path.endswith('/'):
        save_path = save_path + '/'
    data = [
        'method=add_task&app_id=250528',
        '&file_sha1=', file_sha1,
        '&save_path=', encoder.encode_uri_component(save_path),
        '&selected_idx=', ','.join(str(i) for i in selected_idx),
        '&task_from=1',
        '&t=', util.timestamp(),
        '&', url_type, '=', encoder.encode_uri_component(source_url),
        '&type=', type_
    ]
    if vcode:
        data.append('&input=')
        data.append(vcode_input)
        data.append('&vcode=')
        data.append(vcode)
    data = ''.join(data)
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()},
                      data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_query_sinfo(cookie, tokens, source_path):
    '''获取网盘中种子的信息, 比如里面的文件名, 文件大小等.

    source_path - BT种子的绝对路径.
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl?channel=chunlei&clienttype=0&web=1',
        '&method=query_sinfo&app_id=250528',
        '&bdstoken=', tokens['bdstoken'],
        '&source_path=', encoder.encode_uri_component(source_path),
        '&type=2',
        '&t=', util.timestamp(),
    ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_query_magnetinfo(cookie, tokens, source_url, save_path):
    '''获取磁链的信息.
    
    在新建磁链任务时, 要先获取这个磁链的信息, 比如里面包含哪些文件, 文件的名
    称与大小等.

    source_url - 磁链的url, 以magent:开头.
    save_path  - 保存到哪个目录
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
    ])
    data = ''.join([
        'method=query_magnetinfo&app_id=250528',
        '&source_url=', encoder.encode_uri_component(source_url),
        '&save_path=', encoder.encode_uri_component(save_path),
        '&type=4',
    ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()},
                      data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_list_task(cookie, tokens, start=0):
    '''获取当前离线下载的任务信息
    
    start - 从哪个任务开始, 从0开始计数, 会获取这50条任务信息
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        '&need_task_info=1&status=255',
        '&start=', str(start),
        '&limit=50&method=list_task&app_id=250528',
        '&t=', util.timestamp(),
    ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_query_task(cookie, tokens, task_ids):
    '''查询离线下载任务的信息, 比如进度, 是否完成下载等.

    最好先用cloud_list_task() 来获取当前所有的任务, 然后调用这个函数来获取
    某项任务的详细信息.

    task_ids - 一个list, 里面至少要有一个task_id, task_id 是一个字符串
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl?method=query_task&app_id=250528',
        '&bdstoken=', tokens['bdstoken'],
        '&task_ids=', ','.join(task_ids),
        '&t=', util.timestamp(),
        '&channel=chunlei&clienttype=0&web=1',
    ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_cancel_task(cookie, tokens, task_id):
    '''取消离线下载任务.
    
    task_id - 之前建立离线下载任务时的task id, 也可以从cloud_list_task()里
              获取.
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl',
        '?bdstoken=', tokens['bdstoken'],
        '&task_id=', str(task_id),
        '&method=cancel_task&app_id=250528',
        '&t=', util.timestamp(),
        '&channel=chunlei&clienttype=0&web=1',
    ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_delete_task(cookie, tokens, task_id):
    '''删除一个离线下载任务, 不管这个任务是否已完成下载.

    同时还会把它从下载列表中删除.
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl',
        '?bdstoken=', tokens['bdstoken'],
        '&task_id=', str(task_id),
        '&method=delete_task&app_id=250528',
        '&t=', util.timestamp(),
        '&channel=chunlei&clienttype=0&web=1',
    ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_clear_task(cookie, tokens):
    '''清空离线下载的历史(已经完成或者取消的).'''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl?method=clear_task&app_id=250528',
        '&channel=chunlei&clienttype=0&web=1',
        '&t=', util.timestamp(),
        '&bdstoken=', tokens['bdstoken'],
    ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

