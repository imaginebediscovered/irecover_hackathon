#!/bin/bash

# iRecover Frontend Startup Script
# Run this script to start the React development server

set -e

echo "🚀 Starting iRecover Frontend..."

# Check Node.js version
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+"
    exit 1
fi

NODE_VERSION=$(node -v)
echo "📦 Node.js version: $NODE_VERSION"

# Check npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm"
    exit 1
fi

NPM_VERSION=$(npm -v)
echo "📦 npm version: $NPM_VERSION"

# Navigate to frontend directory
cd "$(dirname "$0")"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📥 Installing dependencies..."
    npm install
else
    echo "📦 Dependencies already installed"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
EOF
fi

# Start the development server
echo ""
echo "✅ Frontend starting on http://localhost:5173"
echo "🔄 Press Ctrl+C to stop"
echo ""

npm run dev
