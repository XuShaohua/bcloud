import React from "react";
import './style.scss';

class LoginForm extends React.Component {

  render(): React.ReactNode {
    return (
      <form className="login-form">
        <input type="text" placeholder="Phone/Email/Username"/>
        <input type="password" placeholder="Password"/>
        <input type="checkbox" id="login-mem-pass" name="memPass" checked/>
        <label htmlFor="login-mem-pass">Remember password</label>
        <input type="submit" value="Sign In"/>
      </form>
    );
  }
}

export default LoginForm;
