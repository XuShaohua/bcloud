// Copyright (c) 2017 LiuLang. All rights reserved.
// Use of this source is governed by GPL-3.0 License that can be found
// in the LICENSE file.
'use strict';
Object.defineProperty(exports, "__esModule", { value: true });
var http = require("http");
http.get('http://www.solidot.org/', 
// https.get('https://passport.baidu.com/v2/api/?getapi&tpl=mn&apiver=v3&tt=1&class=login&logintype=basicLogin',
function (response) {
    // let rawData = '';
    var cookies = response.headers['set-cookie'];
    console.log('cookies:', cookies);
    //
    // response.on('data', (chunk) => {
    //   rawData += chunk;
    // });
    //
    // response.on('end', () => {
    //   console.log(rawData.length);
    // });
});
//# sourceMappingURL=main.js.map