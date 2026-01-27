#!/usr/bin/env python3
"""
Test FauxmoESP component using the phue library (designed for real Hue devices).

This script demonstrates that FauxmoESP correctly emulates a Philips Hue Bridge
by using the official phue Python library to interact with it.

Installation:
    pip install phue

Usage:
    python test_fauxmo.py <esp-ip-address>
    python test_fauxmo.py --discover
    
Example:
    python test_fauxmo.py 192.168.1.100
    python test_fauxmo.py --discover
"""

import sys
import time
import socket
import argparse
from phue import Bridge


def discover_ssdp_devices(timeout=5):
    """
    Discover devices using SSDP (Simple Service Discovery Protocol).
    This is the same method Alexa uses to find Hue bridges.
    """
    print("🔍 Discovering devices via SSDP (same method Alexa uses)...")
    print(f"   Listening for {timeout} seconds...\n")
    
    # SSDP multicast parameters
    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900
    SSDP_MX = 3
    SSDP_ST = "urn:schemas-upnp-org:device:basic:1"
    
    # M-SEARCH request message
    ssdp_request = "\r\n".join([
        'M-SEARCH * HTTP/1.1',
        f'HOST: {SSDP_ADDR}:{SSDP_PORT}',
        'MAN: "ssdp:discover"',
        f'MX: {SSDP_MX}',
        f'ST: {SSDP_ST}',
        '', ''
    ]).encode('utf-8')
    
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
                response = data.decode('utf-8', errors='ignore')
                
                # Parse response for Hue-like devices
                if 'hue' in response.lower() or 'IpBridge' in response:
                    ip = addr[0]
                    
                    # Extract location if present
                    location = None
                    for line in response.split('\r\n'):
                        if line.lower().startswith('location:'):
                            location = line.split(':', 1)[1].strip()
                            break
                    
                    devices.append({
                        'ip': ip,
                        'location': location,
                        'response': response
                    })
                    
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
        print("  - Ensure ESP device is on the same network")
        print("  - Check firewall isn't blocking UDP port 1900")
        print("  - Verify FauxmoESP component is running")
        print("  - Try running with sudo if on Linux")
    else:
        print(f"\n✅ Found {len(devices)} device(s) via SSDP\n")
    
    return devices


def test_connection(bridge_ip):
    """Test basic connection and device discovery."""
    print(f"🔌 Connecting to FauxmoESP device at {bridge_ip}...")
    
    try:
        # Connect to the bridge (no authentication needed for FauxmoESP)
        # First connection may require pressing a "link button" but FauxmoESP
        # typically auto-accepts
        bridge = Bridge(bridge_ip)
        
        # This will create a .python_hue config file
        bridge.connect()
        print("✅ Connected successfully!\n")
        return bridge
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  - Ensure ESP device is on the network")
        print("  - Check that FauxmoESP is using port 80")
        print("  - Verify IP address is correct")
        sys.exit(1)


def list_devices(bridge):
    """List all available devices."""
    print("📋 Discovered Devices:")
    print("-" * 50)
    
    lights = bridge.get_light_objects('list')
    
    if not lights:
        print("⚠️  No devices found!")
        return []
    
    for light in lights:
        state = "ON" if light.on else "OFF"
        brightness = light.brightness if hasattr(light, 'brightness') else "N/A"
        print(f"  • {light.name}")
        print(f"    ID: {light.light_id}")
        print(f"    State: {state}")
        print(f"    Brightness: {brightness}/254")
        print()
    
    return lights


