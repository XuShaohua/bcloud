// Copyright (c) 2017 LiuLang. All rights reserved.
// Use of this source is governed by GPL-3.0 License that can be found
// in the LICENSE file.

'use strict';

const forge = require('node-forge');
const fs = require('fs');
const getStdin = require('get-stdin');
const queryString = require('querystring');
const request = require('request');

const cookieJar = request.jar();
const verifyCodeImage = '/tmp/vcode.png';
let token = '';
let rsakey;
let loginParams;

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

function getTimestamp(): string {
  return (new Date()).getTime().toString();
}

function getPpuiLoginTime(): string {
  const startVal = 52000;
  const endVal = 58535;
  const random = Math.random() * (endVal - startVal) + startVal;
  return random.toFixed();
}

function getBaiduId(): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = ['https://passport.baidu.com/v2/api/?getapi&tpl=mn&apiver=v3',
      '&tt=', getTimestamp, '&class=login&logintype=basicLogin'].join('');
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
    const url = ['https://passport.baidu.com/v2/api/?getapi&tpl=pp&apiver=v3',
      '&tt=', getTimestamp, '&class=login&logintype=basicLogin'].join('');
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
    const url = ['https://passport.baidu.com/v2/api/?logincheck&token=', token,
      '&tpl=mm&apiver=v3&tt=', getTimestamp(), '&isphone=false', '&username=', username].join('');
    console.log('url:', url);
    const headers = {
      'Referer': 'https://passport.baidu.com/v2/api/?login',
      'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0 Iceweasel/31.2.0'
    };
    request.get({url: url, jar: cookieJar, headers: headers}, (err, response, body) => {
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
    const url = ['https://passport.baidu.com/v2/getpublickey?token=', token,
      '&tpl=pp&apiver=v3&tt=', getTimestamp()].join('');
    request.get({url: url, jar: cookieJar}, (err, response, body) => {
      console.log('getPublicKey():', err, '\nheaders:', response.headers, '\nbody:', body);
      if (err == null) {
        console.log('cookies:', cookieJar);
        try {
          const msg = JSON.parse(purifySingleQuoteJSON(body));
          // Remove new-line chars.
          // msg.pubkey = msg.pubkey.replace(/\n/g, '');
          console.log('msg:', msg);
          rsakey = msg;
          if (msg.errno === '0') {
            resolve();
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

function getSignInVerifyCode(params: Object): Promise<Object> {
  return new Promise((resolve, reject) => {
    const url = 'https://passport.baidu.com/cgi-bin/genimage?' + params['codeString'];
    console.log('url:', url);
    request.get({url: url, jar: cookieJar}, (err, response, body) => {
      console.log('getSignInVerifyCode()', err, '\nheaders:', response.headers, '\nbody:', body.length);
      if (err == null) {
        fs.writeFileSync(verifyCodeImage, body, 'binary');
        loginParams = params;
        resolve();
      } else {
        reject(err);
      }
    });
  });
}

function login(username: string, password: string, codeString: string, verifyCode: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const encryptedPassword = rsaEncrypt(password, rsakey['pubkey']);
    const url = 'https://passport.baidu.com/v2/api/?login';
    const headers = {
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Referer': 'https://pan.baidu.com/',
      'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0 Iceweasel/31.2.0'
    };
    const form = {
      'staticpage': 'http%3A%2F%2Fyun.baidu.com%2Fres%2Fstatic%2Fthirdparty%2Fpass_v3_jump.html',
      'tpl': 'netdisk',
      'subpro': 'netdisk_web',
      'charset': 'UTF-8',
      'token': token,
      'apiver': 'v3',
      'tt': getTimestamp(),
      'codestring': codeString,
      'safeflg': '0',
      'u': 'http%3A%2F%2Fyun.baidu.com%2Fdisk%2Fhome',
      'isPhone': 'false',
      'quick_user': '0',
      'logintype': 'baseLogin',
      'logLoginType': 'pc_loginBasic',
      'idc': '',
      'loginmerge': 'true',
      'username': encodeURIComponent(username),
      'password': encodeURIComponent(encryptedPassword),
      'verifycode': verifyCode,
      'mem_pass': 'on',
      'rsakey': rsakey['key'],
      'crypttype': '12',
      'ppui_logintime': getPpuiLoginTime(),
      'callback': 'parent.bd__pcbs__28g1kg',
    };
    console.log('form data:', form);
    request.post({url: url, jar: cookieJar, headers: headers, form: form}, (err, response, body) => {
      console.log('login():', err, '\nheaders:', response.headers, '\nbody:', body);

      if (err == null) {
        const reg = /"(err_no=[^"]+)"/;
        const match = reg.exec(body);
        if (match != null) {
          const params = queryString.parse(match[1]);
          console.log('params:', params);
          resolve(params);
        } else {
          reject(body);
        }
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
    .then(() => login(conf.username, conf.password, '', ''))
    .then((params) => {
      console.log(params);
      const errNo = parseInt(params['err_no']);
      if (errNo == 0) {
        console.log('already login');
      } else {
        console.warn('err no:', errNo);
        return getSignInVerifyCode(params);
      }
    })
    .then(getStdin)
    .then(verifyCode => {
      console.log('verifyCode:', verifyCode);
      return login(conf.username, conf.password, loginParams['codeString'], verifyCode.trim());
    })
    .catch(err => console.error(err));
});
