from google_play_scraper import app as play_store_app
from rest_framework.response import Response
from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view
from packaging import version
import requests
from drf_yasg.utils import swagger_auto_schema
from app.serializers.app_version_check import *

ANDROID_PACKAGE_NAME = "com.carland"  # Your Android app’s package name
IOS_APP_ID = "6746539445"  # Your iOS app’s numeric ID


def get_play_store_version():
    """Fetch the latest version from the Google Play Store."""
    cache_key = "play_store_version"
    cached_version = cache.get(cache_key)
    if cached_version:
        return cached_version

    try:
        app_details = play_store_app(ANDROID_PACKAGE_NAME, lang="en", country="us")
        version_text = app_details["version"]
        cache.set(cache_key, version_text, timeout=3600)  # Cache for 1 hour
        return version_text
    except Exception as e:
        # logger.error(f"Play Store fetch error: {str(e)}")
        return None


def get_app_store_version():
    """Fetch the latest version from the Apple App Store with country support."""
    cache_key = "app_store_version"
    cached_version = cache.get(cache_key)
    if cached_version:
        return cached_version

    # Your app is in the Uzbekistan App Store, so we need to specify the country
    # Try multiple country codes where your app might be available
    countries_to_try = [
        "uz",  # Uzbekistan (your primary market)
        "us",  # United States (fallback)
        "",    # No country specified (default)
    ]

    for country in countries_to_try:
        try:
            # Build URL with country parameter if specified
            if country:
                url = f"https://itunes.apple.com/lookup?id={IOS_APP_ID}&country={country}"
                country_desc = f"in {country.upper()}"
            else:
                url = f"https://itunes.apple.com/lookup?id={IOS_APP_ID}"
                country_desc = "globally"
            
            print(f"Trying to fetch App Store version {country_desc}: {url}")
            
            response = requests.get(
                url, 
                timeout=15,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/json',
                    'Accept-Language': 'en-US,en;q=0.5',
                }
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"API response: {data}")
                
                if data.get("resultCount", 0) > 0:
                    result = data["results"][0]
                    version_text = result.get("version")
                    
                    if version_text:
                        print(f"Successfully fetched version {country_desc}: {version_text}")
                        cache.set(cache_key, version_text, timeout=3600)
                        return version_text
                    else:
                        print(f"Version field missing in response {country_desc}")
                else:
                    print(f"No results found {country_desc}")
            else:
                print(f"HTTP {response.status_code} {country_desc}")
                
        except requests.exceptions.Timeout:
            print(f"Timeout error {country_desc}")
        except requests.exceptions.RequestException as e:
            print(f"Request error {country_desc}: {str(e)}")
        except ValueError as e:  # JSON decode error
            print(f"JSON decode error {country_desc}: {str(e)}")
        except Exception as e:
            print(f"Unexpected error {country_desc}: {str(e)}")

    # If all attempts fail, try bundle ID approach
    print("Trying bundle ID approach as fallback")
    return get_app_store_version_by_bundle_id()


def get_app_store_version_by_bundle_id():
    """Fallback method using bundle ID."""
    try:
        url = f"https://itunes.apple.com/lookup?bundleId={ANDROID_PACKAGE_NAME}"
        print(f"Trying bundle ID lookup: {url}")
        
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; AppVersionChecker/1.0)'
        })
        
        if response.status_code == 200:
            data = response.json()
            if data.get("resultCount", 0) > 0:
                version_text = data["results"][0].get("version")
                if version_text:
                    print(f"Bundle ID lookup successful: {version_text}")
                    return version_text
        
        print("Bundle ID lookup failed")
        
    except Exception as e:
        print(f"Bundle ID lookup error: {str(e)}")
    
    # Final fallback - return a default version
    print("All App Store lookup methods failed, returning fallback version")
    return "1.0.0"



@swagger_auto_schema(
    method="post",
    operation_summary="Check if the client’s app version is the latest",
    operation_description=(
        "Detects platform from the **User‑Agent** header, fetches the current "
        "store version (Play Store for Android or App Store for iOS), and returns "
        "whether the client is up‑to‑date."
    ),
    tags=["App Version"],
    request_body=AppVersionRequestSerializer,
    responses={
        200: AppVersionResponseSerializer,
        400: ErrorResponseSerializer,
        503: ErrorResponseSerializer,
    },
)
@api_view(["POST"])
def check_app_version(request):
    """API endpoint to check if the client’s app version is the latest."""
    user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
    client_version = request.data.get("app_version")

    # Validate input
    if not client_version:
        return Response(
            {"is_latest": True, "store_version": "0.0.0", "client_version": "0.0.0"},
            status=status.HTTP_200_OK,
        )

    # Determine platform and fetch store version
    if "android" in user_agent:
        latest_version = get_play_store_version()
        store_name = "Play Store"
    elif "iphone" in user_agent or "ipad" in user_agent or "ios" in user_agent:
        latest_version = get_app_store_version()
        store_name = "App Store"
    else:
        return Response(
            {"error": "Unsupported platform"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Check if store version was fetched successfully
    if not latest_version:
        return Response(
            {
                "is_latest": True,
                "store_version": client_version,
                "client_version": client_version,
            },
            status=status.HTTP_200_OK,
        )
    print(f"Latest version from {store_name}: {latest_version}")
    print(f"Client version: {client_version}")
    # Compare versions
    try:
        client_ver = version.parse(client_version)
        store_ver = version.parse(latest_version)

        is_latest = client_ver >= store_ver
        print(f"Is client version latest? {is_latest}")
        print(f"Client version {client_version} is older than store version {latest_version}")
        print(f"Client version {client_version} is up-to-date with store version {latest_version}")

        return Response(
            {
                "is_latest": is_latest,
                "store_version": latest_version,
                "client_version": client_version,
            },
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {
                "is_latest": True,
                "store_version": latest_version,
                "client_version": client_version,
            },
            status=status.HTTP_200_OK,
        )