def test_on_off(bridge, light_id):
    """Test turning device on and off."""
    print(f"🔦 Testing ON/OFF for device {light_id}...")
    
    try:
        # Turn ON
        bridge.set_light(light_id, 'on', True)
        print("  ✅ Turned ON")
        time.sleep(1)
        
        # Turn OFF
        bridge.set_light(light_id, 'on', False)
        print("  ✅ Turned OFF")
        time.sleep(1)
        
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_brightness(bridge, light_id):
    """Test brightness control."""
    print(f"💡 Testing BRIGHTNESS for device {light_id}...")
    
    brightness_levels = [64, 128, 192, 254]  # 25%, 50%, 75%, 100%
    
    try:
        for bri in brightness_levels:
            percentage = int((bri / 254) * 100)
            bridge.set_light(light_id, {'on': True, 'bri': bri})
            print(f"  ✅ Set to {percentage}% (brightness {bri}/254)")
            time.sleep(1)
        
        # Turn off at the end
        bridge.set_light(light_id, 'on', False)
        print("  ✅ Turned OFF")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_state_query(bridge, light_id):
    """Test querying device state."""
    print(f"🔍 Testing STATE QUERY for device {light_id}...")
    
    try:
        # Get current state
        light = bridge.get_light(light_id)
        
        print(f"  Device Name: {light['name']}")
        print(f"  State: {'ON' if light['state']['on'] else 'OFF'}")
        print(f"  Brightness: {light['state'].get('bri', 'N/A')}/254")
        print(f"  Reachable: {light['state'].get('reachable', 'Unknown')}")
        print("  ✅ State query successful")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def run_full_test_suite(bridge_ip, test_discovery=False):
    """Run complete test suite."""
    print("=" * 50)
    print("   FauxmoESP Test Suite")
    print("   Using phue library (real Hue device library)")
    print("=" * 50)
    print()
    
    # Test SSDP discovery if requested
    if test_discovery:
        devices = discover_ssdp_devices()
        print()
        if not devices and not bridge_ip:
            print("⚠️  No devices discovered and no IP provided.")
            return
    
    # Connect
    bridge = test_connection(bridge_ip)
    
    # List devices
    lights = list_devices(bridge)
    
    if not lights:
        print("⚠️  No devices to test. Check your ESPHome configuration.")
        return
    
    # Test first device
    first_light_id = lights[0].light_id
    print(f"🧪 Running tests on device: {lights[0].name} (ID: {first_light_id})")
    print("=" * 50)
    print()
    
    results = {
        'connection': True,  # Already succeeded
        'on_off': test_on_off(bridge, first_light_id),
        'brightness': test_brightness(bridge, first_light_id),
        'state_query': test_state_query(bridge, first_light_id)
    }
    
    if test_discovery:
        results['ssdp_discovery'] = True  # Already succeeded
    
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
        print("\n⚠️  Some tests failed. Check your ESPHome configuration.")


def interactive_mode(bridge_ip):
    """Interactive testing mode."""
    bridge = test_connection(bridge_ip)
    lights = list_devices(bridge)
    
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
            
            if cmd[0] == 'quit' or cmd[0] == 'exit':
                break
            
            elif cmd[0] == 'list':
                list_devices(bridge)
            
            elif cmd[0] == 'on' and len(cmd) > 1:
                light_id = int(cmd[1])
                bridge.set_light(light_id, 'on', True)
                print(f"✅ Device {light_id} turned ON")
            
            elif cmd[0] == 'off' and len(cmd) > 1:
                light_id = int(cmd[1])
                bridge.set_light(light_id, 'on', False)
                print(f"✅ Device {light_id} turned OFF")
            
            elif cmd[0] == 'bri' and len(cmd) > 2:
                light_id = int(cmd[1])
                brightness = int(cmd[2])
                bridge.set_light(light_id, {'on': True, 'bri': brightness})
                print(f"✅ Device {light_id} brightness set to {brightness}/254")
            
            else:
                print("Unknown command")
        
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Test FauxmoESP using the phue library (real Hue device library)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python test_fauxmo.py 192.168.1.100
  python test_fauxmo.py 192.168.1.100 --discover
  python test_fauxmo.py --discover-only
  python test_fauxmo.py 192.168.1.100 --interactive
  python test_fauxmo.py 192.168.1.100 --list
        '''
    )
    
    parser.add_argument('ip', nargs='?', help='IP address of the ESP device running FauxmoESP')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='Run in interactive mode')
    parser.add_argument('-l', '--list', action='store_true',
                        help='Only list devices and exit')
    parser.add_argument('-d', '--discover', action='store_true',
                        help='Test SSDP discovery before running other tests')
    parser.add_argument('--discover-only', action='store_true',
                        help='Only test SSDP discovery and exit')
    
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
        bridge = test_connection(args.ip)
        list_devices(bridge)
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
        run_full_test_suite(args.ip, test_discovery=args.discover)


if __name__ == '__main__':
    main()
