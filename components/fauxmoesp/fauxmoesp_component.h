#pragma once

#include "esphome/core/component.h"
#include "esphome/core/automation.h"
#include "esphome/core/log.h"

#include <FauxmoESP.h>

#include <vector>
#include <string>
#include <functional>

namespace esphome {
namespace fauxmoesp {

/**
 * Simple device configuration - just a name and callback.
 */
struct DeviceConfig {
  std::string name;
  std::function<void(bool)> on_state_callback;
};

/**
 * Trigger for automation when device state changes from Alexa.
 * Parameters: device_name, state (on/off)
 */
class FauxmoStateTrigger : public Trigger<std::string, bool> {
 public:
  void set_device_name(const std::string &name) { device_name_ = name; }
  std::string get_device_name() const { return device_name_; }
  
 protected:
  std::string device_name_;
};

/**
 * Main component that manages the FauxmoESP library.
 * Simplified to only support on/off control.
 */
class FauxmoESPComponent : public Component {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::AFTER_CONNECTION; }

  void add_device(const std::string &name, FauxmoStateTrigger *trigger);
  void set_port(uint16_t port) { port_ = port; }
  void set_enabled(bool enabled) { enabled_ = enabled; }
  
  // Set device state programmatically (for syncing back to Alexa)
  void set_device_state(const std::string &name, bool state);

 protected:
  void initialize_fauxmo_();
  void on_state_change_(Light *light, LightStateChange *change);
  void on_get_state_(Light *light);

  FauxmoESP fauxmo_{true};
  std::vector<std::pair<std::string, FauxmoStateTrigger *>> devices_;
  uint16_t port_{80};
  bool enabled_{true};
  bool is_initialized_{false};
};

}  // namespace fauxmoesp
}  // namespace esphome