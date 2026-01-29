#pragma once

#include "esphome/core/component.h"
#include "esphome/core/automation.h"
#include "esphome/core/log.h"

// Include fauxmoESP first, then override its debug macros
#include <fauxmoESP.h>

// Redirect FauxmoESP debug output to ESPHome's logging system
// Enable verbose logging by adding these build_flags in your YAML:
//   platformio_options:
//     build_flags:
//       - "-DDEBUG_FAUXMO_VERBOSE_TCP=1"
//       - "-DDEBUG_FAUXMO_VERBOSE_UDP=1"

#define DEBUG_FAUXMO_TAG "fauxmo_lib"

// Undefine the library's macros and replace with ESPHome logging
#undef DEBUG_MSG_FAUXMO
#define DEBUG_MSG_FAUXMO(fmt, ...) ESP_LOGD(DEBUG_FAUXMO_TAG, fmt, ##__VA_ARGS__)

#include <vector>
#include <functional>

namespace esphome {
namespace fauxmoesp {

class FauxmoDevice {
 public:
  void set_name(const std::string &name) { name_ = name; }
  std::string get_name() const { return name_; }
  uint8_t get_id() const { return id_; }
  void set_id(uint8_t id) { id_ = id; }
  
  void add_on_state_callback(std::function<void(uint8_t, const char *, bool, uint8_t)> callback) {
    callbacks_.push_back(callback);
  }
  
  void trigger_callbacks(uint8_t device_id, const char *device_name, bool state, uint8_t value) {
    for (auto &callback : callbacks_) {
      callback(device_id, device_name, state, value);
    }
  }

 protected:
  std::string name_;
  uint8_t id_{0};
  std::vector<std::function<void(uint8_t, const char *, bool, uint8_t)>> callbacks_;
};

class FauxmoStateTrigger : public Trigger<uint8_t, std::string, bool, uint8_t> {
 public:
  explicit FauxmoStateTrigger(FauxmoDevice *parent) {
    parent->add_on_state_callback([this](uint8_t device_id, const char *device_name, bool state, uint8_t value) {
      this->trigger(device_id, std::string(device_name), state, value);
    });
  }
};

class FauxmoESPComponent : public Component {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::AFTER_CONNECTION; }

  void add_device(FauxmoDevice *device);
  void set_port(uint16_t port) { port_ = port; }
  void set_enabled(bool enabled) { enabled_ = enabled; }
  void set_create_server(bool create_server) { create_server_ = create_server; }
  
  // Method to set device state programmatically
  bool set_device_state(uint8_t id, bool state, uint8_t value);
  bool set_device_state(const char *name, bool state, uint8_t value);

 protected:
  ::fauxmoESP fauxmo_;
  std::vector<FauxmoDevice *> devices_;
  uint16_t port_{80};
  bool enabled_{true};
  bool create_server_{true};
  bool setup_complete_{false};   // True once setup() has finished
  bool is_initialized_{false};   // True once WiFi is ready and fauxmo is enabled
};

}  // namespace fauxmoesp
}  // namespace esphome