import React, { Component } from 'react';

import LoginForm from './login';
import './App.scss';

class App extends Component {
  render() {
    return (
      <div className="App">
      <LoginForm/>
      </div>
    );
  }
}

export default App;
