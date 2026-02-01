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

// ── WLED sync ────────────────────────────────────────────────────────────────

TEST_F(XenopixelLightTest, WLED_IgnoresShortPacket) {
  std::vector<uint8_t> pkt = {0x00, 0x00, 0xFF, 0xFF, 0x00};  // only 5 bytes
  light_.apply_wled_packet(pkt);
  EXPECT_TRUE(g_ble_writes().empty());
}

TEST_F(XenopixelLightTest, WLED_IgnoresNonNotifierProtocol) {
  std::vector<uint8_t> pkt = {0x01, 0x00, 0xFF, 0xFF, 0x00, 0x00};
  light_.apply_wled_packet(pkt);
  EXPECT_TRUE(g_ble_writes().empty());
}

TEST_F(XenopixelLightTest, WLED_SendsColorAndBrightness) {
  // brightness=200, R=255, G=0, B=128
  std::vector<uint8_t> pkt = {0x00, 0x00, 200, 255, 0, 128};
  light_.apply_wled_packet(pkt);

  ASSERT_GE(g_ble_writes().size(), 3u);
  EXPECT_EQ(g_ble_writes()[0].data, "[2,{\"PowerOn\":true}]");
  // 200*100/255 = 78
  EXPECT_EQ(g_ble_writes()[1].data, "[2,{\"Brightness\":78}]");
  EXPECT_EQ(g_ble_writes()[2].data, "[2,{\"BackgroundColor\":[255,0,128]}]");
}

TEST_F(XenopixelLightTest, WLED_BrightnessZeroTurnsOff) {
  // First turn on so off is a change
  std::vector<uint8_t> pkt_on = {0x00, 0x00, 128, 255, 0, 0};
  light_.apply_wled_packet(pkt_on);
  g_ble_writes().clear();

  std::vector<uint8_t> pkt_off = {0x00, 0x00, 0, 0, 0, 0};
  light_.apply_wled_packet(pkt_off);

  ASSERT_FALSE(g_ble_writes().empty());
  EXPECT_EQ(g_ble_writes()[0].data, "[2,{\"PowerOn\":false}]");
  // No brightness or color commands after power off
  for (size_t i = 1; i < g_ble_writes().size(); ++i) {
    EXPECT_EQ(g_ble_writes()[i].data.find("Brightness"), std::string::npos);
    EXPECT_EQ(g_ble_writes()[i].data.find("BackgroundColor"), std::string::npos);
  }
}

TEST_F(XenopixelLightTest, WLED_WorksWhileSyncing) {
  // syncing_from_notification should NOT block WLED packets
  // (only authorization matters for WLED)
  syncing_.value() = true;
  std::vector<uint8_t> pkt = {0x00, 0x00, 200, 255, 0, 0};
  light_.apply_wled_packet(pkt);
  ASSERT_GE(g_ble_writes().size(), 3u);
  EXPECT_EQ(g_ble_writes()[0].data, "[2,{\"PowerOn\":true}]");
  EXPECT_EQ(g_ble_writes()[1].data, "[2,{\"Brightness\":78}]");
  EXPECT_EQ(g_ble_writes()[2].data, "[2,{\"BackgroundColor\":[255,0,0]}]");
}

TEST_F(XenopixelLightTest, WLED_SkipsWhenNotAuthorized) {
  authorized_.value() = false;
  std::vector<uint8_t> pkt = {0x00, 0x00, 200, 255, 0, 0};
  light_.apply_wled_packet(pkt);
  EXPECT_TRUE(g_ble_writes().empty());
}

TEST_F(XenopixelLightTest, WLED_BlocksWriteState) {
  light_.set_wled_active(true);
  state_.current_values.set_state(true);
  light_.write_state(&state_);
  EXPECT_TRUE(g_ble_writes().empty());
}

