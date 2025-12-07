#!/usr/bin/env python3
"""
Unit tests for Google Drive integration
Tests the upload functionality with a small test MP3 file
"""

import os
import sys
import json
import tempfile
from datetime import datetime

# Add the server directory to path
sys.path.insert(0, '/home/jcornell/mcp-dev-environment/servers/youtube-to-mp3')

def test_credentials_configured():
    """Test 1: Verify credentials are properly configured"""
    print("\n" + "="*80)
    print("TEST 1: Verify Google Drive credentials configuration")
    print("="*80)

    from google_drive import is_drive_configured

    # Set environment variable
    os.environ['GOOGLE_DRIVE_CREDENTIALS_JSON'] = '/home/jcornell/google-credentials/google-drive-token.json'

    is_configured = is_drive_configured()

    if is_configured:
        print("✅ PASS: Google Drive credentials are configured")
        return True
    else:
        print("❌ FAIL: Google Drive credentials not found")
        return False


def test_drive_service_connection():
    """Test 2: Verify we can connect to Google Drive API"""
    print("\n" + "="*80)
    print("TEST 2: Test Google Drive API connection")
    print("="*80)

    os.environ['GOOGLE_DRIVE_CREDENTIALS_JSON'] = '/home/jcornell/google-credentials/google-drive-token.json'

    try:
        from google_drive import get_drive_service
        service = get_drive_service()

        # Try to list files (just to verify connection)
        results = service.files().list(pageSize=1, fields="files(id, name)").execute()

        print("✅ PASS: Successfully connected to Google Drive API")
        print(f"   Connection verified by listing files")
        return True
    except Exception as e:
        print(f"❌ FAIL: Could not connect to Google Drive API")
        print(f"   Error: {str(e)}")
        return False


def test_create_test_folder():
    """Test 3: Get or create standardized MCP-YouTube-to-MP3 folder"""
    print("\n" + "="*80)
    print("TEST 3: Get or create standardized MCP-YouTube-to-MP3 folder")
    print("="*80)

    os.environ['GOOGLE_DRIVE_CREDENTIALS_JSON'] = '/home/jcornell/google-credentials/google-drive-token.json'

    try:
        from google_drive import get_or_create_folder

        folder_name = "MCP-YouTube-to-MP3"
        folder_id = get_or_create_folder(folder_name)

        print(f"✅ PASS: Using standardized folder '{folder_name}'")
        print(f"   Folder ID: {folder_id}")
        return folder_id
    except Exception as e:
        print(f"❌ FAIL: Could not get/create standardized folder")
        print(f"   Error: {str(e)}")
        return None


def test_upload_file(folder_id=None):
    """Test 4: Upload a test MP3 file"""
    print("\n" + "="*80)
    print("TEST 4: Upload test MP3 file to Google Drive")
    print("="*80)

    os.environ['GOOGLE_DRIVE_CREDENTIALS_JSON'] = '/home/jcornell/google-credentials/google-drive-token.json'

    # Create a small test MP3 file
    test_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.mp3', delete=False)
    test_file_path = test_file.name

    # Write minimal MP3 header (ID3v2 tag)
    test_file.write(b'ID3\x03\x00\x00\x00\x00\x00\x00')  # ID3v2.3 header
    test_file.write(b'\x00' * 100)  # Some padding
    test_file.close()

    try:
        from google_drive import upload_to_drive

        result = upload_to_drive(
            file_path=test_file_path,
            folder_id=folder_id,
            file_name=f"test_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        )

        print(f"✅ PASS: Successfully uploaded test file")
        print(f"   File ID: {result['file_id']}")
        print(f"   File name: {result['name']}")
        print(f"   View link: {result['web_view_link']}")
        print(f"   File size: {result['size']} bytes")

        # Clean up test file
        os.unlink(test_file_path)

        return result
    except Exception as e:
        print(f"❌ FAIL: Could not upload test file")
        print(f"   Error: {str(e)}")

        # Clean up test file
        try:
            os.unlink(test_file_path)
        except:
            pass

        return None


def test_health_endpoint():
    """Test 5: Verify health endpoint shows Google Drive configured"""
    print("\n" + "="*80)
    print("TEST 5: Check MCP server health endpoint")
    print("="*80)

    import requests

    try:
        response = requests.get('http://127.0.0.1:3004/health', timeout=5)
        health_data = response.json()

        print(f"Status: {health_data.get('status')}")
        print(f"Service: {health_data.get('service')}")
        print(f"API Key Configured: {health_data.get('api_key_configured')}")
        print(f"Google Drive Configured: {health_data.get('google_drive_configured')}")

        if health_data.get('google_drive_configured') == True:
            print("✅ PASS: Health endpoint confirms Google Drive is configured")
            return True
        else:
            print("❌ FAIL: Health endpoint shows Google Drive not configured")
            return False
    except Exception as e:
        print(f"❌ FAIL: Could not connect to health endpoint")
        print(f"   Error: {str(e)}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "#"*80)
    print("# GOOGLE DRIVE INTEGRATION - UNIT TESTS")
    print("#"*80)

    results = []

    # Test 1: Credentials configured
    results.append(("Credentials Configuration", test_credentials_configured()))

    # Test 2: Drive service connection
    results.append(("API Connection", test_drive_service_connection()))

    # Test 3: Create test folder
    folder_id = test_create_test_folder()
    results.append(("Folder Creation", folder_id is not None))

    # Test 4: Upload file
    upload_result = test_upload_file(folder_id)
    results.append(("File Upload", upload_result is not None))

    # Test 5: Health endpoint
    results.append(("Health Endpoint", test_health_endpoint()))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Google Drive integration is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
