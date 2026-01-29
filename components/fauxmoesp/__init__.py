"""FauxmoESP Component for ESPHome - Alexa integration via Philips Hue emulation"""

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import automation
from esphome.const import (
    CONF_ID,
    CONF_NAME,
    CONF_PORT,
    CONF_ON_STATE,
)
from esphome.core import CORE, coroutine_with_priority

DEPENDENCIES = ["wifi"]
AUTO_LOAD = []
CODEOWNERS = ["@rajiteh"]

fauxmoesp_ns = cg.esphome_ns.namespace("fauxmoesp")
FauxmoESPComponent = fauxmoesp_ns.class_("FauxmoESPComponent", cg.Component)
FauxmoDevice = fauxmoesp_ns.class_("FauxmoDevice")

# Triggers
FauxmoStateTrigger = fauxmoesp_ns.class_(
    "FauxmoStateTrigger",
    automation.Trigger.template(cg.uint8, cg.std_string, cg.bool_, cg.uint8),
)

CONF_DEVICES = "devices"
CONF_ENABLED = "enabled"
CONF_CREATE_SERVER = "create_server"

DEVICE_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(FauxmoDevice),
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
        cv.Optional(CONF_CREATE_SERVER, default=True): cv.boolean,
    }
).extend(cv.COMPONENT_SCHEMA)


@coroutine_with_priority(50.0)
async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    # AsyncTCP is required by FauxmoESP but not auto-resolved from git repo
    if CORE.is_esp32:
        cg.add_library("esphome/AsyncTCP-esphome", "2.1.4")
    elif CORE.is_esp8266:
        cg.add_library("esphome/ESPAsyncTCP-esphome", "2.0.0")

    # Use patched FauxmoESP library with setIP/setMAC methods for ESPHome compatibility
    cg.add_library(
        "FauxmoESP", None, "https://github.com/rajiteh/fauxmoESP.git#esphome-patches"
    )

    # Configure component
    cg.add(var.set_port(config[CONF_PORT]))
    cg.add(var.set_enabled(config[CONF_ENABLED]))
    cg.add(var.set_create_server(config[CONF_CREATE_SERVER]))

    # Add devices
    for device_config in config[CONF_DEVICES]:
        device = cg.new_Pvariable(device_config[CONF_ID])
        cg.add(device.set_name(device_config[CONF_NAME]))
        cg.add(var.add_device(device))

        # Register state change triggers
        for conf in device_config.get(CONF_ON_STATE, []):
            trigger = cg.new_Pvariable(conf[CONF_ID], device)
            await automation.build_automation(
                trigger,
                [
                    (cg.uint8, "device_id"),
                    (cg.std_string, "device_name"),
                    (cg.bool_, "state"),
                    (cg.uint8, "value"),
                ],
                conf,
            )
