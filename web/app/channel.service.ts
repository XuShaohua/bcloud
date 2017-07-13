// Copyright (c) 2017 LiuLang. All rights reserved.
// Use of this source is governed by GPL-3.0 License that can be found
// in the LICENSE file.

'use strict';

import { Injectable, OnInit } from '@angular/core';

@Injectable()
export class ChannelService implements OnInit {

  ws: WebSocket;
  connections: Object;

  constructor() { }

  ngOnInit(): void {
    this.connections = {};
    this.ws = new WebSocket('ws://localhost:4040');
    this.ws.onmessage = this._onMsg;
  }

  connect(signal: string, slot: Function): void {
    if (this.connections[signal] == null) {
      this.connections[signal] = [];
    }
    if (this.connections[signal].indexOf(slot) === -1) {
      this.connections[signal].push(slot);
    }
  }

  disconnect(signal: string, slot: Function): void {
    if (this.connections[signal] == null) {
      console.warn('Signal not registered:', signal);
      return;
    }

    const index = this.connections[signal].indexOf(slot);
    if (index === -1) {
      console.warn('Slot not registered:', slot);
    } else {
      this.connections[signal].removeAt(index);
    }
  }

  // TODO(LiuLang): Handles function parameter list.
  sendMsg(signal: string, payload: any): void {
    const data = [signal, payload];
    this.ws.send(JSON.stringify(data));
  }

  _onMsg(ev: MessageEvent): void {
    let msg: Array<string>;
    try {
      msg = JSON.parse(ev.data);
      if (msg.length < 2) {
        console.warn('Invalid msg: ', ev.data);
        return;
      }
    } catch (jsonErr) {
      console.warn('ChannelService::_onMsg()', jsonErr);
      return;
    }

    const signal = msg[0];
    if (this.connections[signal] == null) {
      console.warn('ChannelService: not handled signal:', signal);
    } else {
      const slots = this.connections[signal];
      const payload = msg[1];
      for (const slot of slots) {
        slot(payload);
      }
    }
  }
}
