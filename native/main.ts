// Copyright (c) 2017 LiuLang. All rights reserved.
// Use of this source is governed by GPL-3.0 License that can be found
// in the LICENSE file.

'use strict';

import { forge } from 'node-forge';
import * as fs from 'fs';
import { request } from 'request';

const cookieJar = request.jar();
let token = '';

// Convert single quotes to double quotes.
function purifySingleQuoteJSON(input: string): string {
  return input.replace(/'/g, '"');
}

function rsaEncrypt(msg: string, pubkey: string): string {
  const key = forge.pki.publicKeyFromPem(pubkey);
  const cipherBinary = key.encrypt(msg, 'RSAES-PKCS1-V1_5');
  // Convert binary ciphertext to base64 encoded string.
  return new Buffer(cipherBinary, 'binary').toString('base64');
}

function getBaiduId(): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = 'https://passport.baidu.com/v2/api/?getapi&tpl=mn&apiver=v3&tt=1&class=login&logintype=basicLogin';
    request.get({url: url, jar: cookieJar}, (err, response, body) => {
      console.log('getBaiduId:', err, '\nheaders:', response.headers, '\nbody:', body);
      if (err == null) {
        console.log('cookies:', cookieJar);

        resolve();
      } else {
        reject(err);
      }
    });
  });
}

function getToken(): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = 'https://passport.baidu.com/v2/api/?getapi&tpl=pp&apiver=v3&tt=0&class=login&logintype=basicLogin';
    request.get({url: url, jar: cookieJar}, (err, response, body) => {
      console.log('getToken()', err, '\nheaders:', response.headers, '\nbody:', body);
      if (err == null) {
        console.log('cookies:', cookieJar);
        try {
          const msg = JSON.parse(purifySingleQuoteJSON(body));
          token = msg.data.token;
          console.log('token:', token);
          resolve();
        } catch (jsonErr) {
          console.error(jsonErr);
          reject(jsonErr);
        }
      } else {
        reject(err);
      }
    });
  });
}

function checkLoginState(username: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = ['https://passport.baidu.com/v2/api/?logincheck&token=',
      token,
      '&tpl=mm&apiver=v3&tt=0&isphone=false',
      '&username=', username
      ].join('');
    console.log('url:', url);
    request.get({url: url, jar: cookieJar}, (err, response, body) => {
      console.log('checkLoginState:', err, '\nheaders:', response.headers, '\nbody:', body);
      if (err == null) {
        console.log('cookies:', cookieJar);
        // TODO(LiuLang): Handles vcodetype and codestring.
        resolve();
      } else {
        reject(err);
      }
    });
  });
}

function getPublicKey(): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = 'https://passport.baidu.com/v2/getpublickey?token=' + token + '&tpl=pp&apiver=v3&tt=0';
    request.get({url: url, jar: cookieJar}, (err, response, body) => {
      console.log('getPublicKey():', err, '\nheaders:', response.headers, '\nbody:', body);
      if (err == null) {
        console.log('cookies:', cookieJar);
        try {
          const msg = JSON.parse(purifySingleQuoteJSON(body));
          // Remove new-line chars.
          // msg.pubkey = msg.pubkey.replace(/\n/g, '');
          console.log('msg:', msg);
          if (msg.errno === '0') {
            resolve(msg);
          } else {
            reject(msg);
          }
        } catch (jsonErr) {
          reject(jsonErr);
        }
      } else {
        reject(err);
      }
    });
  });
}

// TODO(LiuLang): Add codestring and verifycode parameters.
function login(username: string, password: string, rsakey: Object): Promise<string> {
  return new Promise((resolve, reject) => {
    const encryptedPassword = rsaEncrypt(password, rsakey['pubkey']);
    const url = 'https://passport.baidu.com/v2/api/?login';
    const headers = {
      'Referer': 'https://passport.baidu.com/v2/api/?login',
      'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0 Iceweasel/31.2.0'
    };
    const form = {
      'staticpage': 'https%3A%2F%2Fpassport.baidu.com%2Fstatic%2Fpasspc-account%2Fhtml%2Fv3Jump.html',
      'charset': 'UTF-8',
      'token': token,
      'tpl': 'pp',
      'apiver': 'v3',
      'tt': '0',
      'codestring': '',
      'verifycode': '',
      'safeflg': '0',
      'u': 'http%3A%2F%2Fpassport.baidu.com%2F',
      'quick_user': '0',
      'logintype': 'basicLogin',
      'logLoginType': 'pc_loginBasic',
      'loginmerge': 'true',
      'username': encodeURIComponent(username),
      'password': encryptedPassword,
      'mem_pass': 'on',
      'rsakey': rsakey['key'],
      'crypttype': '12',
      'ppui_logintime': '52000',
      'callback': 'parent.bd__pcbs__28g1kg',
    };
    request.post({url: url, jar: cookieJar, headers: headers, form: form}, (err, response, body) => {
      console.log('login():', err, '\nheaders:', response.headers, '\nbody:', body);
      if (err == null) {
        resolve();
      } else {
        reject(err);
      }
    });
  });
}

fs.readFile('/tmp/bcloud.conf', {encoding: 'UTF-8'}, (readErr, content) => {
  if (readErr) {
    console.error(readErr);
    return;
  }

  let conf;
  try {
    conf = JSON.parse(content);
    console.log('conf:', conf);
  } catch (jsonErr) {
    console.error(jsonErr);
    return;
  }

  getBaiduId()
    .then(getToken)
    .then(() => checkLoginState(conf.username))
    .then(getPublicKey)
    .then((rsakey) => login(conf.username, conf.password, rsakey))
    .catch(err => console.error(err));
});
