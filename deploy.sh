#!/bin/bash
# Deployment script for Metal Music Store with SSO and Chatbot

set -e

echo "=== Metal Music Store Deployment ==="
echo "Targeting space: metal-music-store-sso-test"

# Target the space
cf target -o tanzu-platform-demo -s metal-music-store-sso-test

echo ""
echo "=== Checking Services ==="
cf services

echo ""
echo "=== Deploying Applications ==="
cf push -f manifest.yml

echo ""
echo "=== Deployment Complete ==="
echo "Checking application status..."
cf apps

echo ""
echo "=== Application Routes ==="
cf routes | grep metal-music-store


