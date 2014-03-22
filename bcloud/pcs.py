
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
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

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
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

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

def get_download_link(cookie, dlink):
    '''在下载之前, 要先获取最终的下载链接, 因为中间要进行一次302跳转.

    这一步是为了得到最终的下载地址. 如果得不到最终的下载地址, 那下载速度就
    会受到很大的限制.

    dlink - 在pcs_file里面的dlink项, 这个链接是一个临时下载链接.

    @return (red_url, request_id), red_url 是重定向后的URL, 如果获取失败,
            就返回原来的dlink; request_id 是一个字符串, 用于下载文件时的认
            证, 如果获取失败, 它的值就为空.
    '''
    url = ''.join([
        dlink,
        '&cflg=', cookie.get('cflag').value
        ])
    req = net.urlopen_without_redirect(url, headers={
            'Cookie': cookie.sub_output('BAIDUID', 'BDUSS', 'cflag'),
            'Accept': const.ACCEPT_HTML,
            })
    if not req:
        return (url, '')
    red_url = req.getheader('Location', url)
    req_id = req.getheader('x-pcs-request-id', '')
    return (red_url, req_id)

#def download(cookie, url, targ_path, range_=None):
#    '''以普通方式下载文件.
#
#    如果指定range的话, 可以下载指定的数据段.
#    pcs_file - 文件的详细信息.
#    targ_path - 保存文件的目标路径
#    range_ - 要下载的数据范围, 利用这个可以实现断点续传; 如果不指定它,
#             就会一次性下载文件的全部内容(在pcs_file中有文件的大小信息).
#
#    @return 
#    '''
#    headers = {'Cookie': cookie.header_output()}
#    if range_:
#        headers['Range'] = range_
#    req = net.urlopen(url, headers=headers)
#    content = req.data
#    with open(targ_path, 'wb') as fh:
#        fh.write(content)

def get_metas(cookie, tokens, filelist):
    '''获取文件的metadata.

    filelist - 一个list, 里面是每个文件的绝对路径.
               也可以是一个字符串, 只包含一个文件的绝对路径.

    @return 包含了文件的下载链接dlink, 通过它可以得到最终的下载链接.
    '''
    if isinstance(filelist, str):
        filelist = [filelist, ]
    url = ''.join([
        const.PAN_API_URL,
        'filemetas?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        ])
    data = 'dlink=1&target=' + encoder.encode_uri_component(json.dumps(filelist))
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

def cloud_add_link_task(cookie, tokens, source_url, save_path):
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
    data = ''.join([
        'method=add_task&app_id=250528',
        '&source_url=', encoder.encode_uri_component(source_url),
        '&save_path=', encoder.encode_uri_component(save_path),
        '&type=', type_,
        ])
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_add_bt_task(cookie, tokens, source_url, save_path,
                    selected_idx, file_sha1='', vcode='', vcode_input=''):
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
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        }, data=data.encode())
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
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        }, data=data.encode())
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
