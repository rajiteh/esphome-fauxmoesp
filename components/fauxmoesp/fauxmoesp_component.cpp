#include "fauxmoesp_component.h"
#include "esphome/core/log.h"
#include "esphome/core/application.h"
#include "esphome/core/helpers.h"
#include "esphome/components/network/util.h"
#include <IPAddress.h>

namespace esphome {
namespace fauxmoesp {

static const char *const TAG = "fauxmoesp";

void FauxmoESPComponent::setup() {
  ESP_LOGCONFIG(TAG, "Setting up FauxmoESP (will initialize when WiFi is ready)...");
  
  // Configure FauxmoESP but DON'T enable yet
  this->fauxmo_.createServer(this->create_server_);
  this->fauxmo_.setPort(this->port_);
  // Don't call enable() here - we'll do it in loop() when WiFi is ready

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

  ESP_LOGCONFIG(TAG, "FauxmoESP setup complete (waiting for WiFi)!");
}

void FauxmoESPComponent::loop() {
  // Check if we need to initialize (waiting for WiFi to connect)
  if (!this->is_initialized_) {
    // Use ESPHome's network API instead of Arduino's WiFi class
    if (!network::is_connected()) {
      return;  // Wait for WiFi
    }
    
    // Get IP from ESPHome's network API
    auto ips = network::get_ip_addresses();
    if (ips.empty() || !ips[0].is_set()) {
      return;  // Wait for valid IP
    }
    
    // Get MAC address from ESPHome
    uint8_t mac[6];
    get_mac_address_raw(mac);
    char mac_str[18];
    snprintf(mac_str, sizeof(mac_str), "%02X:%02X:%02X:%02X:%02X:%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    
    ESP_LOGI(TAG, "Network connected! IP: %s, MAC: %s", ips[0].str().c_str(), mac_str);
    
    // Convert ESPHome IP to Arduino IPAddress
    // Parse the IP string since direct conversion isn't available
    IPAddress ip_addr;
    ip_addr.fromString(ips[0].str().c_str());
    
    // Set IP and MAC on fauxmo (patched library method)
    this->fauxmo_.setIP(ip_addr);
    this->fauxmo_.setMAC(mac_str);
    
    ESP_LOGI(TAG, "Enabling FauxmoESP server...");
    this->fauxmo_.enable(this->enabled_);
    this->is_initialized_ = true;
    
    ESP_LOGI(TAG, "FauxmoESP is now active and listening for Alexa discovery");
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
  ESP_LOGCONFIG(TAG, "  Initialized: %s", YESNO(this->is_initialized_));
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
  if (!this->is_initialized_) {
    ESP_LOGW(TAG, "Cannot set state - FauxmoESP not initialized yet");
    return false;
  }
  return this->fauxmo_.setState(id, state, value);
}

bool FauxmoESPComponent::set_device_state(const char *name, bool state, uint8_t value) {
  if (!this->is_initialized_) {
    ESP_LOGW(TAG, "Cannot set state - FauxmoESP not initialized yet");
    return false;
  }
  return this->fauxmo_.setState(name, state, value);
}

}  // namespace fauxmoesp
}  // namespace esphome