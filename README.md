# ESPHome FauxmoESP Component

Reference: https://github.com/creepystefan/esphomefauxmo/blob/main/components/myalexa/__init__.py

Integrate Amazon Alexa with ESPHome devices using Philips Hue emulation via the FauxmoESP library.

## Features

- ✅ Native ESPHome component integration
- ✅ Multiple virtual devices per ESP
- ✅ Alexa voice control ("Alexa, turn on kitchen light")
- ✅ Brightness control support
- ✅ Automatic device discovery
- ✅ Bi-directional state sync
- ✅ ESP8266 and ESP32 support

## Installation

### 1. Add to your ESPHome configuration:

```yaml
external_components:
  - source: github://yourusername/esphome-fauxmoesp
    components: [ fauxmoesp ]
```

### 2. Configure the component:

```yaml
fauxmoesp:
  port: 80  # Required for Gen3 Alexa devices
  devices:
    - name: "Living Room Light"
      on_state:
        - light.toggle: my_light
```

### 3. Flash to your device:

```bash
esphome run your-config.yaml
```

### 4. Discover in Alexa:

Say: **"Alexa, discover devices"** or use the Alexa app.

## Configuration Variables

### Component Configuration

- **port** (*Optional*, int): TCP port for the server. Defaults to `80`. **Must be 80 for Gen3 devices**.
- **enabled** (*Optional*, boolean): Enable/disable the component. Defaults to `true`.
- **create_server** (*Optional*, boolean): Create internal web server. Defaults to `true`.
- **devices** (*Required*, list): List of virtual Alexa devices.

### Device Configuration

- **name** (*Required*, string): Device name as it appears in Alexa.
- **id** (*Optional*, ID): Unique ID for the device (auto-generated if not specified).
- **on_state** (*Optional*, [Automation](https://esphome.io/guides/automations.html)): Actions to perform when Alexa changes the device state.

### on_state Trigger Variables

- `device_id` (uint8): Numeric device ID (0-based index).
- `device_name` (string): Name of the device.
- `state` (bool): ON/OFF state (`true` = ON, `false` = OFF).
- `value` (uint8): Brightness value (0-255). When you say "Set light to 50%", this is 128.

## Usage Examples

### Basic Light Control

```yaml
fauxmoesp:
  devices:
    - name: "Bedroom Light"
      on_state:
        - if:
            condition:
              lambda: 'return state;'
            then:
              - light.turn_on: bedroom_light
            else:
              - light.turn_off: bedroom_light
```

### Brightness Control

```yaml
fauxmoesp:
  devices:
    - name: "Dimmable Light"
      on_state:
        - light.turn_on:
            id: my_light
            brightness: !lambda 'return value / 255.0;'
```

### Multiple Devices

```yaml
fauxmoesp:
  devices:
    - name: "Light 1"
      on_state:
        - switch.toggle: relay1
    
    - name: "Light 2"
      on_state:
        - switch.toggle: relay2
    
    - name: "Fan"
      on_state:
        - switch.toggle: fan_relay
```

### Bi-directional Sync

To report state changes back to Alexa when controlled locally:

```yaml
light:
  - platform: binary
    name: "Smart Light"
    id: smart_light
    output: relay
    on_turn_on:
      - lambda: 'id(fauxmo).set_device_state("Smart Light", true, 255);'
    on_turn_off:
      - lambda: 'id(fauxmo).set_device_state("Smart Light", false, 0);'

fauxmoesp:
  id: fauxmo
  devices:
    - name: "Smart Light"
      on_state:
        - light.toggle: smart_light
```

## Alexa Voice Commands

Once devices are discovered, you can use:

- "Alexa, turn on [device name]"
- "Alexa, turn off [device name]"
- "Alexa, set [device name] to 50 percent"
- "Alexa, dim [device name]"
- "Alexa, brighten [device name]"

## Troubleshooting

### Devices not discovered

1. **Ensure port 80 is used** for Gen3 Alexa devices:
   ```yaml
   fauxmoesp:
     port: 80
   ```

2. **Check ESP and Alexa are on same network** (not guest network).

3. **Disable ESPHome web_server on port 80**:
   ```yaml
   # Remove or change port:
   web_server:
     port: 8080  # Use different port
   ```

4. **Use static IP** for reliability:
   ```yaml
   wifi:
     manual_ip:
       static_ip: 192.168.1.100
       gateway: 192.168.1.1
       subnet: 255.255.255.0
   ```

### Port 80 conflicts

If you need the web server, run FauxmoESP with external server mode (advanced):

```yaml
fauxmoesp:
  create_server: false
  port: 80
```

Then integrate with ESPHome's async web server manually.

## Platform Support

| Platform | Status |
|----------|--------|
| ESP32 | ✅ Fully supported |
| ESP8266 | ✅ Fully supported |
| ESP32-S2 | ✅ Supported |
| ESP32-C3 | ✅ Supported |
| RP2040 | ⚠️ Untested |

## Technical Details

- Uses **AsyncTCP** (ESP32) / **ESPAsyncTCP** (ESP8266)
- Emulates Philips Hue Bridge API v2
- UDP discovery on `239.255.255.250:1900` (SSDP)
- HTTP server on configurable port (default 80)

## Credits

Built on top of:
- [FauxmoESP](https://github.com/vintlabs/fauxmoESP) by Paul Vint & Xose Pérez
- [ESPHome](https://esphome.io/) by Otto Winter

## License

MIT License - See LICENSE file