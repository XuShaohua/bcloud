#!/usr/bin/env python3

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

'''
这个模块主要是网盘的文件操作接口.
'''

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import auth
import const
import encoder
import net
from RequestCookie import RequestCookie
import util


def get_quota(cookie, tokens):
    '''获取当前的存储空间的容量信息.'''
    url = ''.join([
        const.PAN_API_URL,
        'quota?channel=chunlei&clienttype=0&web=1',
        '&t=', util.timestamp(),
        ])
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        })
    content = req.data
    return json.loads(content.decode())

def list_share(cookie, tokens, path='/', page=1, num=100):
    '''获取用户已经共享的文件的信息

    path - 哪个目录的信息, 默认为根目录.
    page - 页数, 默认为第一页.
    num - 一次性获取的共享文件的数量, 默认为100个.
    '''
    url = ''.join([
        const.PAN_URL,
        'share/record?channel=chunlei&clienttype=0&web=1',
        '&num=', str(num),
        '&t=', util.timestamp(),
        '&page=', str(page),
        '&dir=', encoder.encode_uri_component(path),
        '&t=', util.latency(), 
        '&order=tme&desc=1',
        '&_=', util.timestamp(),
        '&bdstoken=', tokens['bdstoken'],
        ])
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Referer': const.SHARE_REFERER,
        })
    content = req.data
    return json.loads(content.decode())

def enable_share(cookie, tokens, fid_list):
    '''建立新的分享.

    fid_list - 是一个list, 里面的每一条都是一个文件的fs_id

    @return - 会返回每一项的分享链接和shareid.
    '''
    url = ''.join([
        const.PAN_URL,
        'share/set?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        ])
    data = encoder.encode_uri('fid_list=' + json.dumps(fid_list) + 
            '&schannel=0&channel_list=[]')
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    content = req.data
    return json.loads(content.decode())

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
    content = req.data
    print(content)
    return json.loads(content.decode())


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
    content = req.data
    return json.loads(content.decode())

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
    content = req.data
    return json.loads(content.decode())

def restore_trash(cookie, tokens, fidlist):
    '''从回收站中还原文件/目录.

    fildlist - 要还要的文件/目录列表, fs_id.
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
    content = req.data
    return json.loads(content.decode())

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
    content = req.data
    return json.loads(content.decode())

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
    content = req.data
    return json.loads(content.decode())


def list_dir(cookie, tokens, path, page=1, num=100):
    '''得到一个目录中的所有文件的信息.'''
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
    content = req.data
    import pprint
    pprint.pprint(json.loads(content.decode()))
    return json.loads(content.decode())

def mkdir(cookie, tokens, path):
    '''创建一个目录.

    path 目录名, 绝对路径.
    @return 返回一个dict, 里面包含了fs_id, ctime等信息.
    '''
    print('pcs.mkdir()--')
    print(path)
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
    content = req.data
    print(content)
    return json.loads(content.decode())

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
    content = req.data
    return json.loads(content.decode())

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
    content = req.data
    return json.loads(content.decode())

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
    content = req.data
    return json.loads(content.decode())

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
    content = req.data
    return json.loads(content.decode())


def get_category(cookie, tokens, category):
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
        '&page=1&order=time&desc=1',
        '&_=', timestamp,
        '&bdstoken=', cookie.get('STOKEN').value,
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    content = req.data
    return json.loads(content.decode())

def get_download_link(pcs_file, cookie):
    '''在下载之前, 要先获取最终的下载链接, 因为中间要进行一次302跳转.

    这一步是为了得到最终的下载地址. 如果得不到最终的下载地址, 那下载速度就
    会受到很大的限制.
    '''
    url = pcs_file['dlink'] + cookie.get('cflag').value
    return net.urlopen_without_redirect(url, headers={
            'Cookie': cookie.sub_output('BAIDUID', 'BDUSS', 'cflag'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            })

def download(url, targ_path, cookie, range_=None):
    '''以普通方式下载文件.

    如果指定range的话, 可以下载指定的数据段.
    pcs_file - 文件的详细信息.
    targ_path - 保存文件的目标路径
    range_ - 要下载的数据范围, 利用这个可以实现断点续传; 如果不指定它,
             就会一次性下载文件的全部内容(在pcs_file中有文件的大小信息).

    @return 
    '''
    headers = {'Cookie': cookie.header_output()}
    if range_:
        headers['Range'] = range_
    req = net.urlopen(url, headers=headers)
    content = req.data
    with open(targ_path, 'wb') as fh:
        fh.write(content)

def main():
    username = 'leeh3oDog9ee@163.com'
    password = 'soz5mae4Neegae'
    cookie, tokens = auth.get_auth_info(username, password, refresh=False)

    #timestamp = util.timestamp()
    #cookie.load('Hm_lvt_773fea2ac036979ebb5fcc768d8beb67=' + timestamp)
    #cookie.load('Hm_lpvt_773fea2ac036979ebb5fcc768d8beb67=' + timestamp)
    #cookie.load('Hm_lvt_b181fb73f90936ebd334d457c848c8b5=' + timestamp)
    #cookie.load('Hm_lpvt_b181fb73f90936ebd334d457c848c8b5=' + timestamp)
    #cookie.load('Hm_lvt_adf736c22cd6bcc36a1d27e5af30949e=' + timestamp)
    #cookie.load('Hm_lpvt_adf736c22cd6bcc36a1d27e5af30949e=' + timestamp)

    #quota = get_quota(cookie, tokens)
    #print(quota)

    dirs = list_dir('/', cookie, tokens)
    import pprint
    pprint.pprint(dirs)

    #category = 3  # 图片
    #get_category(cookie, tokens, category)

    #path = '/dir8'
    #mkdir(path, cookie, tokens)
    
    #list_inbox(cookie, tokens)

    #trash_files = list_trash(cookie, tokens)
    #print(trash_files)
    #restore_trash(cookie, tokens, [186616217120184, 222756948157255])
    #delete_trash(cookie, tokens, [331091603537793, 222756948157255])
    #clear_trash(cookie, tokens)

    #delete_files(cookie, tokens, ['/dir6', '/dir7'])

    #rename(cookie, tokens, [
    #    {'path': '/dir5.1', 'newname': 'dir5.0'},
    #    {'path': '/dir4.2', 'newname': 'dir4.0'},
    #    ])
    #move(cookie, tokens, [
    #    {'path': '/dir5.0', 'dest': '/dir3', 'newname': 'dir5.1'},
    #    {'path': '/dir4.0', 'dest': '/dir3', 'newname': 'dir4.1'},
    #    ])
    #copy(cookie, tokens, [
    #    {'path': '/dir', 'dest': '/dir3', 'newname': 'dir0.1'},
    #    ])

    #list_share(cookie, tokens)
    #enable_share(cookie, tokens, [
    #    220763851904839,
    #    ])
    #disable_share(cookie, tokens, [
    #    491379316,
    #    ])

if __name__ == '__main__':
    main()
