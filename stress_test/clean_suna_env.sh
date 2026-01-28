#!/bin/bash

# Default values
API_URL="http://localhost:8000/api"
API_KEY=""

# Help function
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo "Clean up Suna execution environment by deleting all threads."
    echo ""
    echo "Options:"
    echo "  -k, --key KEY    API Key (format: pk_xxx:sk_xxx)"
    echo "  -u, --url URL    API URL (default: http://localhost:8000/api)"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 -k 'pk_test:sk_test'"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -k|--key)
            API_KEY="$2"
            shift 2
            ;;
        -u|--url)
            API_URL="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check dependencies
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed."
    echo "Please install jq (e.g., sudo apt-get install jq)"
    exit 1
fi

# Check API Key
if [ -z "$API_KEY" ]; then
    echo "Error: API Key is required."
    show_help
    exit 1
fi

echo "Configuration:"
echo "  API URL: $API_URL"
# Mask the secret part of the key for display
PUBLIC_PART=$(echo "$API_KEY" | cut -d':' -f1)
echo "  API Key: $PUBLIC_PART:******"
echo ""

# 1. Get all threads
echo "Fetching thread list..."
THREADS_RESPONSE=$(curl -s -H "x-api-key: $API_KEY" "$API_URL/threads?limit=1000")

# Check for errors in response
if echo "$THREADS_RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    ERROR_MSG=$(echo "$THREADS_RESPONSE" | jq -r '.detail')
    echo "Error fetching threads: $ERROR_MSG"
    exit 1
fi

THREAD_IDS=$(echo "$THREADS_RESPONSE" | jq -r '.threads[].thread_id // empty')

if [ -z "$THREAD_IDS" ]; then
    echo "No threads found to delete."
    exit 0
fi

COUNT=$(echo "$THREAD_IDS" | wc -l)
echo "Found $COUNT threads. Starting deletion..."

# 2. Delete threads
SUCCESS_COUNT=0
FAIL_COUNT=0

for id in $THREAD_IDS; do
    echo -n "Deleting thread $id ... "
    DELETE_RESPONSE=$(curl -s -X DELETE -H "x-api-key: $API_KEY" "$API_URL/threads/$id")
    
    if echo "$DELETE_RESPONSE" | jq -e '.message == "Thread deleted successfully"' > /dev/null 2>&1; then
        echo "✅ OK"
        ((SUCCESS_COUNT++))
    else
        ERROR=$(echo "$DELETE_RESPONSE" | jq -r '.detail // "Unknown error"')
        echo "❌ Failed: $ERROR"
        ((FAIL_COUNT++))
    fi
done

echo ""
echo "Summary:"
echo "  Total: $COUNT"
echo "  Deleted: $SUCCESS_COUNT"
echo "  Failed: $FAIL_COUNT"
