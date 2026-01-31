#pragma once

#include "esphome/core/component.h"
#include "esphome/components/ble_client/ble_client.h"
#include "esphome/components/globals/globals_component.h"
#include "esphome/components/light/light_output.h"

// Custom light output for Xenopixel sabers.
// Sends separate BLE commands for power, color, and brightness
// instead of the combined values that ESPHome's built-in RGB light uses.

namespace esphome {
namespace xenopixel_light {

class XenopixelLight : public Component, public light::LightOutput {
 public:
  void set_ble_client(ble_client::BLEClient *client) { ble_client_ = client; }
  void set_authorized_global(globals::GlobalsComponent<bool> *g) {
    authorized_global_ = g;
  }
  void set_syncing_global(globals::GlobalsComponent<bool> *g) {
    syncing_global_ = g;
  }

  light::LightTraits get_traits() override {
    auto traits = light::LightTraits();
    traits.set_supported_color_modes({light::ColorMode::RGB});
    return traits;
  }

  void write_state(light::LightState *state) override {
    if (!is_ready_for_commands_()) return;

    bool is_on = state->current_values.is_on();
    float brightness = state->current_values.get_brightness();
    float r, g, b;
    state->current_values.as_rgb(&r, &g, &b);
    recover_rgb_(&r, &g, &b, brightness, is_on);

    send_power_if_changed_(is_on);
    if (!is_on) return;

    send_brightness_if_changed_((int)(brightness * 100.0f));
    send_color_if_changed_((int)(r * 255.0f), (int)(g * 255.0f),
                           (int)(b * 255.0f));
  }

  void reset_handle() { char_handle_ = 0; }

 protected:
  bool is_ready_for_commands_() {
    if (syncing_global_ != nullptr && syncing_global_->value()) return false;
    if (authorized_global_ == nullptr || !authorized_global_->value())
      return false;
    return true;
  }

  // as_rgb() bakes brightness in; recover raw color by dividing it out
  static void recover_rgb_(float *r, float *g, float *b, float brightness,
                           bool is_on) {
    if (brightness > 0.0f && is_on) {
      *r /= brightness;
      *g /= brightness;
      *b /= brightness;
      clamp_float_(r);
      clamp_float_(g);
      clamp_float_(b);
    }
  }

  static void clamp_float_(float *v) {
    if (*v > 1.0f) *v = 1.0f;
  }

  void send_power_if_changed_(bool is_on) {
    if (is_on != last_on_) {
      send_command_(is_on ? "[2,{\"PowerOn\":true}]"
                          : "[2,{\"PowerOn\":false}]");
      last_on_ = is_on;
    }
  }

  void send_brightness_if_changed_(int br_val) {
    if (br_val != last_brightness_) {
      char cmd[48];
      int len = snprintf(cmd, sizeof(cmd), "[2,{\"Brightness\":%d}]", br_val);
      send_command_(cmd, len);
      last_brightness_ = br_val;
    }
  }

  void send_color_if_changed_(int r, int g, int b) {
    if (r == last_r_ && g == last_g_ && b == last_b_) return;
    uint32_t now = millis();
    if (now - last_color_send_ms_ < 100) return;
    char cmd[64];
    int len = snprintf(cmd, sizeof(cmd),
                       "[2,{\"BackgroundColor\":[%d,%d,%d]}]", r, g, b);
    send_command_(cmd, len);
    last_r_ = r;
    last_g_ = g;
    last_b_ = b;
    last_color_send_ms_ = now;
  }

  void send_command_(const char *cmd) {
    send_command_(cmd, static_cast<int>(strlen(cmd)));
  }

  void send_command_(const char *cmd, int len) {
    if (ble_client_ == nullptr) return;

    // Cache the characteristic handle for performance
    if (char_handle_ == 0) {
      auto chr = ble_client_->get_characteristic(
          esp32_ble_tracker::ESPBTUUID::from_raw(
              "00003ab0-0000-1000-8000-00805f9b34fb"),
          esp32_ble_tracker::ESPBTUUID::from_raw(
              "00003ab1-0000-1000-8000-00805f9b34fb"));
      if (chr == nullptr) {
        ESP_LOGW("xenopixel", "BLE characteristic not found");
        return;
      }
      char_handle_ = chr->handle;
    }

    ESP_LOGI("xenopixel", "Light cmd: %s", cmd);
    auto status = esp_ble_gattc_write_char(
        ble_client_->get_gattc_if(), ble_client_->get_conn_id(), char_handle_,
        len, (uint8_t *)cmd, ESP_GATT_WRITE_TYPE_NO_RSP,
        ESP_GATT_AUTH_REQ_NONE);
    if (status != ESP_OK) {
      ESP_LOGW("xenopixel", "BLE write failed: %d", status);
    }
  }

  ble_client::BLEClient *ble_client_{nullptr};
  globals::GlobalsComponent<bool> *authorized_global_{nullptr};
  globals::GlobalsComponent<bool> *syncing_global_{nullptr};
  uint16_t char_handle_{0};
  bool last_on_{false};
  int last_r_{-1};
  int last_g_{-1};
  int last_b_{-1};
  int last_brightness_{-1};
  uint32_t last_color_send_ms_{0};
};

}  // namespace xenopixel_light
}  // namespace esphome
