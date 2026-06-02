#!/bin/bash
# Ensure we're on the feature branch, not main

cd /Users/orenpenso/git/metal-music-store

CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" = "main" ]; then
    echo "ERROR: Currently on main branch!"
    echo "Creating and switching to feature/add-sso-and-chatbot branch..."
    git checkout -b feature/add-sso-and-chatbot
    echo "Switched to feature/add-sso-and-chatbot"
else
    echo "Already on feature branch: $CURRENT_BRANCH"
fi

echo ""
echo "Current branch: $(git branch --show-current)"
echo ""
echo "Uncommitted changes:"
git status --short


