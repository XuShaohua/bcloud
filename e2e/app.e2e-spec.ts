import { BcloudWebPage } from './app.po';

describe('bcloud-web App', () => {
  let page: BcloudWebPage;

  beforeEach(() => {
    page = new BcloudWebPage();
  });

  it('should display welcome message', () => {
    page.navigateTo();
    expect(page.getParagraphText()).toEqual('Welcome to app!!');
  });
});
