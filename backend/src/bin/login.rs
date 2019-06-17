
extern crate chrono;
extern crate regex;
extern crate reqwest;
extern crate serde;

use std::collections::HashMap;
use chrono::prelude::*;
use reqwest::header::{ COOKIE, USER_AGENT };
use serde::Deserialize;

const DEFAULT_UA: &'static str = "Mozilla/5.0 (X11; Linux x86_64; rv:67.0) Gecko/20100101 Firefox/67.0";

#[derive(Debug, Default)]
struct Login {
    cookies: HashMap<String, String>,
    trace_id: String,
    server_time: String,
    rsa_pub_key: String,

    pub token: String,
}

impl Login {

    pub fn get_trace_id(&mut self) {
        println!("get_trace_id()");
        let resp = reqwest::Client::new().get("https://wappass.baidu.com/")
            .send().unwrap();
        for cookie in resp.cookies() {
            self.cookies.insert(cookie.name().to_string(), cookie.value().to_string());
        }
        self.trace_id = resp.headers().get("Trace-Id").unwrap().to_str()
            .expect("get trace id failed")
            .to_string();
    }

    pub fn get_server_time(&mut self) {
        println!("get_server_time()");
        let mut resp = reqwest::Client::new().get("https://wappass.baidu.com/wp/api/security/antireplaytoken")
            .header(COOKIE, self.to_cookie_str())
            .send().unwrap();
        for cookie in resp.cookies() {
            self.cookies.insert(cookie.name().to_string(), cookie.value().to_string());
        }

        #[derive(Debug, Deserialize)]
        struct ReplayToken {
            errno: i32,
            errmsg: String,
            time: String,
        }

        let replay_token: ReplayToken = resp.json().unwrap();
        self.server_time = replay_token.time.clone();
    }

    pub fn get_rsa_pub_key(&mut self) {
        println!("get_rsa_pub_key()");
        let mut resp = reqwest::Client::new().get("https://wappass.bdimg.com/static/touch/pkg/template_touch_show_login_aio_19fd620.js")
            .header(COOKIE, self.to_cookie_str())
            .send().unwrap();
        for cookie in resp.cookies() {
            self.cookies.insert(cookie.name().to_string(), cookie.value().to_string());
        }

        let pattern = regex::Regex::new(r#",rsa:"(.*)?",error"#).unwrap();
        let body = resp.text().unwrap();
        let captures = pattern.captures(&body).unwrap();
        self.rsa_pub_key = captures[1].to_string();
    }

    fn enc_password(&self, password: &str) -> String {
        let t = format!("{}{}", password, self.server_time);
    }

    pub fn login(&mut self, username: &str, password: &str, verifycode: &str, vcodestr: &str) {
        let timestamp = format!("{}773_357", Local::now().timestamp());
        let enc_passwd = self.enc_password(password);

        let login_form: HashMap<&str, &str> = [
            ("username", username),
            ("password", &enc_passwd),
            ("verifycode", verifycode),
            ("vcodestr",  vcodestr),
            ("isphone", "0"),
            ("loginmerge", "1"),
            ("action", "login"),
            ("uid", &timestamp),
            ("skin", "default_v2"),
            ("connect", "0"),
            ("dv", "tk0.408376350146535171516806245342@oov0QqrkqfOuwaCIxUELn3oYlSOI8f51tbnGy-nk3crkqfOuwaCIxUou2iobENoYBf51tb4Gy-nk3cuv0ounk5vrkBynGyvn1QzruvN6z3drLJi6LsdFIe3rkt~4Lyz5ktfn1Qlrk5v5D5fOuwaCIxUobJWOI3~rkt~4Lyi5kBfni0vrk8~n15fOuwaCIxUobJWOI3~rkt~4Lyz5DQfn1oxrk0v5k5eruvN6z3drLneFYeVEmy-nk3c-qq6Cqw3h7CChwvi5-y-rkFizvmEufyr1By4k5bn15e5k0~n18inD0b5D8vn1Tyn1t~nD5~5T__ivmCpA~op5gr-wbFLhyFLnirYsSCIAerYnNOGcfEIlQ6I6VOYJQIvh515f51tf5DBv5-yln15f5DFy5myl5kqf5DFy5myvnktxrkT-5T__Hv0nq5myv5myv4my-nWy-4my~n-yz5myz4Gyx4myv5k0f5Dqirk0ynWyv5iTf5DB~rk0z5Gyv4kTf5DQxrkty5Gy-5iQf51B-rkt~4B__"),
            //("getpassUrl", "/passport/getpass?clientfrom=&adapter=0&ssid=&from=&authsite=&bd_page_type=&uid=" + timestampStr + "&pu=&tpl=wimn&u=https://m.baidu.com/usrprofile%3Fuid%3D" + timestampStr + "%23logined&type=&bdcm=060d5ffd462309f7e5529822720e0cf3d7cad665&tn=&regist_mode=&login_share_strategy=&subpro=wimn&skin=default_v2&client=&connect=0&smsLoginLink=1&loginLink=&bindToSmsLogin=&overseas=&is_voice_sms=&subpro=wimn&hideSLogin=&forcesetpwd=&regdomestic="),
            ("mobilenum", "undefined"),
            ("servertime", &self.server_time),
            ("gid", "DA7C3AE-AF1F-48C0-AF9C-F1882CA37CD5"),
            ("logLoginType", "wap_loginTouch"),
            ("FP_UID", "0b58c206c9faa8349576163341ef1321"),
            ("traceid", &self.trace_id),
        ].iter().cloned().collect();
        let login_resp = reqwest::Client::new().post("https://wappass.baidu.com/wp/api/login")
            .header(USER_AGENT, DEFAULT_UA)
            .form(&login_form)
            .send().unwrap();
        println!("login resp: {:?}", login_resp);
    }

    fn to_cookie_str(&self) -> String {
        return "".to_string();
    }
}

fn main() {
    let mut l = Login::default();
    l.get_server_time();
    l.get_trace_id();
    l.get_rsa_pub_key();
    l.login("13871096052", "password", "", "");
    println!("login: {:?}", l);
}
