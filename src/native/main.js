/**
 * Created by LiuLang on 6/10/17.
 */

"use strict";

const electron = require('electron');
const path = require('path')
const url = require('url')

let win = null;

function createWindow () {
  "use strict";

  console.log("createWindow()");
  win = new electron.BrowserWindow({width: 860, height:640});

  win.loadURL(url.format({
    pathname: path.join(__dirname, 'web/index.html'),
    protocol: 'file:',
    slashes: true,
  }));

  win.webContents.openDevTools();

  win.on('closed', () => {
    win = null;
});
}

electron.app.on('ready', createWindow);

electron.app.on('window-all-closed', () => {
  "use strict";
electron.app.quit();
});

electron.app.on('activate', function () {
  if (win === null) {
    createWindow();
  }
});