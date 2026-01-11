const { execSync } = require('child_process');

exports.default = async function (context) {
  const { electronPlatformName, appOutDir } = context;

  if (electronPlatformName !== 'darwin') {
    return;
  }

  const appPath = `${appOutDir}/WeMath2MD.app`;

  console.log('Signing application with ad-hoc signature...');

  try {
    // Remove extended attributes that cause signing issues
    console.log('Removing extended attributes...');
    execSync(`xattr -cr "${appPath}"`, {
      stdio: 'inherit'
    });

    // Ad-hoc signing with "-" and --options=runtime
    console.log('Applying ad-hoc signature...');
    execSync(`codesign --force --deep --sign "-" --options=runtime "${appPath}"`, {
      stdio: 'inherit'
    });
    console.log('Application signed successfully!');
  } catch (error) {
    console.error('Failed to sign application:', error);
    throw error;
  }
};
