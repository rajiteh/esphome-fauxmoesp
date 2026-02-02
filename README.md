# ESPHome FauxmoESP Component

Integrate Amazon Alexa with ESPHome devices using Philips Hue emulation via the [FauxmoESP](https://github.com/vintlabs/fauxmoESP) library.

## Features

- ✅ Native ESPHome component integration
- ✅ Multiple virtual devices per ESP
- ✅ Alexa voice control ("Alexa, turn on kitchen light")
- ✅ Brightness control support
- ✅ Automatic device discovery
- ✅ Bi-directional state sync
- ✅ ESP32 support (ESP8266 may work but is untested)

## Installation

### 1. Add to your ESPHome configuration:

```yaml
external_components:
  - source: github://rajiteh/esphome-fauxmoesp
    components: [ fauxmoesp ]
```

### 2. Configure the component:

```yaml
fauxmoesp:
  port: 80  # Required for Gen3 Alexa devices
  devices:
    - name: "Living Room Light"
      on_state:
        - if:
            condition:
              lambda: "return state;"
            then:
              - light.turn_on: my_light
            else:
              - light.turn_off: my_light
```

### 3. Flash to your device:

```bash
esphome run your-config.yaml
```

### 4. Discover in Alexa:

Say: **"Alexa, discover devices"** or use the Alexa app.

## Configuration Variables

### Component Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| **id** | ID | *auto* | Unique ID for the component (required for bi-directional sync) |
| **port** | int | `80` | TCP port for the server. **Must be 80 for Gen3 Alexa devices** |
| **enabled** | boolean | `true` | Enable/disable the component |
| **create_server** | boolean | `true` | Create internal web server |
| **devices** | list | *required* | List of virtual Alexa devices |

### Device Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| **name** | string | *required* | Device name as it appears in Alexa |
| **id** | ID | *auto* | Unique ID for the device |
| **on_state** | [Automation](https://esphome.io/guides/automations.html) | *optional* | Actions when Alexa changes state |

### on_state Trigger Variables

| Variable | Type | Description |
|----------|------|-------------|
| `device_id` | uint8 | Numeric device ID (0-based index) |
| `device_name` | string | Name of the device |
| `state` | bool | ON/OFF state (`true` = ON, `false` = OFF) |
| `value` | uint8 | Brightness value (0-255). "Set light to 50%" = 128 |

## Usage Examples

### Basic Light Control

```yaml
fauxmoesp:
  devices:
    - name: "Bedroom Light"
      on_state:
        - logger.log:
            format: "Alexa: %s turned %s"
            args: ['device_name.c_str()', 'state ? "ON" : "OFF"']
        - if:
            condition:
              lambda: "return state;"
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
            brightness: !lambda "return value / 255.0;"
```

### Multiple Devices

```yaml
fauxmoesp:
  devices:
    - name: "Light 1"
      on_state:
        - if:
            condition:
              lambda: "return state;"
            then:
              - switch.turn_on: relay1
            else:
              - switch.turn_off: relay1
    
    - name: "Light 2"
      on_state:
        - if:
            condition:
              lambda: "return state;"
            then:
              - switch.turn_on: relay2
            else:
              - switch.turn_off: relay2
```

### Bi-directional Sync

To report state changes back to Alexa when controlled locally, give the component an `id` and call `set_device_state()`:

```yaml
fauxmoesp:
  id: fauxmo
  devices:
    - name: "Smart Light"
      on_state:
        - if:
            condition:
              lambda: "return state;"
            then:
              - light.turn_on: smart_light
            else:
              - light.turn_off: smart_light

light:
  - platform: monochromatic
    name: "Smart Light"
    id: smart_light
    output: light_output
    on_turn_on:
      - lambda: 'id(fauxmo).set_device_state("Smart Light", true);'
    on_turn_off:
      - lambda: 'id(fauxmo).set_device_state("Smart Light", false);'
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
| ESP32-S2 | ✅ Supported |
| ESP32-C3 | ✅ Supported |
| ESP8266 | ⚠️ Untested (library support exists) |
| RP2040 | ❌ Not supported |

## Technical Details

- Uses **AsyncTCP** (ESP32) / **ESPAsyncTCP** (ESP8266)
- Emulates Philips Hue Bridge API v2
- UDP discovery on `239.255.255.250:1900` (SSDP)
- HTTP server on configurable port (default 80)
- Patched FauxmoESP library bundled in `components/fauxmoesp/` for ESPHome compatibility

## Development

This component includes a patched version of the upstream [FauxmoESP](https://github.com/vintlabs/fauxmoESP) library. The patches add `setIP()` and `setMac()` methods to allow ESPHome to explicitly set network parameters instead of relying on Arduino WiFi globals.

### Repository Structure

```
components/fauxmoesp/
├── __init__.py              # ESPHome component definition
├── fauxmoesp_component.cpp  # ESPHome wrapper implementation
├── fauxmoesp_component.h    # ESPHome wrapper header
├── fauxmoESP.cpp            # Patched upstream library
├── fauxmoESP.h              # Patched upstream library
└── templates.h              # Upstream library templates
```

### Syncing with Upstream

The Makefile provides targets to manage the patched library:

```bash
# Fetch upstream FauxmoESP and apply patches
make apply-patch

# After making changes to fauxmoESP/, generate a new patch file
make generate-patch
```

The patch is based on commit `1b8b91e362bc4c2f0891f1160c69f1e399346c02` of the upstream library.

### Enabling Debug Logging

To enable verbose FauxmoESP library logging, add these build flags to your YAML:

```yaml
esphome:
  platformio_options:
    build_flags:
      - "-DDEBUG_FAUXMO_VERBOSE_TCP=1"
      - "-DDEBUG_FAUXMO_VERBOSE_UDP=1"
```

## Credits

Built on top of:
- [FauxmoESP](https://github.com/vintlabs/fauxmoESP) by Paul Vint & Xose Pérez
- [ESPHome](https://esphome.io/) by Otto Winter

## License

MIT License - See LICENSE file