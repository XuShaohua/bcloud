// Copyright (c) 2017 LiuLang. All rights reserved.
// Use of this source is governed by GPL-3.0 License that can be found
// in the LICENSE file.

'use strict';

import * as http from 'http';

http.get({
  hostname: 'www.debian.org',
  port: 80,
  path: '/',
  agent: false,
}, (res) => {
  console.log("res:", res);
})