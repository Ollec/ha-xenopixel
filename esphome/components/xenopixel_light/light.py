import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components.globals import GlobalsComponent
from esphome.const import CONF_OUTPUT_ID

from esphome.components import ble_client, light

DEPENDENCIES = ["ble_client"]

xenopixel_light_ns = cg.esphome_ns.namespace("xenopixel_light")
XenopixelLightOutput = xenopixel_light_ns.class_(
    "XenopixelLight", light.LightOutput, cg.Component
)

CONF_BLE_CLIENT_ID = "ble_client_id"
CONF_AUTHORIZED_ID = "authorized_id"
CONF_SYNCING_ID = "syncing_id"

CONFIG_SCHEMA = light.RGB_LIGHT_SCHEMA.extend(
    {
        cv.GenerateID(CONF_OUTPUT_ID): cv.declare_id(XenopixelLightOutput),
        cv.Required(CONF_BLE_CLIENT_ID): cv.use_id(ble_client.BLEClient),
        cv.Required(CONF_AUTHORIZED_ID): cv.use_id(GlobalsComponent),
        cv.Required(CONF_SYNCING_ID): cv.use_id(GlobalsComponent),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_OUTPUT_ID])
    await cg.register_component(var, config)
    await light.register_light(var, config)

    ble = await cg.get_variable(config[CONF_BLE_CLIENT_ID])
    cg.add(var.set_ble_client(ble))

    auth = await cg.get_variable(config[CONF_AUTHORIZED_ID])
    cg.add(var.set_authorized_global(auth))

    sync = await cg.get_variable(config[CONF_SYNCING_ID])
    cg.add(var.set_syncing_global(sync))
