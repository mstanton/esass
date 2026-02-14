---
description: Automatically fix common Markdown linting errors
---

This workflow ensures your Markdown files follow project standards using `markdownlint-cli2` and a Python fallback.

1. **Prerequisites**
   - Node.js (v20+) managed by NVM.
   - Python 3.8+.

2. **Automated Fix**
   // turbo
   Run the fix script which automatically discovers the local Node/NVM environment and applies fixes.

   ```powershell
   python scripts/fix_markdown.py PATH_TO_FILE
   ```

3. **Manual Trigger (Advanced)**
   If you want to run the standard linter directly:

   ```powershell
   # Ensure Node is in PATH or use nvm use
   npx -y markdownlint-cli2 --fix PATH_TO_FILE
   ```
