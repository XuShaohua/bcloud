// Copyright (c) 2017 LiuLang. All rights reserved.
// Use of this source is governed by GPL-3.0 License that can be found
// in the LICENSE file.
'use strict';
var fs = require("fs");
var request = require("request");
var cookieJar = request.jar();
var token = '';
// Convert single quotes to double quotes.
function purifySingleQuoteJSON(input) {
    return input.replace(/'/g, '"');
}
function getBaiduId() {
    return new Promise(function (resolve, reject) {
        var url = 'https://passport.baidu.com/v2/api/?getapi&tpl=mn&apiver=v3&tt=1&class=login&logintype=basicLogin';
        request.get({ url: url, jar: cookieJar }, function (err, response, body) {
            console.log('getBaiduId:', err, '\nheaders:', response.headers, '\nbody:', body);
            if (err == null) {
                console.log('cookies:', cookieJar);
                resolve();
            }
            else {
                reject(err);
            }
        });
    });
}
function getToken() {
    return new Promise(function (resolve, reject) {
        var url = 'https://passport.baidu.com/v2/api/?getapi&tpl=pp&apiver=v3&tt=0&class=login&logintype=basicLogin';
        request.get({ url: url, jar: cookieJar }, function (err, response, body) {
            console.log('getToken()', err, '\nheaders:', response.headers, '\nbody:', body);
            if (err == null) {
                console.log('cookies:', cookieJar);
                try {
                    var msg = JSON.parse(purifySingleQuoteJSON(body));
                    token = msg.data.token;
                    console.log('token:', token);
                    resolve();
                }
                catch (jsonErr) {
                    console.error(jsonErr);
                    reject(jsonErr);
                }
            }
            else {
                reject(err);
            }
        });
    });
}
function checkLoginState(username) {
    return new Promise(function (resolve, reject) {
        var url = ['https://passport.baidu.com/v2/api/?logincheck&token=',
            token,
            '&tpl=mm&apiver=v3&tt=0&isphone=false',
            '&username=', username
        ].join('');
        console.log('url:', url);
        request.get({ url: url, jar: cookieJar }, function (err, response, body) {
            console.log('checkLoginState:', err, '\nheaders:', response.headers, '\nbody:', body);
            if (err == null) {
                console.log('cookies:', cookieJar);
                // TODO(LiuLang): Handles vcodetype and codestring.
                resolve();
            }
            else {
                reject(err);
            }
        });
    });
}
function getPublicKey() {
    return new Promise(function (resolve, reject) {
        var url = 'https://passport.baidu.com/v2/getpublickey?token=' + token + '&tpl=pp&apiver=v3&tt=0';
        request.get({ url: url, jar: cookieJar }, function (err, response, body) {
            console.log('getPublicKey():', err, '\nheaders:', response.headers, '\nbody:', body);
            if (err == null) {
                console.log('cookies:', cookieJar);
                try {
                    var msg = JSON.parse(purifySingleQuoteJSON(body));
                    // Remove new-line chars.
                    msg.pubkey = msg.pubkey.replace(/\n/g, '');
                    console.log('msg:', msg);
                    resolve(msg);
                }
                catch (jsonErr) {
                    reject(jsonErr);
                }
            }
            else {
                reject(err);
            }
        });
    });
}
fs.readFile('/tmp/bcloud.conf', { encoding: 'UTF-8' }, function (readErr, content) {
    if (readErr) {
        console.error(readErr);
        return;
    }
    try {
        var conf_1 = JSON.parse(content);
        console.log('conf:', conf_1);
        getBaiduId()
            .then(getToken)
            .then(function () { return checkLoginState(conf_1.username)
            .then(getPublicKey)
            .catch(function (err) { return console.error(err); }); });
    }
    catch (jsonErr) {
        console.error(jsonErr);
    }
});
//# sourceMappingURL=main.js.map