const { execSync } = require('child_process');

exports.default = async function (context) {
  const { electronPlatformName, appOutDir } = context;

  if (electronPlatformName !== 'darwin') {
    return;
  }

  const appPath = `${appOutDir}/WeMath2MD.app`;

  console.log('Signing application with ad-hoc signature...');

  try {
    // Ad-hoc signing with "-"
    execSync(`codesign --force --deep --sign "-" "${appPath}"`, {
      stdio: 'inherit'
    });
    console.log('Application signed successfully!');
  } catch (error) {
    console.error('Failed to sign application:', error);
    throw error;
  }
};
