// C++ unit tests for XenopixelLight (esphome/components/xenopixel_light/)
// Mock header MUST be included first to define all types before the real header.
#include "esphome_mock.h"

#include "xenopixel_light/xenopixel_light.h"

#include <gtest/gtest.h>

using namespace esphome;
using namespace esphome::xenopixel_light;

// ── Test fixture ────────────────────────────────────────────────────────────

class XenopixelLightTest : public ::testing::Test {
 protected:
  void SetUp() override {
    g_ble_writes().clear();
    mock_millis_value() = 1000;  // Start well past debounce window

    authorized_.value() = true;
    syncing_.value() = false;

    chr_.handle = 42;
    client_.set_mock_characteristic(&chr_);
    client_.set_gattc_if(1);
    client_.set_conn_id(2);

    light_.set_ble_client(&client_);
    light_.set_authorized_global(&authorized_);
    light_.set_syncing_global(&syncing_);

    // Default state: off, full brightness, white
    state_.current_values.set_state(false);
    state_.current_values.set_brightness(1.0f);
    state_.current_values.set_rgb(1.0f, 1.0f, 1.0f);
  }

  XenopixelLight light_;
  ble_client::BLEClient client_;
  ble_client::BLECharacteristic chr_;
  globals::GlobalsComponent<bool> authorized_{true};
  globals::GlobalsComponent<bool> syncing_{false};
  light::LightState state_;
};

// ── get_traits ──────────────────────────────────────────────────────────────

TEST_F(XenopixelLightTest, GetTraits_ReturnsRGB) {
  auto traits = light_.get_traits();
  auto modes = traits.get_supported_color_modes();
  ASSERT_EQ(modes.size(), 1u);
  EXPECT_EQ(*modes.begin(), light::ColorMode::RGB);
}

// ── Guard conditions ────────────────────────────────────────────────────────

TEST_F(XenopixelLightTest, WriteState_SkipsWhenSyncing) {
  syncing_.value() = true;
  state_.current_values.set_state(true);
  light_.write_state(&state_);
  EXPECT_TRUE(g_ble_writes().empty());
}

TEST_F(XenopixelLightTest, WriteState_SkipsWhenNotAuthorized) {
  authorized_.value() = false;
  state_.current_values.set_state(true);
  light_.write_state(&state_);
  EXPECT_TRUE(g_ble_writes().empty());
}

TEST_F(XenopixelLightTest, WriteState_SkipsWhenAuthorizedNull) {
  light_.set_authorized_global(nullptr);
  state_.current_values.set_state(true);
  light_.write_state(&state_);
  EXPECT_TRUE(g_ble_writes().empty());
}

// ── Power commands ──────────────────────────────────────────────────────────

TEST_F(XenopixelLightTest, WriteState_SendsPowerOn) {
  state_.current_values.set_state(true);
  light_.write_state(&state_);
  ASSERT_FALSE(g_ble_writes().empty());
  EXPECT_EQ(g_ble_writes()[0].data, "[2,{\"PowerOn\":true}]");
}

TEST_F(XenopixelLightTest, WriteState_SendsPowerOff) {
  // First turn on so that turning off is a change
  state_.current_values.set_state(true);
  light_.write_state(&state_);
  g_ble_writes().clear();

  state_.current_values.set_state(false);
  light_.write_state(&state_);
  ASSERT_FALSE(g_ble_writes().empty());
  EXPECT_EQ(g_ble_writes()[0].data, "[2,{\"PowerOn\":false}]");
}

TEST_F(XenopixelLightTest, WriteState_SkipsRedundantPower) {
  state_.current_values.set_state(true);
  light_.write_state(&state_);
  g_ble_writes().clear();

  // Same state again — no power command expected
  light_.write_state(&state_);
  // Brightness/color may still be sent on second call (first time cached),
  // but no PowerOn command should appear
  for (const auto &w : g_ble_writes()) {
    EXPECT_EQ(w.data.find("PowerOn"), std::string::npos)
        << "Unexpected PowerOn in: " << w.data;
  }
}

// ── Brightness ──────────────────────────────────────────────────────────────

TEST_F(XenopixelLightTest, WriteState_SendsBrightness) {
  state_.current_values.set_state(true);
  state_.current_values.set_brightness(0.75f);
  light_.write_state(&state_);

  bool found = false;
  for (const auto &w : g_ble_writes()) {
    if (w.data.find("Brightness") != std::string::npos) {
      EXPECT_EQ(w.data, "[2,{\"Brightness\":75}]");
      found = true;
    }
  }
  EXPECT_TRUE(found) << "No Brightness command found";
}

TEST_F(XenopixelLightTest, WriteState_SkipsRedundantBrightness) {
  state_.current_values.set_state(true);
  state_.current_values.set_brightness(0.50f);
  light_.write_state(&state_);
  g_ble_writes().clear();

  // Same brightness again
  mock_millis_value() = 2000;  // avoid color debounce
  light_.write_state(&state_);
  for (const auto &w : g_ble_writes()) {
    EXPECT_EQ(w.data.find("Brightness"), std::string::npos)
        << "Unexpected Brightness in: " << w.data;
  }
}

// ── Color ───────────────────────────────────────────────────────────────────

