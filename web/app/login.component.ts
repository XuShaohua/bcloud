// Copyright (c) 2017 LiuLang. All rights reserved.
// Use of this source is governed by GPL-3.0 License that can be found
// in the LICENSE file.

'use strict';

import { Component, OnInit, OnDestroy } from '@angular/core';

import { ChannelService } from './channel.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})

export class LoginComponent implements OnInit, OnDestroy {

  username: string;
  password: string;

  constructor(
    private channel: ChannelService
  ) {}

  ngOnInit(): void {
    this.channel.connect('onGetBaiduId', this.onGetBaiduId);
    this.channel.connect('onGetToken', this.onGetToken);
    this.channel.connect('onCheckLoginState', this.onCheckLoginState);
    this.channel.connect('onGetPublicKey', this.onGetPublicKey);
    this.channel.connect('onLogin', this.onLogin);
  }

  ngOnDestroy(): void {
    this.channel.disconnect('onGetBaiduId', this.onGetBaiduId);
    this.channel.disconnect('onGetToken', this.onGetToken);
    this.channel.disconnect('onCheckLoginState', this.onCheckLoginState);
    this.channel.disconnect('onGetPublicKey', this.onGetPublicKey);
    this.channel.disconnect('onLogin', this.onLogin);
  }

  tryLogin(): void {
    this.username = '';
    this.password = '';

    this.channel.sendMsg('getBaiduId', '');
  }

  onGetBaiduId(): void {
    this.channel.sendMsg('getToken', '');
  }

  onGetToken(): void {
    this.channel.sendMsg('checkLoginState', this.username);
  }

  onCheckLoginState(): void {
    this.channel.sendMsg('getPublicKey', '');
  }

  onGetPublicKey(): void {
    this.channel.sendMsg('login', '');
  }

  onLogin(): void {
    console.log('on login');
  }
}
