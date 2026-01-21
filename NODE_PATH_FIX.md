# Node.js PATH Issue Fix

## Issue
Node.js is installed but not accessible via the `node` command in Git Bash.

## Temporary Solution (Current)
Use the direct esbuild command for development:

```bash
# For development with watch mode
./node_modules/.bin/esbuild main.ts --bundle --external:obsidian --external:electron --format=cjs --target=es2018 --outfile=main.js --watch

# For production build
./node_modules/.bin/esbuild main.ts --bundle --external:obsidian --external:electron --format=cjs --target=es2018 --outfile=main.js
```

## Permanent Solution
The issue is that Git Bash doesn't see Node.js in the PATH. I've created symlinks in your user bin directory:

```bash
# These have been created:
/c/Users/Tsunade/bin/node -> "C:\Program Files\nodejs\node.exe"
/c/Users/Tsunade/bin/npm -> "C:\Program Files\nodejs\npm.cmd"
```

## Alternative: Fix Windows PATH
1. Open System Properties → Advanced → Environment Variables
2. Check that `C:\Program Files\nodejs` is in your PATH
3. Move it to the top of the PATH if it exists
4. If not, add it to the PATH
5. Restart your terminal/Git Bash

## Verification
After fixing, these should work:
```bash
node --version  # Should show v22.15.0
npm --version   # Should show 10.9.2
```

## Current Status
✅ Plugin builds successfully with direct esbuild
✅ Node.js accessible via full path
🔄 npm run commands need PATH fix to work properly