ABOUT
=====
bcloud 是[百度网盘](http://pan.baidu.com)的Linux桌面客户端实现.

支持的系统版本:

* Fedora 20
* Debian sid
* Debian testing
* Debian stable
* Ubuntu 14.04
* Ubuntu 13.10
* Ubuntu 12.04
* OpenSuse 13

类似项目
=======
[bypy](https://github.com/houtianze/bypy), 终端里使用的百度网盘客户端, 它
使用了百度网盘PCS接口.


安装
====
请用户直接到 [bcloud-packages](https://github.com/LiuLang/bcloud-packages)
下载发行版相对应的安装包, 比如deb, rpm等.

如果需要手动安装的话, 也可以用pip3来安装, 比如: `# pip3 install bcloud`

如果不想安装安装, 请至少把blcoud/share目录合并到~/.local/share, 不然图标会显示不全.

DEPENDENCIES
===========

* python3-gi  Gtk3 的python3 绑定. 这个包需要手动安装gir1.2-gtk-3.0, 但它并
没有把这个依赖关系写清楚, 详细情况请看 [issue 5](https://github.com/LiuLang/bcloud/issues/5)
* gnome-icon-theme-symbolic Gnome3 提供的一套按纽.
* python3-keyring  这个模块是推荐安装的, 用于把帐户的密码存放到
* python3-dbus  dbus的python3绑定, 如果在密码时超时, 会产生一个dbus.exceptions.Exception异常.
gnome-keyring或kwallet里面; 如果缺少了这个模块, 帐户的密码就会被明文存储!
* gir1.2-notify 这个是GtkNotification的接口, 显示桌面消息通知

Q&A
===
1. 为什么bcloud不支持本地与远程服务器同步?

因为百度网盘没有公开它的同步算法.

2. 能不能支持其它网盘?

我时间和精力都非常有限, 单单开发bcloud就占用了我一个多月的业余时间. 而且
本来工作之外的时间就非常少, 还有很多其它事情要处理. 所以如果你报告了bug或者
反馈了问题, 没有及时收到回复, 请多等待一下, 我会安排时间处理这些问题的.


COPYRIGHT
========
Copyright (C) 2014 [LiuLang](mailto:gsushzhsosgsu@gmail.com)

基于GNU通用许可协议第三版发布, 详细的许可信息请参考 [LICENSE](LICENSE)

SCREENSHOTS
==========
![MainWindow](screenshots/bcloud.png)