TEST_F(XenopixelLightTest, WriteState_SendsColor) {
  state_.current_values.set_state(true);
  state_.current_values.set_brightness(1.0f);
  state_.current_values.set_rgb(1.0f, 0.0f, 0.5f);
  light_.write_state(&state_);

  bool found = false;
  for (const auto &w : g_ble_writes()) {
    if (w.data.find("BackgroundColor") != std::string::npos) {
      // 0.5 * 255 = 127 (truncated)
      EXPECT_EQ(w.data, "[2,{\"BackgroundColor\":[255,0,127]}]");
      found = true;
    }
  }
  EXPECT_TRUE(found) << "No BackgroundColor command found";
}

TEST_F(XenopixelLightTest, WriteState_SkipsRedundantColor) {
  state_.current_values.set_state(true);
  state_.current_values.set_rgb(0.5f, 0.5f, 0.5f);
  light_.write_state(&state_);
  g_ble_writes().clear();

  // Same color, enough time passed to avoid debounce
  mock_millis_value() = 2000;
  light_.write_state(&state_);
  for (const auto &w : g_ble_writes()) {
    EXPECT_EQ(w.data.find("BackgroundColor"), std::string::npos)
        << "Unexpected BackgroundColor in: " << w.data;
  }
}

TEST_F(XenopixelLightTest, WriteState_DebouncesColor) {
  state_.current_values.set_state(true);
  state_.current_values.set_rgb(1.0f, 0.0f, 0.0f);
  light_.write_state(&state_);
  g_ble_writes().clear();

  // Change color but only 50ms later — should be suppressed
  state_.current_values.set_rgb(0.0f, 1.0f, 0.0f);
  mock_millis_value() = 1050;
  light_.write_state(&state_);
  for (const auto &w : g_ble_writes()) {
    EXPECT_EQ(w.data.find("BackgroundColor"), std::string::npos)
        << "Color should be debounced: " << w.data;
  }
}

// ── Off skips brightness/color ──────────────────────────────────────────────

TEST_F(XenopixelLightTest, WriteState_SkipsCommandsWhenOff) {
  state_.current_values.set_state(false);
  state_.current_values.set_brightness(0.5f);
  state_.current_values.set_rgb(1.0f, 0.0f, 0.0f);
  light_.write_state(&state_);

  for (const auto &w : g_ble_writes()) {
    EXPECT_EQ(w.data.find("Brightness"), std::string::npos);
    EXPECT_EQ(w.data.find("BackgroundColor"), std::string::npos);
  }
}

// ── RGB recovery from brightness ────────────────────────────────────────────

TEST_F(XenopixelLightTest, WriteState_RecoverRGBFromBrightness) {
  state_.current_values.set_state(true);
  state_.current_values.set_brightness(0.5f);
  state_.current_values.set_rgb(1.0f, 0.5f, 0.0f);
  // as_rgb will return (0.5, 0.25, 0.0) — dividing by 0.5 recovers (1.0, 0.5, 0.0)
  light_.write_state(&state_);

  bool found = false;
  for (const auto &w : g_ble_writes()) {
    if (w.data.find("BackgroundColor") != std::string::npos) {
      EXPECT_EQ(w.data, "[2,{\"BackgroundColor\":[255,127,0]}]");
      found = true;
    }
  }
  EXPECT_TRUE(found) << "No BackgroundColor command found";
}

TEST_F(XenopixelLightTest, WriteState_ClampsRGBOvershoot) {
  state_.current_values.set_state(true);
  state_.current_values.set_brightness(0.5f);
  // Set RGB > 1.0 to force overshoot after brightness division
  // as_rgb returns (r*br, g*br, b*br) = (0.6, 0.5, 0.5)
  // dividing by 0.5 gives (1.2, 1.0, 1.0) — 1.2 should clamp to 1.0
  state_.current_values.set_rgb(1.2f, 1.0f, 1.0f);
  light_.write_state(&state_);

  bool found = false;
  for (const auto &w : g_ble_writes()) {
    if (w.data.find("BackgroundColor") != std::string::npos) {
      EXPECT_EQ(w.data, "[2,{\"BackgroundColor\":[255,255,255]}]");
      found = true;
    }
  }
  EXPECT_TRUE(found) << "No BackgroundColor command found";
}

// ── reset_handle ────────────────────────────────────────────────────────────

TEST_F(XenopixelLightTest, ResetHandle_ClearsCache) {
  state_.current_values.set_state(true);
  light_.write_state(&state_);
  ASSERT_FALSE(g_ble_writes().empty());
  // Handle was cached; now reset it
  light_.reset_handle();
  g_ble_writes().clear();

  // Make the client return nullptr — simulates disconnected
  client_.set_mock_characteristic(nullptr);
  state_.current_values.set_state(false);
  light_.write_state(&state_);
  // Power change attempted, but characteristic lookup fails → no writes
  EXPECT_TRUE(g_ble_writes().empty());
}

// ── Null safety ─────────────────────────────────────────────────────────────

TEST_F(XenopixelLightTest, SendCommand_HandlesNullClient) {
  light_.set_ble_client(nullptr);
  state_.current_values.set_state(true);
  light_.write_state(&state_);
  // Should not crash; no writes
  EXPECT_TRUE(g_ble_writes().empty());
}

TEST_F(XenopixelLightTest, SendCommand_HandlesNullCharacteristic) {
  client_.set_mock_characteristic(nullptr);
  state_.current_values.set_state(true);
  light_.write_state(&state_);
  // Characteristic lookup fails → no writes
  EXPECT_TRUE(g_ble_writes().empty());
}
