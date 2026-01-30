#include "fauxmoesp_component.h"
#include "esphome/core/log.h"
#include "esphome/components/network/util.h"

#ifdef USE_ESP32
#include <WiFi.h>
#endif
#ifdef USE_ESP8266
#include <ESP8266WiFi.h>
#endif

namespace esphome {
namespace fauxmoesp {

static const char *const TAG = "fauxmoesp";

void FauxmoESPComponent::setup() {
  // Initialization deferred to loop when network is ready
}

void FauxmoESPComponent::initialize_fauxmo_() {
  if (this->is_initialized_) {
    return;
  }
  ESP_LOGI(TAG, "Initializing FauxmoESP on port %d", this->port_);
  
  this->fauxmo_.setWebServerPort(this->port_);
  this->fauxmo_.setWebServerEnabled(true);
  this->fauxmo_.setCheckUsername(false);
  
  // Add all devices
  for (auto &device : this->devices_) {
    ESP_LOGD(TAG, "Adding device: %s", device.first.c_str());
    
    LightState initial_state(false);
    initial_state.isLightReachable = true;
    
    Light *light = this->fauxmo_.addLight(String(device.first.c_str()), LightCapabilities(), initial_state);
    
    if (light != nullptr) {
      ESP_LOGD(TAG, "Device '%s' added with ID %d", device.first.c_str(), light->deviceId);
    } else {
      ESP_LOGE(TAG, "Failed to add device: %s", device.first.c_str());
    }
  }

  this->fauxmo_.setup(
    [this](Light *light, LightStateChange *change) { this->on_state_change_(light, change); },
    [this](Light *light) { this->on_get_state_(light); }
  );
  
  this->is_initialized_ = true;
  ESP_LOGI(TAG, "FauxmoESP initialized successfully");
}

void FauxmoESPComponent::loop() {
  
  if (!this->enabled_) {
    return;
  }

  if (!this->is_initialized_) {
    if (network::is_connected() && WiFi.localIP() != IPAddress(0, 0, 0, 0)) {
      this->initialize_fauxmo_();
    }
    return;
  }  
  
  this->fauxmo_.update();
}

void FauxmoESPComponent::on_state_change_(Light *light, LightStateChange *change) {
  if (light == nullptr || change == nullptr) {
    return;
  }
  
  // Only handle on/off changes
  if (change->isOnSet()) {
    bool new_state = change->getIsOn();
    light->state.isOn = new_state;
    change->setOnSuccess(true);
    
    ESP_LOGD(TAG, "'%s' turned %s", light->name.c_str(), new_state ? "ON" : "OFF");
    
    // Find and trigger the callback
    for (auto &device : this->devices_) {
      if (device.first == light->name.c_str()) {
        if (device.second != nullptr) {
          device.second->trigger(device.first, new_state);
        }
        break;
      }
    }
  }
}

void FauxmoESPComponent::on_get_state_(Light *light) {
  if (light == nullptr) {
    return;
  }
  light->state.isLightReachable = true;
}

void FauxmoESPComponent::dump_config() {
  ESP_LOGCONFIG(TAG, "FauxmoESP:");
  ESP_LOGCONFIG(TAG, "  Port: %d", this->port_);
  ESP_LOGCONFIG(TAG, "  Enabled: %s", YESNO(this->enabled_));
  ESP_LOGCONFIG(TAG, "  Initialized: %s", YESNO(this->is_initialized_));
  ESP_LOGCONFIG(TAG, "  Devices (%d):", this->devices_.size());
  for (auto &device : this->devices_) {
    ESP_LOGCONFIG(TAG, "    - %s", device.first.c_str());
  }
}

void FauxmoESPComponent::add_device(const std::string &name, FauxmoStateTrigger *trigger) {
  this->devices_.push_back({name, trigger});
}

void FauxmoESPComponent::set_device_state(const std::string &name, bool state) {
  if (!this->is_initialized_) {
    ESP_LOGW(TAG, "Cannot set state - not initialized");
    return;
  }
  
  Light *light = this->fauxmo_.getLightByName(String(name.c_str()));
  if (light != nullptr) {
    light->state.isOn = state;
    ESP_LOGD(TAG, "Set '%s' state to %s", name.c_str(), state ? "ON" : "OFF");
  }
}

}  // namespace fauxmoesp
}  // namespace esphome