#!/usr/bin/env python3
"""
API Test Script for PDF to EPUB Converter
Tests all endpoints and demonstrates the workflow
"""

import requests
import os
import time

# Configuration
LOCAL_API = "http://localhost:8000"
PROD_API = "https://pdf-epub-converter-api.onrender.com"
TEST_PDF = "sample1.pdf"

def test_api(base_url, name):
    """Test the API endpoints"""
    print(f"\n🧪 Testing {name} API: {base_url}")
    
    # Test 1: Health checks. `/` is Render's probe. `/health` matches auth and library.
    try:
        response = requests.get(f"{base_url}/")
        detailed = requests.get(f"{base_url}/health")
        detailed_ok = (
            detailed.status_code == 200
            and detailed.json().get("status") == "healthy"
        )
        if response.status_code == 200 and detailed_ok:
            print("✅ Health check passed")
        else:
            print(
                f"❌ Health check failed: / {response.status_code}, "
                f"/health {detailed.status_code}"
            )
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test 2: API docs
    try:
        response = requests.get(f"{base_url}/docs")
        if response.status_code == 200:
            print("✅ API documentation accessible")
        else:
            print(f"⚠️  API docs status: {response.status_code}")
    except Exception as e:
        print(f"⚠️  API docs check failed: {e}")
    
    # Test 3: PDF conversion
    if not os.path.exists(TEST_PDF):
        print(f"❌ Test PDF not found: {TEST_PDF}")
        return False
        
    try:
        print(f"📤 Uploading {TEST_PDF}...")
        with open(TEST_PDF, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{base_url}/api/convert", files=files)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ Conversion successful")
                print(f"   📄 Pages: {result.get('pages')}")
                print(f"   📝 Words: {result.get('total_words')}")
                print(f"   🔗 Download URL: {result.get('download_url')}")
                
                # Test 4: Download EPUB
                conversion_id = result.get('conversion_id')
                download_url = result.get('download_url')
                
                if download_url:
                    if download_url.startswith('http'):
                        test_url = download_url
                    else:
                        test_url = f"{base_url}{download_url}"
                    
                    try:
                        print(f"📥 Testing download...")
                        dl_response = requests.get(test_url)
                        if dl_response.status_code == 200:
                            epub_size = len(dl_response.content) / (1024 * 1024)
                            print(f"✅ Download successful ({epub_size:.2f} MB)")
                            return True
                        else:
                            print(f"❌ Download failed: {dl_response.status_code}")
                    except Exception as e:
                        print(f"❌ Download test failed: {e}")
                        
            else:
                print(f"❌ Conversion failed: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Conversion test failed: {e}")
        
    return False

def main():
    print("🚀 PDF to EPUB Converter API Test Suite")
    print("=" * 50)
    
    # Test local API if available
    local_success = False
    try:
        requests.get(LOCAL_API, timeout=2)
        local_success = test_api(LOCAL_API, "Local")
    except:
        print(f"\n⚠️  Local API not accessible: {LOCAL_API}")
    
    # Test production API
    prod_success = test_api(PROD_API, "Production")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    if local_success:
        print("✅ Local API: Working")
    else:
        print("❌ Local API: Not working or not accessible")
        
    if prod_success:
        print("✅ Production API: Working")
    else:
        print("❌ Production API: Not working")
        
    print(f"\n🌐 Frontend URL: https://w1neskin.github.io/pdf-epub-converter/")
    print(f"📚 API Docs: {PROD_API}/docs")

if __name__ == "__main__":
    main() 