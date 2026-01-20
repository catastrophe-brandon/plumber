#!/bin/bash
# Setup git hooks for the plumber project
# Run this script to install pre-commit hooks that ensure code quality

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
HOOKS_DIR="${REPO_ROOT}/.git/hooks"

echo "Setting up git hooks for plumber..."

# Create pre-commit hook
cat > "${HOOKS_DIR}/pre-commit" << 'EOF'
#!/bin/bash
# Pre-commit hook to run ruff linter and formatter

echo "Running ruff linter..."
if ! ruff check .; then
    echo "❌ Ruff linter found issues. Please fix them before committing."
    echo "   Run: ruff check . --fix"
    exit 1
fi

echo "Running ruff formatter check..."
if ! ruff format . --check; then
    echo "❌ Code formatting issues found. Please format your code before committing."
    echo "   Run: ruff format ."
    exit 1
fi

echo "✅ All ruff checks passed!"
exit 0
EOF

# Make the hook executable
chmod +x "${HOOKS_DIR}/pre-commit"

echo "✅ Git hooks installed successfully!"
echo ""
echo "The pre-commit hook will now:"
echo "  - Run ruff linter before each commit"
echo "  - Run ruff formatter check before each commit"
echo "  - Prevent commits if issues are found"
echo ""
echo "To bypass the hook (not recommended), use: git commit --no-verify"