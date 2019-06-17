import React from "react";

import './style.scss';

class Sidebar extends React.Component {
  render(): React.ReactNode {
    return (
      <nav>
        <ul>
          <li>
            <a href="/home">Home</a>
          </li>

          <li>
            <a href="/pictures">Pictures</a>
          </li>

          <li>
            <a href="/documents">Documents</a>
          </li>

          <li>
            <a href="/videos">Videos</a>
          </li>

          <li>
            <a href="/bt">BT</a>
          </li>

          <li>
            <a href="/music">Music</a>
          </li>

          <li>
            <a href="/others">Others</a>
          </li>

          <li>
            <a href="/trash">Trash</a>
          </li>

          <li>
            <a href="/cloud-download">Cloud Download</a>
          </li>

          <li>
            <a href="/download">Download</a>
          </li>

          <li>
            <a href="/upload">Upload</a>
          </li>
        </ul>
      </nav>
    );
  }
}

export default Sidebar;
