import React, { Component } from 'react';

import LoginForm from './login';
import './App.scss';
import Sidebar from './sidebar';

class App extends Component {
  render() {
    return (
      <div className="App">
      <Sidebar/>
      <LoginForm/>
      </div>
    );
  }
}

export default App;
