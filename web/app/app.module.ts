// Copyright (c) 2017 LiuLang. All rights reserved.
// Use of this source is governed by GPL-3.0 License that can be found
// in the LICENSE file.

import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppComponent } from './app.component';
import { LoginComponent } from './login.component';

import { ChannelService } from './channel.service';

@NgModule({
  declarations: [
    AppComponent,
    LoginComponent
  ],
  imports: [
    BrowserModule
  ],
  providers: [
    ChannelService
  ],
  bootstrap: [
    AppComponent
  ]
})
export class AppModule { }
