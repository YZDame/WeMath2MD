const { execSync } = require('child_process');

// Hook runs after packaging but BEFORE signing
exports.default = async function (context) {
  const { electronPlatformName, appOutDir } = context;

  if (electronPlatformName !== 'darwin') {
    return;
  }

  const appPath = `${appOutDir}/WeMath2MD.app`;

  console.log('beforePack: Cleaning extended attributes before signing...');

  try {
    // Remove all extended attributes from the app bundle
    // This must be done BEFORE electron-builder tries to sign
    execSync(`xattr -cr "${appPath}"`, {
      stdio: 'inherit'
    });

    // Also clean any Finder metadata
    execSync(`find "${appPath}" -type f -exec dscl . -delete /Users/$(whoami) {} \\; 2>/dev/null || true`, {
      stdio: 'inherit'
    });

    console.log('Extended attributes cleaned. Proceeding with signing...');
  } catch (error) {
    console.error('Failed to clean extended attributes:', error.message);
    // Don't throw - electron-builder will continue
  }
};
