console.log('Testing Electron module...');
console.log('require:', typeof require);
console.log('Requiring electron module...');

const electronModule = require('electron');
console.log('electronModule:', electronModule);
console.log('electronModule type:', typeof electronModule);
console.log('electronModule keys:', Object.keys(electronModule || {}));

const app = electronModule.app;
console.log('app:', app);
console.log('app type:', typeof app);

if (app && typeof app.whenReady === 'function') {
  console.log('SUCCESS: app.whenReady is available!');
  process.exit(0);
} else {
  console.log('FAIL: app.whenReady is not available');
  process.exit(1);
}
