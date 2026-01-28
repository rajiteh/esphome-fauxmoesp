#!/usr/bin/env python3
"""
Test FauxmoESP component using direct HTTP requests to the Hue API.

This script tests that FauxmoESP correctly emulates a Philips Hue Bridge
by making the same HTTP requests that Alexa and Hue apps would make.

Usage:
    python test_fauxmo.py <esp-ip-address>
    python test_fauxmo.py <esp-ip-address> --discover

Example:
    python test_fauxmo.py 192.168.1.100
    python test_fauxmo.py 192.168.1.100 --interactive
"""

import sys
import time
import socket
import argparse
import json
import http.client
import urllib.request
import urllib.error


class FauxmoClient:
    """Simple client for FauxmoESP Hue API."""

    def __init__(self, ip, port=80, username="fauxmo"):
        self.ip = ip
        self.port = port
        self.username = username
        self.base_url = f"http://{ip}:{port}/api/{username}"

    def _request(self, method, path, data=None):
        """Make HTTP request to the device."""
        url = f"{self.base_url}{path}"

        req = urllib.request.Request(url, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Connection", "close")

        if data is not None:
            data = json.dumps(data).encode("utf-8")

        try:
            with urllib.request.urlopen(req, data, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection error: {e.reason}")
        except http.client.RemoteDisconnected:
            # FauxmoESP may close connection after response, this is expected for PUT
            return [{"success": True}]

    def get_lights(self):
        """Get all lights."""
        return self._request("GET", "/lights")

    def get_light(self, light_id):
        """Get a specific light."""
        return self._request("GET", f"/lights/{light_id}")

    def set_light_state(self, light_id, state):
        """Set light state (on, bri, etc.)."""
        return self._request("PUT", f"/lights/{light_id}/state", state)

    def turn_on(self, light_id, brightness=None):
        """Turn on a light, optionally setting brightness."""
        state = {"on": True}
        if brightness is not None:
            state["bri"] = brightness
        return self.set_light_state(light_id, state)

    def turn_off(self, light_id):
        """Turn off a light."""
        return self.set_light_state(light_id, {"on": False})

    def set_brightness(self, light_id, brightness):
        """Set brightness (0-254)."""
        return self.set_light_state(light_id, {"on": True, "bri": brightness})


def discover_ssdp_devices(timeout=5):
    """
    Discover devices using SSDP (Simple Service Discovery Protocol).
    This is the same method Alexa uses to find Hue bridges.
    Note: Won't work across VLANs without multicast routing.
    """
    print("🔍 Discovering devices via SSDP (same method Alexa uses)...")
    print(f"   Listening for {timeout} seconds...\n")

    # SSDP multicast parameters
    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900
    SSDP_MX = 3
    SSDP_ST = "urn:schemas-upnp-org:device:basic:1"

    # M-SEARCH request message
    ssdp_request = "\r\n".join(
        [
            "M-SEARCH * HTTP/1.1",
            f"HOST: {SSDP_ADDR}:{SSDP_PORT}",
            'MAN: "ssdp:discover"',
            f"MX: {SSDP_MX}",
            f"ST: {SSDP_ST}",
            "",
            "",
        ]
    ).encode("utf-8")

    devices = []

    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)

        # Send M-SEARCH request
        sock.sendto(ssdp_request, (SSDP_ADDR, SSDP_PORT))

        # Collect responses
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(65507)
                response = data.decode("utf-8", errors="ignore")

                # Parse response for Hue-like devices
                if "hue" in response.lower() or "IpBridge" in response:
                    ip = addr[0]

                    # Extract location if present
                    location = None
                    for line in response.split("\r\n"):
                        if line.lower().startswith("location:"):
                            location = line.split(":", 1)[1].strip()
                            break

                    devices.append(
                        {"ip": ip, "location": location, "response": response}
                    )

                    print(f"  ✅ Found device at {ip}")
                    if location:
                        print(f"     Location: {location}")

            except socket.timeout:
                break

        sock.close()

    except Exception as e:
        print(f"  ⚠️  Discovery error: {e}")
        return []

    if not devices:
        print("  ⚠️  No devices found via SSDP")
        print("\nTroubleshooting:")
        print("  - Ensure ESP device is on the same network/VLAN")
        print("  - Check firewall isn't blocking UDP port 1900")
        print("  - Verify FauxmoESP component is running")
        print("  - SSDP multicast doesn't work across VLANs")
    else:
        print(f"\n✅ Found {len(devices)} device(s) via SSDP\n")

    return devices


def test_connection(ip):
    """Test basic connection to FauxmoESP."""
    print(f"🔌 Connecting to FauxmoESP device at {ip}...")

    try:
        client = FauxmoClient(ip)
        lights = client.get_lights()
        print("✅ Connected successfully!\n")
        return client
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  - Ensure ESP device is on the network")
        print("  - Check that FauxmoESP is using port 80")
        print("  - Verify IP address is correct")
        sys.exit(1)


def list_devices(client):
    """List all available devices."""
    print("📋 Discovered Devices:")
    print("-" * 50)

    try:
        lights = client.get_lights()
    except Exception as e:
        print(f"❌ Failed to get lights: {e}")
        return {}

    if not lights:
        print("⚠️  No devices found!")
        return {}

    for light_id, light in lights.items():
        print(f"  • {light.get('name', 'Unknown')}")
        print(f"    ID: {light_id}")
        print(f"    Type: {light.get('type', 'Unknown')}")
        print(f"    Unique ID: {light.get('uniqueid', 'N/A')}")
        print()

    return lights


def test_on_off(client, light_id):
    """Test turning device on and off."""
    print(f"🔦 Testing ON/OFF for device {light_id}...")

    try:
        # Turn ON
        result = client.turn_on(light_id)
        print(f"  ✅ Turned ON - Response: {result}")
        time.sleep(1)

        # Turn OFF
        result = client.turn_off(light_id)
        print(f"  ✅ Turned OFF - Response: {result}")
        time.sleep(1)

        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_brightness(client, light_id):
    """Test brightness control."""
    print(f"💡 Testing BRIGHTNESS for device {light_id}...")

    brightness_levels = [64, 128, 192, 254]  # 25%, 50%, 75%, 100%

    try:
        for bri in brightness_levels:
            percentage = int((bri / 254) * 100)
            result = client.set_brightness(light_id, bri)
            print(f"  ✅ Set to {percentage}% (brightness {bri}/254)")
            time.sleep(0.5)

        # Turn off at the end
        client.turn_off(light_id)
        print("  ✅ Turned OFF")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_description_xml(ip):
    """Test the description.xml endpoint."""
    print("📄 Testing description.xml endpoint...")

    try:
        url = f"http://{ip}/description.xml"
        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read().decode("utf-8")

        if "Philips hue" in content:
            print("  ✅ description.xml returns Philips Hue device info")
            return True
        else:
            print("  ⚠️  description.xml doesn't look like Hue response")
            return False
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def run_full_test_suite(ip, test_discovery=False):
    """Run complete test suite."""
    print("=" * 50)
    print("   FauxmoESP Test Suite")
    print("   Direct HTTP API Testing")
    print("=" * 50)
    print()

    results = {}

    # Test SSDP discovery if requested
    if test_discovery:
        devices = discover_ssdp_devices()
        results["ssdp_discovery"] = len(devices) > 0
        print()

    # Test description.xml
    results["description_xml"] = test_description_xml(ip)
    print()

    # Connect
    client = test_connection(ip)
    results["connection"] = True  # If we get here, connection succeeded

    # List devices
    lights = list_devices(client)

    if not lights:
        print("⚠️  No devices to test. Check your ESPHome configuration.")
        return

    # Test first device
    first_light_id = list(lights.keys())[0]
    first_light_name = lights[first_light_id].get("name", "Unknown")
    print(f"🧪 Running tests on device: {first_light_name} (ID: {first_light_id})")
    print("=" * 50)
    print()

    results["on_off"] = test_on_off(client, first_light_id)
    print()
    results["brightness"] = test_brightness(client, first_light_id)

    print()
    print("=" * 50)
    print("   Test Results Summary")
    print("=" * 50)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")

    print()

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! FauxmoESP is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

    return passed == total


def interactive_mode(ip):
    """Interactive testing mode."""
    client = test_connection(ip)
    lights = list_devices(client)

    if not lights:
        return

    print("\n🎮 Interactive Mode")
    print("Commands: on <id>, off <id>, bri <id> <0-254>, list, quit")
    print()

    while True:
        try:
            cmd = input(">>> ").strip().lower().split()

            if not cmd:
                continue

            if cmd[0] == "quit" or cmd[0] == "exit":
                break

            elif cmd[0] == "list":
                list_devices(client)

            elif cmd[0] == "on" and len(cmd) > 1:
                light_id = cmd[1]
                result = client.turn_on(light_id)
                print(f"✅ Device {light_id} turned ON - {result}")

            elif cmd[0] == "off" and len(cmd) > 1:
                light_id = cmd[1]
                result = client.turn_off(light_id)
                print(f"✅ Device {light_id} turned OFF - {result}")

            elif cmd[0] == "bri" and len(cmd) > 2:
                light_id = cmd[1]
                brightness = int(cmd[2])
                result = client.set_brightness(light_id, brightness)
                print(
                    f"✅ Device {light_id} brightness set to {brightness}/254 - {result}"
                )

            else:
                print(
                    "Unknown command. Use: on <id>, off <id>, bri <id> <0-254>, list, quit"
                )

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Test FauxmoESP using direct HTTP API calls",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_fauxmo.py 192.168.1.100
  python test_fauxmo.py 192.168.1.100 --discover
  python test_fauxmo.py --discover-only
  python test_fauxmo.py 192.168.1.100 --interactive
  python test_fauxmo.py 192.168.1.100 --list
        """,
    )

    parser.add_argument(
        "ip", nargs="?", help="IP address of the ESP device running FauxmoESP"
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Run in interactive mode"
    )
    parser.add_argument(
        "-l", "--list", action="store_true", help="Only list devices and exit"
    )
    parser.add_argument(
        "-d",
        "--discover",
        action="store_true",
        help="Test SSDP discovery before running other tests",
    )
    parser.add_argument(
        "--discover-only", action="store_true", help="Only test SSDP discovery and exit"
    )

    args = parser.parse_args()

    if args.discover_only:
        devices = discover_ssdp_devices()
        if devices:
            print("\n💡 Tip: Use one of the discovered IPs to run full tests:")
            print(f"   python test_fauxmo.py {devices[0]['ip']}")
    elif args.list:
        if not args.ip:
            print("Error: IP address required for --list")
            sys.exit(1)
        client = test_connection(args.ip)
        list_devices(client)
    elif args.interactive:
        if not args.ip:
            print("Error: IP address required for --interactive")
            sys.exit(1)
        interactive_mode(args.ip)
    else:
        if not args.ip:
            print("Error: IP address required (or use --discover-only)")
            parser.print_help()
            sys.exit(1)
        success = run_full_test_suite(args.ip, test_discovery=args.discover)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
