/*
 * WiFi compatibility layer for ESPHome
 *
 * Provides Arduino-style WiFi.localIP() and WiFi.macAddress()
 * using ESPHome's native APIs, since ESPHome no longer exposes
 * Arduino WiFi headers on ESP32 (as of ESPHome 2026.2+).
 */

#pragma once

#include <IPAddress.h>

#include "esphome/components/network/ip_address.h"
#include "esphome/components/wifi/wifi_component.h"
#include "esphome/core/helpers.h"

namespace fauxmoesp_compat {

// WiFi compatibility shim for ESP32 under ESPHome
class WiFiCompat {
   public:
    IPAddress localIP() {
        auto* wifi = esphome::wifi::global_wifi_component;
        if (wifi != nullptr) {
            auto addresses = wifi->get_ip_addresses();
            if (!addresses.empty()) {
                auto addr = addresses[0];
                char buf[esphome::network::IP_ADDRESS_BUFFER_SIZE];
                addr.str_to(buf);
                IPAddress result;
                result.fromString(buf);
                return result;
            }
        }
        return IPAddress(0, 0, 0, 0);
    }

    String macAddress() {
        std::string mac = esphome::get_mac_address_pretty();
        return String(mac.c_str());
    }
};

}  // namespace fauxmoesp_compat

// Create a global WiFi object that mimics Arduino's WiFi
static fauxmoesp_compat::WiFiCompat WiFi;
