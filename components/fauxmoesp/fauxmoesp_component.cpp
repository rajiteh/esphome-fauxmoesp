#include "fauxmoesp_component.h"
#include "esphome/core/log.h"

namespace esphome {
namespace fauxmoesp {

static const char *const TAG = "fauxmoesp";

void FauxmoESPComponent::setup() {
  ESP_LOGD(TAG, "FauxmoESP setup called");
  
  
  ESP_LOGD(TAG, "Calling createServer(%s)...", this->create_server_ ? "true" : "false");
  this->fauxmo_.createServer(this->create_server_);
  ESP_LOGD(TAG, "createServer done");
  
  ESP_LOGD(TAG, "Calling setPort(%d)...", this->port_);
  this->fauxmo_.setPort(this->port_);
  ESP_LOGD(TAG, "setPort done");

  ESP_LOGD(TAG, "Adding %d configured devices...", this->devices_.size());
  // Add all configured devices
  for (auto *device : this->devices_) {
    ESP_LOGD(TAG, "  Adding device: '%s'...", device->get_name().c_str());
    uint8_t id = this->fauxmo_.addDevice(device->get_name().c_str());
    device->set_id(id);
    ESP_LOGD(TAG, "  Added device: '%s' (ID: %d)", device->get_name().c_str(), id);
  }

  ESP_LOGD(TAG, "Setting up state change callback...");
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
}

void FauxmoESPComponent::initialize_fauxmo_() {
  ESP_LOGD(TAG, "Initializing FauxmoESP...");
  if (this->is_initialized_) {
    return;
  }
  this->fauxmo_.enable(this->enabled_);

  this->is_initialized_ = true;
  ESP_LOGD(TAG, "FauxmoESP setup complete!");
}

void FauxmoESPComponent::loop() {
  
  if (!this->enabled_) {
    return;
  }

  if (!this->is_initialized_) {
    // Use ESP-IDF's esp_netif directly - supports WiFi STA, AP, and Ethernet
    esp_netif_ip_info_t ip_info = {0};
    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    if (netif == NULL) {
      netif = esp_netif_get_handle_from_ifkey("WIFI_AP_DEF");
    }
    if (netif == NULL) {
      netif = esp_netif_get_handle_from_ifkey("ETH_DEF");
    }
    if (netif == NULL) {
      ESP_LOGW(TAG, "Network interface not found, deferring FauxmoESP initialization");
      return;
    }
    esp_err_t err = esp_netif_get_ip_info(netif, &ip_info);
    if (err != ESP_OK || ip_info.ip.addr == 0) {
      return;
    }
    ESP_LOGI(TAG, "Network ready with IP: %u.%u.%u.%u",
             esp_ip4_addr_get_byte(&ip_info.ip, 0),
             esp_ip4_addr_get_byte(&ip_info.ip, 1),
             esp_ip4_addr_get_byte(&ip_info.ip, 2),
             esp_ip4_addr_get_byte(&ip_info.ip, 3));
    this->initialize_fauxmo_();
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