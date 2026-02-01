#pragma once
// Minimal mocks for ESPHome and ESP-IDF types used by xenopixel_light.h.
// No real BLE or ESP32 hardware needed.

#include <cstdint>
#include <cstring>
#include <set>
#include <string>
#include <vector>

// ── ESP-IDF types & constants ───────────────────────────────────────────────
using esp_err_t = int;
using esp_gatt_if_t = uint8_t;
using esp_gatt_write_type_t = int;
using esp_gatt_auth_req_t = int;

constexpr esp_err_t ESP_OK = 0;
constexpr int ESP_GATT_WRITE_TYPE_NO_RSP = 1;
constexpr int ESP_GATT_AUTH_REQ_NONE = 0;

// ── Logging macros (no-op) ──────────────────────────────────────────────────
#define ESP_LOGD(tag, fmt, ...)
#define ESP_LOGI(tag, fmt, ...)
#define ESP_LOGW(tag, fmt, ...)
#define ESP_LOGE(tag, fmt, ...)

// ── Controllable millis() ───────────────────────────────────────────────────
inline uint32_t &mock_millis_value() {
  static uint32_t val = 0;
  return val;
}
inline uint32_t millis() { return mock_millis_value(); }

// ── BLE write capture ───────────────────────────────────────────────────────
struct BLEWriteRecord {
  uint16_t handle;
  std::string data;
};

inline std::vector<BLEWriteRecord> &g_ble_writes() {
  static std::vector<BLEWriteRecord> writes;
  return writes;
}

inline esp_err_t esp_ble_gattc_write_char(esp_gatt_if_t, uint16_t conn_id,
                                           uint16_t handle, uint16_t len,
                                           uint8_t *data,
                                           esp_gatt_write_type_t,
                                           esp_gatt_auth_req_t) {
  g_ble_writes().push_back(
      {handle, std::string(reinterpret_cast<char *>(data), len)});
  return ESP_OK;
}

// ── ESPHome namespaces ──────────────────────────────────────────────────────
namespace esphome {

namespace setup_priority {
constexpr float AFTER_WIFI = -10.0f;
}

class Component {
 public:
  virtual ~Component() = default;
  virtual void setup() {}
  virtual void loop() {}
  virtual float get_setup_priority() const { return 0.0f; }
};

namespace esp32_ble_tracker {

class ESPBTUUID {
 public:
  static ESPBTUUID from_raw(const std::string &) { return {}; }
};

}  // namespace esp32_ble_tracker

namespace ble_client {

struct BLECharacteristic {
  uint16_t handle{0};
};

class BLEClient {
 public:
  void set_mock_characteristic(BLECharacteristic *chr) { mock_chr_ = chr; }
  void set_gattc_if(esp_gatt_if_t gattc_if) { gattc_if_ = gattc_if; }
  void set_conn_id(uint16_t conn_id) { conn_id_ = conn_id; }

  BLECharacteristic *get_characteristic(esp32_ble_tracker::ESPBTUUID,
                                         esp32_ble_tracker::ESPBTUUID) {
    return mock_chr_;
  }

  esp_gatt_if_t get_gattc_if() { return gattc_if_; }
  uint16_t get_conn_id() { return conn_id_; }

 private:
  BLECharacteristic *mock_chr_{nullptr};
  esp_gatt_if_t gattc_if_{0};
  uint16_t conn_id_{0};
};

}  // namespace ble_client

namespace globals {

template <typename T>
class GlobalsComponent {
 public:
  explicit GlobalsComponent(T initial = {}) : value_(initial) {}
  T &value() { return value_; }

 private:
  T value_;
};

}  // namespace globals

namespace light {

enum class ColorMode { RGB = 1 };

class LightTraits {
 public:
  void set_supported_color_modes(std::set<ColorMode> modes) {
    modes_ = modes;
  }
  const std::set<ColorMode> &get_supported_color_modes() const {
    return modes_;
  }

 private:
  std::set<ColorMode> modes_;
};

class LightColorValues {
 public:
  bool is_on() const { return is_on_; }
  float get_brightness() const { return brightness_; }

  // ESPHome's as_rgb bakes brightness into the values
  void as_rgb(float *r, float *g, float *b) const {
    *r = r_ * brightness_;
    *g = g_ * brightness_;
    *b = b_ * brightness_;
  }

  // Test helpers
  void set_state(bool on) { is_on_ = on; }
  void set_brightness(float v) { brightness_ = v; }
  void set_rgb(float r, float g, float b) {
    r_ = r;
    g_ = g;
    b_ = b;
  }

 private:
  bool is_on_{false};
  float brightness_{1.0f};
  float r_{1.0f}, g_{1.0f}, b_{1.0f};
};

class LightState {
 public:
  LightColorValues current_values;
};

class LightOutput {
 public:
  virtual ~LightOutput() = default;
  virtual LightTraits get_traits() = 0;
  virtual void write_state(LightState *state) = 0;
};

}  // namespace light
}  // namespace esphome

// ── Redirect real ESPHome includes to this mock ─────────────────────────────
// These guards prevent the real headers from being pulled in.
#define ESPHOME_CORE_COMPONENT_H_
#define ESPHOME_COMPONENTS_BLE_CLIENT_BLE_CLIENT_H_
#define ESPHOME_COMPONENTS_GLOBALS_GLOBALS_COMPONENT_H_
#define ESPHOME_COMPONENTS_LIGHT_LIGHT_OUTPUT_H_
