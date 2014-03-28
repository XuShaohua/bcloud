ABOUT
=====
bcloud 是[百度网盘](http://pan.baidu.com)的Linux桌面客户端实现.

现在只写了一部分主要功能, 其它功能还要等有空再加入. gloud 还处于早期的开发阶段, 欢迎各位朋友提交问题.

支持的系统版本:

* Fedora 20
* Debian sid
* Debian testing
* Debian stable
* Ubuntu 13.10
* Ubuntu 14.04
* OpenSuse 13

不支持的版本:

* Ubuntu 12.04

安装
====
请用户直接到 [bcloud-packages](https://github.com/LiuLang/bcloud-packages)
下载发行版相对应的安装包, 比如deb, rpm等.

如果需要手动安装的话, 也可以用pip3来安装, 比如: `# pip3 install bcloud`

如果不想安装安装, 请至少把blcoud/share目录合并到~/.local/share, 不然图标会显示不全.

DEPENDENCIES
===========

* python3-gi  Gtk3 的python3 绑定
* python3-urllib3 urllib的封装, 更易用, 在这里 https://pypi.python.org/pypi/urllib3.
* gnome-icon-theme-symbolic Gnome3 提供的一套按纽.
* python3-keyring  这个模块是推荐安装的, 用于把帐户的密码存放到gnome-keyring
或者kwallet里面; 如果缺少了这个模块, 帐户的密码就会被明文存储!


COPYRIGHT
========
Copyright (C) 2014 [LiuLang](mailto:gsushzhsosgsu@gmail.com)

基于GNU通用许可协议第三版发布, 详细的许可信息请参考 [LICENSE](LICENSE)

SCREENSHOTS
==========
![MainWindow](screenshots/bcloud.png)
