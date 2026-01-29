#include "fauxmoesp_component.h"
#include "esphome/core/log.h"
#include "esphome/core/application.h"
#include "esphome/components/network/util.h"
#include <WiFi.h>

namespace esphome {
namespace fauxmoesp {

static const char *const TAG = "fauxmoesp";

void FauxmoESPComponent::setup() {
  ESP_LOGCONFIG(TAG, "Setting up FauxmoESP...");
  
  // Debug: Check what WiFi is returning
  IPAddress ip = WiFi.localIP();
  String mac = WiFi.macAddress();
  ESP_LOGW(TAG, "DEBUG: Arduino WiFi.localIP() = %s", ip.toString().c_str());
  ESP_LOGW(TAG, "DEBUG: Arduino WiFi.macAddress() = %s", mac.c_str());
  
  // Also check ESPHome's network info
  auto ips = network::get_ip_addresses();
  if (!ips.empty()) {
    ESP_LOGW(TAG, "DEBUG: ESPHome network IP = %s", ips[0].str().c_str());
  }

  // Configure FauxmoESP
  this->fauxmo_.createServer(this->create_server_);
  this->fauxmo_.setPort(this->port_);
  this->fauxmo_.enable(this->enabled_);

  // Add all configured devices
  for (auto *device : this->devices_) {
    uint8_t id = this->fauxmo_.addDevice(device->get_name().c_str());
    device->set_id(id);
    ESP_LOGCONFIG(TAG, "  Added device: '%s' (ID: %d)", device->get_name().c_str(), id);
  }

  // Set up state change callback
  this->fauxmo_.onSetState([this](unsigned char device_id, const char *device_name, bool state,
                                   unsigned char value) {
    ESP_LOGD(TAG, "State change: Device #%d (%s) -> %s (value: %d)", 
             device_id, device_name, state ? "ON" : "OFF", value);

    // Find the device and trigger its callbacks
    if (device_id < this->devices_.size()) {
      this->devices_[device_id]->trigger_callbacks(device_id, device_name, state, value);
    }
  });

  // Enable FauxmoESP
  this->is_setup_ = true;

  ESP_LOGCONFIG(TAG, "FauxmoESP setup complete!");
}

void FauxmoESPComponent::loop() {
  if (!this->is_setup_) {
    return;
  }
  
  // Handle FauxmoESP events (UDP discovery, TCP requests)
  this->fauxmo_.handle();
}

void FauxmoESPComponent::dump_config() {
  ESP_LOGCONFIG(TAG, "FauxmoESP:");
  ESP_LOGCONFIG(TAG, "  Port: %d", this->port_);
  ESP_LOGCONFIG(TAG, "  Enabled: %s", YESNO(this->enabled_));
  ESP_LOGCONFIG(TAG, "  Create Server: %s", YESNO(this->create_server_));
  ESP_LOGCONFIG(TAG, "  Devices (%d):", this->devices_.size());
  for (auto *device : this->devices_) {
    ESP_LOGCONFIG(TAG, "    - '%s' (ID: %d)", device->get_name().c_str(), device->get_id());
  }
  
  if (this->port_ != 80) {
    ESP_LOGW(TAG, "  WARNING: Gen3 Alexa devices require port 80!");
  }
}

void FauxmoESPComponent::add_device(FauxmoDevice *device) {
  this->devices_.push_back(device);
}

bool FauxmoESPComponent::set_device_state(uint8_t id, bool state, uint8_t value) {
  if (!this->is_setup_) {
    ESP_LOGW(TAG, "Cannot set state - component not setup yet");
    return false;
  }
  return this->fauxmo_.setState(id, state, value);
}

bool FauxmoESPComponent::set_device_state(const char *name, bool state, uint8_t value) {
  if (!this->is_setup_) {
    ESP_LOGW(TAG, "Cannot set state - component not setup yet");
    return false;
  }
  return this->fauxmo_.setState(name, state, value);
}

}  // namespace fauxmoesp
}  // namespace esphome