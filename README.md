关于
=====
bcloud 是[百度网盘](http://pan.baidu.com)的Linux桌面客户端.

已经支持的Linux系统/版本:

* ArchLinux
* Debian sid
* Debian testing
* Debian stable
* Fedora 20
* Fedora 21
* Gentoo
* OpenSuse 13
* Ubuntu 14.04
* Ubuntu 13.10
* Linux Mint 17

类似项目
=======
[bypy](https://github.com/houtianze/bypy) 终端里使用的百度网盘客户端, 它
使用了百度网盘PCS接口.

如果需要, 也可以直接调用bcloud提供的百度网盘接口, 使用bcloud/auth.py得到百度
服务器的连接授权, 然后使用bcloud/pcs.py调用相应的网盘接口.


安装
====
请用户直接到 [bcloud-packages](https://github.com/LiuLang/bcloud-packages)
下载发行版相对应的安装包, 比如deb, rpm等.

如果需要手动安装的话, 也可以用`pip3`(ArchLinux里面是`pip`)来安装,
比如: `# pip3 install bcloud`


依赖的软件包
===========

* python3-gi  Gtk3 的python3 绑定. 这个包需要手动安装gir1.2-gtk-3.0, 但它并
没有把这个依赖关系写清楚, 详细情况请看 [issue 5](https://github.com/LiuLang/bcloud/issues/5)
* gnome-icon-theme-symbolic Gnome3 提供的一套按纽.
* python3-keyring  这个模块是推荐安装的, 用于把帐户的密码存放到
gnome-keyring或kwallet里面; 如果缺少了这个模块, 帐户的密码就会被明文存储!
* gnome-keyring或者kwalletmanager, 并且要保证它在用户登录桌面后自动启动.
代替gnome-keyring.
* python3-dbus  dbus的python3绑定, 如果在密码时超时, 会产生一个dbus.exceptions.Exception异常.
* python3-lxml 强大的XML解析器, 可以在[这里](https://pypi.python.org/pypi/lxml)下载.
* python3-cssselect CSS3 属性选择器, 在[这里](https://pypi.python.org/pypi/cssselect).
* python3-crypto  使用RSA算法加密用户密码.
* gir1.2-notify 这个是GtkNotification的接口, 显示桌面消息通知

Q&A
===
1.为什么bcloud不支持本地与远程服务器同步?

因为百度网盘没有公开它的同步算法. 参考这个[issue](https://github.com/LiuLang/bcloud/issues/11)

2.能不能支持其它网盘?

我时间和精力都非常有限, 单单开发bcloud就占用了我一个多月的业余时间. 而且
本来工作之外的时间就非常少, 还有很多其它事情要处理. 所以如果你报告了bug或者
反馈了问题, 没有及时收到回复, 请多等待一下, 我会安排时间处理这些问题的.

3.如何设置keyring?
ArchLinux 用户最有可能遇到这个问题. 因为在debian/ubuntu/mint等系统里面, keyring
在安装后会自动被配置好, 而在arch中, 这些都需要用户手动设定, 很麻烦.

arch的wiki里面有完整的介绍, 请arch用户到[这里](https://wiki.archlinux.org/index.php/GNOME_Keyring)
读完整篇文章, 然后针对自己的桌面环境以及自己的需要, 选择相应的配置方式.

还有一篇类似的文档, 是gnomekeyring官方的, 有也相应[介绍](https://wiki.gnome.org/action/show/Projects/GnomeKeyring?action=show&redirect=GnomeKeyring#Automatic_Unlocking)

4.为什么不同的发行版里面, bcloud的界面不一样?
bcloud目前已经开始调用gtk3.12中的组件, 这样与新版gnome-shell的样式更统一;
但旧的发行版, 比如debian 7等, 里面的gtk3的版本很老, 只能继续使用旧的界面了.
它们在功能上并无差别.

5.有命令行界面吗?
bcloud只提供了GUI界面. 但是, 可以很方便的基于bcloud进行扩展, bcloud实现了百度网
盘的大部分接口, 其中bcloud/auth.py用于授权登录, bcloud/pcs.py是网盘接口.

比如, [这个issue](https://github.com/LiuLang/bcloud/issues/47)里面,
通过调用bcloud, 来遍历网盘, 得到文件目录结构.


版权
====
Copyright (C) 2014 [LiuLang](mailto:gsushzhsosgsu@gmail.com)

基于GNU通用许可协议第三版发布, 详细的许可信息请参考 [LICENSE](LICENSE)

截屏
====
![MainWindow](screenshots/bcloud.png)
