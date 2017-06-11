// Copyright (c) 2017 LiuLang. All rights reserved.
// Use of this source is governed by GPL-3.0 License that can be found
// in the LICENSE file.

'use strict';

import * as fs from 'fs';
import * as request from 'request';

const cookieJar = request.jar();
let token = '';

// Convert single quotes to double quotes.
function purifySingleQuoteJSON(input: string): string {
  return input.replace(/'/g, '"');
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
          msg.pubkey = msg.pubkey.replace(/\n/g, '');
          console.log('msg:', msg);
          resolve(msg);
        } catch (jsonErr) {
          reject(jsonErr);
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

  try {
    const conf = JSON.parse(content);
    console.log('conf:', conf);

    getBaiduId()
      .then(getToken)
      .then(() => checkLoginState(conf.username)
      .then(getPublicKey)
      .catch(err => console.error(err));

  } catch (jsonErr) {
    console.error(jsonErr);
  }
});
