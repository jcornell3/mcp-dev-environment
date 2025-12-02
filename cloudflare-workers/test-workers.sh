#!/bin/bash
# Test script for Cloudflare Workers MCP servers
# Usage: ./test-workers.sh <santa-clara-url> <math-url> <santa-clara-key> <math-key>

if [ $# -ne 4 ]; then
    echo "Usage: $0 <santa-clara-url> <math-url> <santa-clara-key> <math-key>"
    echo ""
    echo "Example:"
    echo "  $0 'https://santa-clara.account.workers.dev' 'https://math.account.workers.dev' '6c2da9cf...' '7dce5a53...'"
    exit 1
fi

SANTA_CLARA_URL="$1"
MATH_URL="$2"
SANTA_CLARA_KEY="$3"
MATH_KEY="$4"

echo "════════════════════════════════════════════════════════════════════════════════"
echo "TESTING CLOUDFLARE WORKERS MCP SERVERS"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# Test Santa Clara
echo "SANTA CLARA WORKER TESTS"
echo "════════════════════════════════════════════════════════════════════════════════"
echo "URL: $SANTA_CLARA_URL"
echo ""

echo "Test 1: Initialize"
curl -s -X POST "$SANTA_CLARA_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SANTA_CLARA_KEY" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' | jq .

echo ""
echo "Test 2: List Tools"
curl -s -X POST "$SANTA_CLARA_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SANTA_CLARA_KEY" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":2}' | jq .

echo ""
echo "Test 3: Get Property Info (APN: 288-12-033)"
curl -s -X POST "$SANTA_CLARA_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SANTA_CLARA_KEY" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_property_info","arguments":{"apn":"288-12-033"}},"id":3}' | jq .

echo ""
echo ""
echo "MATH WORKER TESTS"
echo "════════════════════════════════════════════════════════════════════════════════"
echo "URL: $MATH_URL"
echo ""

echo "Test 1: Initialize"
curl -s -X POST "$MATH_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MATH_KEY" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' | jq .

echo ""
echo "Test 2: List Tools"
curl -s -X POST "$MATH_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MATH_KEY" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":2}' | jq .

echo ""
echo "Test 3: Calculate (5 + 3)"
curl -s -X POST "$MATH_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MATH_KEY" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"calculate","arguments":{"operation":"add","a":5,"b":3}},"id":3}' | jq .

echo ""
echo "Test 4: Calculate (16 / 4)"
curl -s -X POST "$MATH_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MATH_KEY" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"calculate","arguments":{"operation":"divide","a":16,"b":4}},"id":4}' | jq .

echo ""
echo "Test 5: Calculate (5^3 = 125)"
curl -s -X POST "$MATH_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MATH_KEY" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"calculate","arguments":{"operation":"power","a":5,"b":3}},"id":5}' | jq .

echo ""
echo "Test 6: Factorial (10! = 3628800)"
curl -s -X POST "$MATH_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MATH_KEY" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"factorial","arguments":{"n":10}},"id":6}' | jq .

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "Tests complete!"
echo "════════════════════════════════════════════════════════════════════════════════"
