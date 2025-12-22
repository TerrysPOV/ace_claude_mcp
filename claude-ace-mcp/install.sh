#!/bin/bash
#
# claude-ace installer (MCP version)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.ace"

echo "Installing claude-ace (MCP version)..."

# Create directory
mkdir -p "$INSTALL_DIR/bin"

# Copy wrapper
cp "$SCRIPT_DIR/bin/claude-ace" "$INSTALL_DIR/bin/"
chmod +x "$INSTALL_DIR/bin/claude-ace"

# Check for anthropic package (optional, for reflection)
if ! python3 -c "import anthropic" 2>/dev/null; then
    echo ""
    echo "Optional: Install anthropic for post-session reflection:"
    echo "  pip install anthropic"
fi

# PATH instructions
if ! echo "$PATH" | grep -q "$INSTALL_DIR/bin"; then
    echo ""
    echo "Add to PATH:"
    echo ""
    echo "  echo 'export PATH=\"\$HOME/.ace/bin:\$PATH\"' >> ~/.zshrc"
    echo "  source ~/.zshrc"
fi

echo ""
echo "✓ Installed to $INSTALL_DIR/bin/claude-ace"
echo ""
echo "Usage:"
echo "  cd your-project"
echo "  claude-ace setup                    # Configure MCP server"
echo "  claude-ace                          # Start session"
echo "  claude-ace --dangerously-skip-permissions --resume"
echo ""
echo "Requires: ace_claude_mcp server at ~/claude-workspace/ace_claude_mcp/"
