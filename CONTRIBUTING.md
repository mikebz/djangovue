# Contributing to djangovue

First off, thank you for considering contributing to `djangovue`! 

## Browser Support & Local Testing Requirements

Because this project serves as a foundational starter template, we maintain strict cross-browser compatibility standards. 

**Maintainer & Contributor Requirements:**
To safely merge front-end UI changes (Vue/Vite modifications), maintainers and contributors are **strictly required** to perform local cross-browser compatibility testing across different rendering engines. 

Specifically, due to known differences in WebKit rendering and JavaScript API support (e.g., `requestIdleCallback`), all frontend UI modifications **must be tested locally in Safari on macOS**. Relying solely on Chromium-based browsers during local development is insufficient and can lead to critical regressions for Apple platform users.

## Pull Request Process
1. Ensure your local environment passes all checks (`make verify`).
2. **Verify UI changes in both Chrome and Safari.**
3. Submit your PR with a description of the changes and screenshots if applicable.
