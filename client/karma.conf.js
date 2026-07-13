// Configuration Karma partagée par le dev local et la CI.
// En local, `ng test` utilise Chrome (ou ChromeHeadless) normalement : karma-chrome-launcher
// détecte automatiquement une installation Chrome standard, CHROME_BIN n'est pas requis.
// En CI (voir .github/workflows), CHROME_BIN est positionné explicitement sur le Chromium
// fourni par Puppeteer (devDependency), et ChromeHeadlessCI ajoute --no-sandbox, requis
// dans la plupart des conteneurs CI où l'utilisateur n'a pas les privilèges du sandbox Chrome.

module.exports = function (config) {
  config.set({
    basePath: '',
    frameworks: ['jasmine', '@angular-devkit/build-angular'],
    plugins: [
      require('karma-jasmine'),
      require('karma-chrome-launcher'),
      require('karma-jasmine-html-reporter'),
      require('karma-coverage'),
      require('@angular-devkit/build-angular/plugins/karma'),
    ],
    client: {
      jasmine: {},
      clearContext: false,
    },
    jasmineHtmlReporter: {
      suppressAll: true,
    },
    coverageReporter: {
      dir: require('path').join(__dirname, './coverage/shop-wise'),
      subdir: '.',
      reporters: [{ type: 'html' }, { type: 'text-summary' }],
    },
    reporters: ['progress', 'kjhtml'],
    port: 9876,
    colors: true,
    logLevel: config.LOG_INFO,
    autoWatch: true,
    customLaunchers: {
      ChromeHeadlessCI: {
        base: 'ChromeHeadless',
        flags: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
      },
    },
    singleRun: false,
    restartOnFileChange: true,
  });
};
