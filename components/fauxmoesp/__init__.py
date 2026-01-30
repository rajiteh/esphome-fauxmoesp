"""FauxmoESP Component for ESPHome - Alexa integration via Philips Hue emulation

Simplified component supporting on/off control only.
"""

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import automation
from esphome.const import (
    CONF_ID,
    CONF_NAME,
    CONF_PORT,
    CONF_ON_STATE,
)
from esphome.core import coroutine_with_priority, CORE

AUTO_LOAD = ["network"]
CODEOWNERS = ["@rajiteh"]

fauxmoesp_ns = cg.esphome_ns.namespace("fauxmoesp")
FauxmoESPComponent = fauxmoesp_ns.class_("FauxmoESPComponent", cg.Component)

# Trigger with device_name (string) and state (bool)
FauxmoStateTrigger = fauxmoesp_ns.class_(
    "FauxmoStateTrigger",
    automation.Trigger.template(cg.std_string, cg.bool_),
)

CONF_DEVICES = "devices"
CONF_ENABLED = "enabled"

DEVICE_SCHEMA = cv.Schema(
    {
        cv.Required(CONF_NAME): cv.string,
        cv.Optional(CONF_ON_STATE): automation.validate_automation(
            {
                cv.GenerateID(CONF_ID): cv.declare_id(FauxmoStateTrigger),
            }
        ),
    }
)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(FauxmoESPComponent),
        cv.Optional(CONF_DEVICES, default=[]): cv.ensure_list(DEVICE_SCHEMA),
        cv.Optional(CONF_PORT, default=80): cv.port,
        cv.Optional(CONF_ENABLED, default=True): cv.boolean,
    }
).extend(cv.COMPONENT_SCHEMA)


@coroutine_with_priority(50.0)
async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    CORE.add_platformio_option("lib_ignore", ["AsyncTCP-esphome"])

    cg.add_library(
        name="ESP32SSDP",
        repository="https://github.com/rajiteh/ESP32SSDP",
        version="2.x",
    )

    cg.add_library("ESP32Async/AsyncTCP", "3.4.10")
    cg.add_library("bblanchon/ArduinoJson", "^6.20.1")
    cg.add_library(
        name="FauxmoESP",
        repository="https://github.com/Subtixx/FauxmoESP",
        version="main",
    )

    cg.add(var.set_port(config[CONF_PORT]))
    cg.add(var.set_enabled(config[CONF_ENABLED]))

    # Add devices
    for device_config in config[CONF_DEVICES]:
        device_name = device_config[CONF_NAME]

        # Create trigger if on_state is defined
        trigger = None
        for conf in device_config.get(CONF_ON_STATE, []):
            trigger = cg.new_Pvariable(conf[CONF_ID])
            cg.add(trigger.set_device_name(device_name))
            await automation.build_automation(
                trigger,
                [
                    (cg.std_string, "device_name"),
                    (cg.bool_, "state"),
                ],
                conf,
            )

        cg.add(var.add_device(device_name, trigger))
