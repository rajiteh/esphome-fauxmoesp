#include "fauxmoesp_component.h"

#include "esphome/core/log.h"

namespace esphome {
namespace fauxmoesp {

static const char* const TAG = "fauxmoesp";

void FauxmoESPComponent::setup() {
    ESP_LOGD(TAG, "FauxmoESP setup called");

    this->fauxmo_.createServer(this->create_server_);
    this->fauxmo_.setPort(this->port_);

    ESP_LOGD(TAG, "Adding %d configured devices...", this->devices_.size());
    // Add all configured devices
    for (auto* device : this->devices_) {
        uint8_t id = this->fauxmo_.addDevice(device->get_name().c_str());
        device->set_id(id);
        ESP_LOGD(TAG, "  Added device: '%s' (ID: %d)",
                 device->get_name().c_str(), id);
    }

    // Set up state change callback
    this->fauxmo_.onSetState([this](unsigned char device_id,
                                    const char* device_name, bool state,
                                    unsigned char value) {
        ESP_LOGD(TAG, "State change: Device #%d (%s) -> %s (value: %d)",
                 device_id, device_name, state ? "ON" : "OFF", value);

        // Find the device and trigger its callbacks
        if (device_id < this->devices_.size()) {
            this->devices_[device_id]->trigger_callbacks(device_id, device_name,
                                                         state, value);
        }
    });
}

void FauxmoESPComponent::initialize_fauxmo_() {
    if (this->is_initialized_) {
        return;
    }

    IPAddress ip;
    if (!this->get_ip_(ip)) {
        ESP_LOGD(
            TAG,
            "IP address not assigned yet, deferring FauxmoESP initialization");
        return;
    }

    char mac_str[18];
    if (!this->get_mac_(mac_str, sizeof(mac_str))) {
        ESP_LOGD(
            TAG,
            "Failed to get MAC address, deferring FauxmoESP initialization");
        return;
    }

    ESP_LOGI(TAG, "Network ready with IP: %s", ip.toString().c_str());

    this->fauxmo_.setMac(mac_str);
    this->fauxmo_.setIP(ip);
    this->fauxmo_.enable(this->enabled_);

    this->is_initialized_ = true;
    ESP_LOGD(TAG, "FauxmoESP setup complete!");
}

void FauxmoESPComponent::loop() {
    if (!this->enabled_) {
        return;
    }

    if (!this->is_initialized_) {
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
    for (auto* device : this->devices_) {
        ESP_LOGCONFIG(TAG, "    - '%s' (ID: %d)", device->get_name().c_str(),
                      device->get_id());
    }

    if (this->port_ != 80) {
        ESP_LOGW(TAG, "  WARNING: Gen3 Alexa devices require port 80!");
    }
}

void FauxmoESPComponent::add_device(FauxmoDevice* device) {
    this->devices_.push_back(device);
}

bool FauxmoESPComponent::set_device_state(uint8_t id, bool state,
                                          uint8_t value) {
    if (!this->is_initialized_) {
        ESP_LOGW(TAG, "Cannot set state - FauxmoESP not initialized yet");
        return false;
    }
    return this->fauxmo_.setState(id, state, value);
}

bool FauxmoESPComponent::set_device_state(const char* name, bool state,
                                          uint8_t value) {
    if (!this->is_initialized_) {
        ESP_LOGW(TAG, "Cannot set state - FauxmoESP not initialized yet");
        return false;
    }
    return this->fauxmo_.setState(name, state, value);
}

esp_netif_t* FauxmoESPComponent::get_network_interface_() {
    // Use ESP-IDF's esp_netif directly - supports WiFi STA, AP, and Ethernet
    esp_netif_t* netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    if (netif == NULL) {
        netif = esp_netif_get_handle_from_ifkey("WIFI_AP_DEF");
    }
    if (netif == NULL) {
        netif = esp_netif_get_handle_from_ifkey("ETH_DEF");
    }
    return netif;
}

bool FauxmoESPComponent::get_ip_(IPAddress& ip) {
    esp_netif_t* netif = this->get_network_interface_();
    if (netif == NULL) {
        ESP_LOGW(TAG,
                 "Network interface not found, deferring FauxmoESP "
                 "initialization");
        return false;
    }

    esp_netif_ip_info_t ip_info = {0};
    esp_err_t err = esp_netif_get_ip_info(netif, &ip_info);
    if (err != ESP_OK || ip_info.ip.addr == 0) {
        return false;
    }

    ip = IPAddress(esp_ip4_addr_get_byte(&ip_info.ip, 0),
                   esp_ip4_addr_get_byte(&ip_info.ip, 1),
                   esp_ip4_addr_get_byte(&ip_info.ip, 2),
                   esp_ip4_addr_get_byte(&ip_info.ip, 3));
    return true;
}

bool FauxmoESPComponent::get_mac_(char* mac_str, size_t len) {
    esp_netif_t* netif = this->get_network_interface_();
    if (netif == NULL) {
        return false;
    }

    uint8_t mac[6];
    esp_err_t err = esp_netif_get_mac(netif, mac);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Failed to get MAC address from network interface");
        return false;
    }

    snprintf(mac_str, len, "%02X:%02X:%02X:%02X:%02X:%02X", mac[0], mac[1],
             mac[2], mac[3], mac[4], mac[5]);
    return true;
}

}  // namespace fauxmoesp
}  // namespace esphome