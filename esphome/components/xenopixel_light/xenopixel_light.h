#pragma once

#include "esphome/core/component.h"
#include "esphome/components/ble_client/ble_client.h"
#include "esphome/components/globals/globals_component.h"
#include "esphome/components/light/light_output.h"

#ifndef UNIT_TEST
#include <WiFiUdp.h>                                  // cppcheck-suppress missingInclude
#include "esphome/components/wifi/wifi_component.h"   // cppcheck-suppress missingInclude
#endif

// Custom light output for Xenopixel sabers.
// Sends separate BLE commands for power, color, and brightness
// instead of the combined values that ESPHome's built-in RGB light uses.
//
// WLED UDP sync: A single static UDP socket is shared across all instances.
// Each instance's loop() participates — the first to run each iteration reads
// packets, and every instance with wled_active_ applies the latest packet.
// A generation counter ensures each instance processes each packet exactly once.

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

  void loop() override {
#ifndef UNIT_TEST
    static WiFiUDP udp;
    static bool udp_started = false;
    static std::vector<uint8_t> latest_packet;
    static uint32_t packet_gen = 0;

    if (!ensure_udp_started_(udp, udp_started)) return;
    drain_udp_packets_(udp, latest_packet, packet_gen);

    if (wled_active_ && packet_gen != last_seen_gen_ &&
        latest_packet.size() >= 6) {
      apply_wled_packet(latest_packet);
      last_seen_gen_ = packet_gen;
    }
#endif
  }

  light::LightTraits get_traits() override {
    auto traits = light::LightTraits();
    traits.set_supported_color_modes({light::ColorMode::RGB});
    return traits;
  }

  void apply_wled_packet(const std::vector<uint8_t> &data) {
    if (data.size() < 6 || data[0] != 0) return;

    // Only check authorization, not syncing — WLED packets should not be
    // blocked by the syncing_from_notification flag (that's for HA feedback)
    if (authorized_global_ == nullptr || !authorized_global_->value()) return;

    uint8_t wled_bri = data[2];
    uint8_t r = data[3], g = data[4], b = data[5];

    bool power_on = (wled_bri > 0);
    send_power_if_changed_(power_on);
    if (!power_on) return;

    send_brightness_if_changed_((wled_bri * 100) / 255);
    send_color_if_changed_(r, g, b);
  }

  void set_wled_active(bool active) {
    wled_active_ = active;
    ESP_LOGI("xenopixel", "WLED sync %s", active ? "enabled" : "disabled");
  }

  bool is_wled_active() const { return wled_active_; }

  void write_state(light::LightState *state) override {
    if (!is_ready_for_commands_()) return;
    if (wled_active_) return;

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
#ifndef UNIT_TEST
  // Start the shared UDP listener once WiFi is connected.
  static bool ensure_udp_started_(WiFiUDP &udp, bool &started) {
    if (started) return true;
    if (wifi::global_wifi_component == nullptr ||
        !wifi::global_wifi_component->is_connected())
      return false;
    udp.begin(21324);
    started = true;
    ESP_LOGI("xenopixel", "WLED UDP listener started on port 21324");
    return true;
  }

  // Drain all queued UDP packets, keeping only the latest valid one.
  static void drain_udp_packets_(WiFiUDP &udp,
                                 std::vector<uint8_t> &latest_packet,
                                 uint32_t &packet_gen) {
    uint8_t buf[256];
    int latest_len = 0;
    int pkt_size;
    while ((pkt_size = udp.parsePacket()) > 0) {
      if (pkt_size >= 6 && pkt_size <= static_cast<int>(sizeof(buf)))
        latest_len = udp.read(buf, sizeof(buf));
      udp.clear();
    }
    if (latest_len > 0) {
      latest_packet.assign(buf, buf + latest_len);
      packet_gen++;
      ESP_LOGD("xenopixel",
               "WLED UDP packet: %d bytes, proto=%d bri=%d rgb=[%d,%d,%d]",
               latest_len, latest_packet[0], latest_packet[2],
               latest_packet[3], latest_packet[4], latest_packet[5]);
    }
  }
#endif

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
      static const char on_cmd[] = "[2,{\"PowerOn\":true}]";
      static const char off_cmd[] = "[2,{\"PowerOn\":false}]";
      if (is_on)
        send_command_(on_cmd, sizeof(on_cmd) - 1);
      else
        send_command_(off_cmd, sizeof(off_cmd) - 1);
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
  bool wled_active_{false};
  uint32_t last_seen_gen_{0};
};

}  // namespace xenopixel_light
}  // namespace esphome