TEST_F(XenopixelLightTest, WLED_BrightnessMapping) {
  // Test boundary values: 1 → 0, 128 → 50, 255 → 100
  std::vector<uint8_t> pkt = {0x00, 0x00, 1, 255, 255, 255};
  light_.apply_wled_packet(pkt);
  bool found = false;
  for (const auto &w : g_ble_writes()) {
    if (w.data.find("Brightness") != std::string::npos) {
      EXPECT_EQ(w.data, "[2,{\"Brightness\":0}]");  // 1*100/255 = 0
      found = true;
    }
  }
  EXPECT_TRUE(found);

  g_ble_writes().clear();
  mock_millis_value() = 1200;  // advance past color debounce
  pkt[2] = 128;
  light_.apply_wled_packet(pkt);
  for (const auto &w : g_ble_writes()) {
    if (w.data.find("Brightness") != std::string::npos) {
      EXPECT_EQ(w.data, "[2,{\"Brightness\":50}]");  // 128*100/255 = 50
    }
  }

  g_ble_writes().clear();
  mock_millis_value() = 1400;  // advance past color debounce
  pkt[2] = 255;
  light_.apply_wled_packet(pkt);
  for (const auto &w : g_ble_writes()) {
    if (w.data.find("Brightness") != std::string::npos) {
      EXPECT_EQ(w.data, "[2,{\"Brightness\":100}]");  // 255*100/255 = 100
    }
  }
}

TEST_F(XenopixelLightTest, WLED_SkipsWhenAuthorizedNull) {
  light_.set_authorized_global(nullptr);
  std::vector<uint8_t> pkt = {0x00, 0x00, 200, 255, 0, 0};
  light_.apply_wled_packet(pkt);
  EXPECT_TRUE(g_ble_writes().empty());
}

TEST_F(XenopixelLightTest, WLED_IgnoresEmptyPacket) {
  std::vector<uint8_t> pkt = {};
  light_.apply_wled_packet(pkt);
  EXPECT_TRUE(g_ble_writes().empty());
}

TEST_F(XenopixelLightTest, WLED_SkipsRedundantValues) {
  // First packet: power on, brightness 78, color [255,0,0]
  std::vector<uint8_t> pkt = {0x00, 0x00, 200, 255, 0, 0};
  light_.apply_wled_packet(pkt);
  ASSERT_EQ(g_ble_writes().size(), 3u);
  g_ble_writes().clear();

  // Same packet again — power, brightness, and color are all unchanged
  mock_millis_value() = 1200;  // advance past color debounce
  light_.apply_wled_packet(pkt);
  EXPECT_TRUE(g_ble_writes().empty());
}

TEST_F(XenopixelLightTest, WLED_SharesStateWithWriteState) {
  // write_state turns saber on — WLED should not re-send PowerOn
  state_.current_values.set_state(true);
  state_.current_values.set_brightness(1.0f);
  state_.current_values.set_rgb(1.0f, 0.0f, 0.0f);
  light_.write_state(&state_);
  g_ble_writes().clear();

  // WLED packet with same power state (on) — no PowerOn command expected
  mock_millis_value() = 1200;  // advance past color debounce
  std::vector<uint8_t> pkt = {0x00, 0x00, 200, 0, 255, 0};
  light_.apply_wled_packet(pkt);

  for (const auto &w : g_ble_writes()) {
    EXPECT_EQ(w.data.find("PowerOn"), std::string::npos)
        << "Unexpected PowerOn in: " << w.data;
  }
  // But brightness and color should change
  EXPECT_GE(g_ble_writes().size(), 2u);
}

TEST_F(XenopixelLightTest, WLED_WriteStateWorksAfterDisable) {
  // Enable WLED — write_state should be blocked
  light_.set_wled_active(true);
  state_.current_values.set_state(true);
  light_.write_state(&state_);
  EXPECT_TRUE(g_ble_writes().empty());

  // Disable WLED — write_state should work again
  light_.set_wled_active(false);
  light_.write_state(&state_);
  EXPECT_FALSE(g_ble_writes().empty());
}
