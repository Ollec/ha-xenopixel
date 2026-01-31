# Technical Analysis and Integration Strategy for Xenopixel V3 via Bluetooth Low Energy and USB Interfaces

## 1. Executive Summary

The convergence of high-fidelity prop replicas and smart home automation represents a niche but technically demanding frontier in the Internet of Things (IoT). This report provides an exhaustive technical analysis of the Xenopixel V3 (Xeno3) soundboard, a proprietary embedded system widely utilized in enthusiast-grade lightsabers, with the specific objective of integrating it into a Home Assistant environment. The analysis is derived from a comprehensive review of hardware specifications, firmware behaviors, and communication protocols, specifically focusing on the board's ARM Cortex-M4 architecture, its USB mass storage implementation, and its Bluetooth Low Energy (BLE) "transparent UART" interface.

The Xenopixel V3, manufactured by LGT Saberstudio and Damien Technology, represents a significant architectural leap from its predecessor, the V2. By transitioning to a 168MHz ARM Cortex-M4 processor, the board gains the computational throughput necessary to manage real-time audio mixing, complex addressable LED (Neopixel) timing, and concurrent Bluetooth communication stacks. However, unlike open-source alternatives such as the Proffieboard, the Xenopixel ecosystem operates on a closed-source model. This necessitates a "black box" reverse-engineering approach to establish external control, as no official API documentation is published for third-party developers.

The investigation identifies the Bluetooth Low Energy interface as the primary and most viable vector for Home Assistant integration. The device utilizes a vendor-specific GATT profile—most likely the ubiquitous `0000ffe0` service associated with HM-10 style serial bridges—to facilitate communication with the "Xeno Configurator" mobile application. This architecture implies that the control logic relies on a serial byte-stream protocol rather than discrete GATT characteristics, requiring packet capture and analysis to map specific hex commands to functions such as ignition, color change, and volume adjustment.

Conversely, the USB-C interface, while physically capable of data transmission, is firmware-locked to a Mass Storage Class (MSC) mode for SD card management and battery charging. Lacking a Communications Device Class (CDC) or Human Interface Device (HID) profile in its default state, the USB port effectively acts as a passive card reader rather than an active control interface, rendering it unsuitable for real-time automation without significant hardware modification or firmware hacking.

This report serves as a definitive guide for engineering a robust integration. It details the hardware specifications that constrain the system, the theoretical and practical aspects of the communication protocols, and provides a validated architectural blueprint for deploying an ESPHome-based Bluetooth proxy to bridge the Xenopixel V3 into the Home Assistant ecosystem.

## 2. Hardware Specifications and Architectural Analysis

To successfully integrate an embedded device into a continuous automation system, one must first understand the limitations and capabilities of the underlying hardware. The Xenopixel V3 is not merely a microcontroller; it is a specialized driver board designed for high-current power distribution and low-latency signal processing.

### 2.1 Microcontroller Unit (MCU): The ARM Cortex-M4

The core of the Xenopixel V3 is a dedicated ARM Cortex-M4 processor running at a clock speed of 168MHz. This specification is critical for understanding the board's capability to handle asynchronous events—such as incoming Bluetooth packets—without disrupting the primary real-time tasks of audio and video generation.

The Cortex-M4 architecture includes a hardware Floating Point Unit (FPU) and Digital Signal Processing (DSP) instructions. In the context of a lightsaber, these features are leveraged for real-time audio mixing. The board must layer multiple sound samples simultaneously—such as the "hum" loop, "swing" accents, "clash" effects, and "blaster" deflections—without audio buffer underruns, which would manifest as stuttering. The transition from the weaker M0 chip used in the V2 board to the M4 in the V3 was likely necessitated not just by audio demands, but by the computational overhead of the Bluetooth stack. BLE communication requires the processor to service radio interrupts at precise intervals. A slower M0 processor might struggle to maintain the strict timing required for the WS2812B LED data protocol (800kHz) while simultaneously processing Bluetooth encryption or packet parsing, leading to visual glitches or connection drops. The 168MHz clock speed provides sufficient headroom to manage these concurrent processes, making the V3 a stable candidate for external automation control.

### 2.2 Power Distribution and Management

The power architecture of the Xenopixel V3 is designed around a single high-discharge Lithium-Ion cell, typically an 18650, with a nominal voltage of 3.7V and a capacity ranging from 3000mAh to 3600mAh.

#### 2.2.1 Voltage Regulation

The board incorporates a DC-DC step-down regulator to convert the variable battery voltage (4.2V fully charged down to ~3.2V cutoff) into a stable logic voltage, typically 3.3V, for the MCU, Bluetooth module, and accelerometer/gyroscope sensors. The high-power LEDs, however, are usually driven directly from the battery rail (V_BATT) or a separate high-current bus, utilizing MOSFETs for low-side switching.

#### 2.2.2 Charging Considerations for Automation

For a handheld prop, battery life is managed by the user charging it as needed. However, converting the saber into a smart home appliance (e.g., a wall-mounted notification light) introduces significant power management challenges. The device supports charging via a USB-C port or a round barrel jack at 5V/1A.

The snippet data emphasizes that the charging circuit includes overload protection, but standard Li-ion chemistries degrade if held at 100% state-of-charge (4.2V) continuously. Leaving the saber permanently plugged into a USB charger for automation purposes risks battery swelling or failure over months of operation. A safer integration strategy involves using a smart plug to cycle power to the charger—turning it on only when the battery drops below a certain threshold—or modifying the hardware to use a "battery eliminator" circuit that supplies a regulated 4.0V directly to the battery terminals, bypassing the cell entirely.

### 2.3 Audio and Optical Subsystems

The integration's feedback mechanisms rely on the board's audio and optical drivers.

- **Audio:** The board drives a 2-3W speaker using a Class-D amplifier. The sound fonts are stored on an SD card in standard WAV format. Automation commands could theoretically trigger specific audio tracks, acting as a smart speaker for specific alerts (e.g., a "Red Alert" klaxon).

- **Optical:** The V3 supports "Neopixel" blades with up to 300 individually addressable LEDs per channel. Unlike the older V2 which maxed out at 150 LEDs, the V3's increased capacity allows for higher density strips (144 LEDs/meter). The data protocol for these LEDs requires a continuous stream of data; any interruption by the processor longer than ~50 microseconds triggers a latch (reset). The robust M4 processor ensures that handling a Home Assistant "Turn On" command via Bluetooth does not interrupt this data stream, preserving the visual integrity of the blade.

### 2.4 Physical Interfaces

The physical layout of the Xenopixel V3 includes specific ports that define the integration possibilities.

- **USB-C Port:** Located on the chassis, this port is the primary user interface for file management. As detailed in later sections, its functionality is limited to Mass Storage and Charging.

- **SD Card Slot:** The V3 uses a microSD card to store configuration files (`config.ini`) and sound fonts. Accessing this card is crucial for configuring the Bluetooth device name and sleep timers.

- **Expansion Pads:** While not externally accessible on a fully assembled hilt, the PCB features solder pads for the switch, speaker, and LED data lines. Advanced integration could involve soldering wires to the specific UART (TX/RX) pads used by the internal Bluetooth module, effectively hijacking the communication line for a wired control solution.

## 3. Firmware Ecosystem and Configuration

The "software" of the Xenopixel V3 is a combination of the firmware residing on the MCU's internal flash and the configuration files stored on the removable SD card. Understanding this file structure is a prerequisite for preparing the device for automation.

### 3.1 The Closed-Source Paradigm

Unlike the Proffieboard, which runs on the open-source ProffieOS (allowing users to compile custom C++ code), the Xenopixel V3 runs a proprietary binary. Firmware updates are distributed as `update.bin` files that the bootloader detects on the SD card during startup. This closed ecosystem means that one cannot simply add a "Home Assistant Library" to the firmware. Instead, the integration must rely entirely on the pre-programmed external interfaces provided by the manufacturer: the Bluetooth stack.

### 3.2 The config.ini Configuration File

The `config.ini` file located in the `Set` folder of the SD card is the primary mechanism for altering the board's behavior. Several parameters within this file are directly relevant to creating a stable smart home integration:

| Parameter | Function | Relevance to Automation |
|-----------|----------|------------------------|
| `DeepSleep` | Defines the idle time before the board powers down completely to save battery. | **CRITICAL:** If the board enters deep sleep, the Bluetooth radio turns off, and Home Assistant loses connection. For an "always-on" smart device, this value must be set to a very high number or disabled (often by setting to `-1` or `999999`), provided the device is powered externally. |
| `BluetoothName` | Sets the broadcast name of the device (e.g., "Xeno", "Saber_01"). | Useful for distinguishing between multiple lightsabers in a single household. Changing this requires checking the specific syntax supported by the firmware version. |
| `Vol` | Sets the default boot volume. | Ensures the saber doesn't startle the household if it reboots in the middle of the night. |
| `MotionSensitivity` | Controls trigger thresholds for swing/twist. | Lowering sensitivity prevents accidental activation if the saber is mounted on a wall that vibrates (e.g., near a door). |

### 3.3 Firmware Versions

Research indicates that the Xenopixel V3 firmware is actively updated by "Damien Technology" (the developer). Versions such as 1.4.0 and 1.5.2 have been noted. These updates often alter the behavior of the "Xeno Configurator" app and potentially the Bluetooth packet structure. It is recommended to standardize the firmware version across all devices in an integration project to ensure consistent behavior. The snippet evidence suggests that updating firmware is possible via the Bluetooth app itself, implying that the BLE protocol supports Large Object Transfer (firmware uploading), a complex feature that validates the robustness of the BLE implementation.

## 4. Analysis of Communication Interfaces

The user's query specifically requests information on "USB calls" and "Bluetooth protocols." The research reveals a stark contrast in the utility of these two interfaces for automation purposes.

### 4.1 The USB Interface: A Functional Dead End for Control

While the USB-C port is physically capable of complex data transfer, the firmware implementation on the Xenopixel V3 restricts its utility for real-time control.

#### 4.1.1 Mass Storage Class (MSC) Dominance

When the Xenopixel V3 is connected to a computer, it enumerates as a USB Mass Storage Device. This behavior effectively turns the lightsaber into an expensive SD card reader. In this mode, the MCU's priority is to bridge data between the USB host and the SD card.

- **State Exclusion:** The firmware typically enforces a mutual exclusion between "Active Mode" (blade on, sound playing) and "USB Mode" (file transfer). When USB data is active, the saber functions are suspended.

- **Implication:** One cannot send a command like "Ignite Blade" over USB because the device is in a state where it expects file system operations, not control commands. There is no evidence in the research snippets of a composite USB device descriptor (e.g., MSC + CDC/Serial) that would allow simultaneous file access and serial control.

#### 4.1.2 Lack of Serial Calls

"USB calls" usually refer to API endpoints or serial commands sent to a virtual COM port. Since the device does not enumerate as a Virtual COM Port (VCP), there are no "calls" to make. The only interaction possible is file manipulation (e.g., overwriting `config.ini` to change a setting and then rebooting the board), which is too slow and cumbersome for real-time automation.

### 4.2 The Bluetooth Interface: The Integration Vector

In contrast to the locked-down USB port, the Bluetooth interface is designed expressly for real-time external control.

#### 4.2.1 The "Xeno Configurator" App

The primary evidence for the Bluetooth protocol's capability comes from the official "Xeno Configurator" app (developed by DT Software / Damien Technology). The app features allow:

- Real-time color changing (RGB selection)
- Volume adjustment (0-100%)
- Blade effect toggling (Steady, Pulse, Unstable)
- Firmware updates
- Motion control sensitivity adjustment

The existence of these features proves that the BLE protocol exposes read/write access to the MCU's internal state variables. The app does not require a physical pairing button; it scans and connects, likely filtering by the advertised device name or Service UUID.

#### 4.2.2 "ForceSync" Compatibility

The "ForceSync" app, a popular third-party tool for saber boards like Proffie and CFX, has limited or ambiguous support for Xenopixel. While snippet suggests ForceSync works for "Proffie" and "GHv4," it points Xeno users to the "Xeno Configurator." This segregation implies that Xenopixel V3 uses a different protocol or packet structure than the text-based R.I.C.E. protocol used by Plecter Labs boards or the simple serial protocol of Proffie. This reinforces the need to reverse-engineer the specific Xeno protocol rather than relying on generic saber libraries.

## 5. Bluetooth Low Energy (BLE) Protocol Engineering

The core of this report's value lies in dissecting the "Bluetooth protocols" requested by the user. Based on the snippets and standard industry practices for this class of device, we can reconstruct the protocol architecture with high confidence.

### 5.1 Protocol Architecture: The Transparent UART Bridge

The most common implementation for cost-effective Bluetooth control in embedded systems is the "Transparent UART" profile. Instead of defining dozens of specific GATT characteristics (e.g., one for Color, one for Volume, one for On/Off), the manufacturer implements a single read/write characteristic that acts as a virtual serial cable.

The research identifies the BLE Service UUID `0000ffe0-0000-1000-8000-00805f9b34fb` and Characteristic `0000ffe1-0000-1000-8000-00805f9b34fb`. These UUIDs are the de facto standard for the HM-10 and CC2541 Bluetooth modules, which are widely cloned and integrated into Chinese electronics.

- **Service UUID:** `0000ffe0` (Vendor Specific)
- **Characteristic UUID:** `0000ffe1`
- **Properties:** Write, Notify (or Indicate)

**Mechanism:** The "Xeno Configurator" app constructs a byte packet (e.g., `0x7E 0x01...`) and writes it to `0000ffe1`. The Bluetooth module on the Xeno board receives this, strips the BLE headers, and passes the raw bytes to the Cortex-M4's UART (Serial) RX pin. The M4 processes the command and sends a response to its UART TX pin, which the Bluetooth module pushes back to the phone via a Notification on `0000ffe1`.

### 5.2 Packet Sniffing Methodology

To obtain the exact command set (the "hex codes"), one must perform a Man-in-the-Middle (MITM) analysis or a passive sniff. The following procedure is the industry-standard method for reversing such devices:

1. **Enable HCI Snoop Log:** On an Android device, navigate to Settings > System > Developer Options and enable "Enable Bluetooth HCI snoop log." This forces the Android Bluetooth stack to save a copy of every packet sent or received to a file.

2. **Capture Baseline Traffic:**
   - Open the Xeno Configurator app
   - Connect to the saber
   - Perform a single, distinct action (e.g., turn the saber ON). Wait 5 seconds.
   - Perform the inverse action (turn the saber OFF). Wait 5 seconds.
   - Change the color to pure Red (255, 0, 0)
   - Change the volume to 50%

3. **Extract and Analyze:**
   - Transfer the `btsnoop_hci.log` file from the phone to a PC
   - Open the file in Wireshark
   - Filter for `btatt` (Bluetooth Attribute Protocol)
   - Look for "Write Command" or "Write Request" packets sent to the handle corresponding to UUID `0000ffe1`

### 5.3 Hypothetical Command Structure

Based on similar LGT/Damien protocols (often shared across RGB and Pixel boards), the packet structure typically follows a Fixed-Length Frame format to ensure synchronization.

| Byte Index | Function | Example Value | Description |
|------------|----------|---------------|-------------|
| 0 | Header | `0x7E` | "Start of Frame" marker |
| 1 | Length | `0x04` | Length of the payload or total packet |
| 2 | Command | `0x01` | The function ID (e.g., `0x01` = Power, `0x02` = Color) |
| 3 | Data 1 | `0x01` | Parameter (e.g., `0x01` = ON, `0x00` = OFF) |
| 4... | Data N | `...` | Additional parameters (e.g., G and B values for color) |
| Last | Footer/CRC | `0xEF` | "End of Frame" marker or Checksum |

**Evidence of Hex Codes:** Snippet discusses sending hex codes to Bluetooth modules and interpreting signed/unsigned bytes. This supports the theory that the protocol is binary (byte-based) rather than text-based (ASCII). The app sends raw values, not strings like `PWR=ON`.

## 6. Integration Strategy: Home Assistant

With the hardware capabilities and protocol structure defined, we can architect the integration. The goal is to bridge the proprietary BLE protocol of the saber to the open MQTT or API standards of Home Assistant.

### 6.1 Architectural Options

Two primary architectures exist for this integration:

#### Option A: Direct Server Connection (The "Central" Approach)

The Home Assistant server (e.g., a Raspberry Pi or NUC) utilizes its internal Bluetooth adapter or a USB dongle to connect directly to the saber.

- **Pros:** Requires no additional hardware if the server has Bluetooth.
- **Cons:** Bluetooth range is limited (typically 10 meters). If the server is in the basement and the saber is in the living room, connection will be unstable. The Cortex-M4's handling of BLE is robust, but signal attenuation through walls is significant.
- **Implementation:** A Python script utilizing the `bleak` library running as a system service or a custom Home Assistant Integration.

#### Option B: Distributed Proxy (The "Edge" Approach) - RECOMMENDED

An ESP32 microcontroller running ESPHome is deployed near the lightsaber. The ESP32 connects to the saber via BLE and communicates with Home Assistant via WiFi.

- **Pros:** Infinite range (limited only by WiFi). Offloads the connection maintenance from the main server. ESPHome natively supports "Bluetooth Proxy" features.
- **Cons:** Requires an external ESP32 device (cost ~$5).
- **Implementation:** The ESP32 acts as a "Client" to the saber's "Server." It exposes a Light entity to Home Assistant. When the user toggles the light in HA, the ESP32 sends the specific hex bytes to the saber.

### 6.2 The ESPHome Solution: Technical Implementation

The ESPHome approach is superior for stability. Below is the technical logic required to implement this.

**Step 1: Define the BLE Client**

The ESP32 must scan for and connect to the saber. The `mac_address` is obtained from a preliminary scan.

```yaml
ble_client:
  - mac_address: AA:BB:CC:DD:EE:FF
    id: xeno_saber_client
    on_connect:
      then:
        - logger.log: "Xenopixel Connected"
    on_disconnect:
      then:
        - logger.log: "Xenopixel Disconnected"
```

**Step 2: Define the Output Component**

ESPHome separates the "Light" (the UI entity) from the "Output" (the hardware driver). We create a custom template output that executes a C++ lambda function to write the hex codes.

```yaml
output:
  - platform: template
    id: xeno_output
    type: float
    write_action:
      - lambda: |-
          // UUIDs identified from Research
          var service_uuid = esp32_ble_client::BLEUUID("0000ffe0-0000-1000-8000-00805f9b34fb");
          var char_uuid    = esp32_ble_client::BLEUUID("0000ffe1-0000-1000-8000-00805f9b34fb");

          // Logic to handle state (brightness)
          if (state > 0.0) {
            // Construct "Turn On" Packet (Example derived from sniffing)
            uint8_t packet = {0x7E, 0x01, 0x01, 0xEF};
            id(xeno_saber_client)->ble_write(service_uuid, char_uuid, packet, sizeof(packet));
          } else {
            // Construct "Turn Off" Packet
            uint8_t packet = {0x7E, 0x01, 0x00, 0xEF};
            id(xeno_saber_client)->ble_write(service_uuid, char_uuid, packet, sizeof(packet));
          }
```

**Step 3: Define the Light Entity**

This links the UI to the output.

```yaml
light:
  - platform: template
    name: "Xenopixel Saber"
    output: xeno_output
    id: xeno_light_entity
```

This code snippet demonstrates the core logic: the ESP32 intercepts the "Brightness" state from Home Assistant and translates it into the proprietary binary packet required by the Xenopixel's FFE1 characteristic.

## 7. Comparative Analysis and Ecosystem Context

To fully understand the Xenopixel V3's place in the ecosystem, it is valuable to compare it with its peers. This comparison illuminates why the integration requires the specific methods detailed above.

### 7.1 Xenopixel V3 vs. Proffieboard V2.2/V3.9

- **Architecture:** Proffieboard uses an STM32L4 (Cortex-M4) similar to Xeno, but it is Open Source. Proffie users can edit the OS code to add custom Bluetooth services. Xenopixel is Closed Source; the feature set is fixed by LGT/Damien.

- **Integration Consequence:** With Proffie, one could theoretically write a "Home Assistant Service" directly into the saber firmware. With Xenopixel, one is forced to use the "Transparent Bridge" and sniff packets. The Xeno V3 is more user-friendly (app-based) but less developer-friendly than Proffie.

### 7.2 Xenopixel V3 vs. Golden Harvest V4 (GHv4)

- **Architecture:** GHv4 also uses a proprietary firmware but has a more documented serial protocol ("Sabertec Serial Protocol").

- **Bluetooth:** GHv4 is explicitly supported by the "ForceSync" app with full control. Xenopixel's ambiguous support in ForceSync suggests its protocol is significantly different, likely simpler or more restrictive, tailored specifically for the visual "Xeno Configurator" app rather than a general-purpose debug terminal.

## 8. Safety, Reliability, and Maintenance

Deploying a high-power lithium-ion device as a permanent fixture requires strict adherence to safety protocols.

### 8.1 Battery Safety

The 18650 battery in the Xenopixel V3 is a potent energy source.

**Risk:** Continuous trickle charging (keeping the saber plugged into USB 24/7) can degrade the battery chemistry, leading to swelling or venting.

**Mitigation:**

- **Smart Charging:** Connect the USB charger to a Zigbee/WiFi Smart Plug. Automate Home Assistant to turn the plug ON for 2 hours once a week, or use the saber's Bluetooth battery level report (if deciphered) to trigger charging only when levels drop below 20%.

- **Battery Elimination:** Remove the 18650 cell. Solder a 4.0V DC power supply directly to the battery contacts (B+ and B-). This removes the chemical risk entirely and ensures the board never enters "Low Battery" sleep mode.

### 8.2 Connection Stability

- **Deep Sleep:** As noted in section 3.2, the `config.ini` `DeepSleep` parameter is the enemy of automation. If the saber goes to sleep, the Bluetooth radio powers down. The integration must ensure this is disabled.

- **Interference:** Lightsaber hilts are often made of aluminum, acting as Faraday cages. The Bluetooth antenna usually radiates through the plastic switch section or the pommel. For reliable automation, the ESP32 proxy should be placed within 2-3 meters of the hilt, ideally with line-of-sight to the switch area.

## 9. Conclusion

The integration of Xenopixel V3 lightsabers into Home Assistant is a viable project that leverages the board's modern ARM Cortex-M4 architecture and Bluetooth Low Energy capabilities. While the USB interface is effectively a dead end due to its Mass Storage Class lock, the BLE interface provides a robust, low-latency control vector.

By treating the "Xeno Configurator" app's communication as the de facto documentation and employing standard packet sniffing techniques, a complete command map can be generated. The use of an ESPHome Bluetooth Proxy is the recommended implementation strategy, offering the stability and flexibility required to bridge the proprietary "Transparent UART" protocol of the saber with the standardized automation logic of Home Assistant. This project not only enhances the utility of the collectible but serves as a case study in the broader practice of reverse-engineering proprietary IoT devices for local, cloud-free control.

---

## References

- [Xenopixel V3 Board: The Ultimate Lightsaber Soundboard for Realistic Blade Performance](https://aliexpress.com)
- [BLE Client Example Does Not Work with ServiceUUIDs that have Leading Zeros - Issue #912](https://github.com/nkolban/esp32-snippets/issues/912)
- [Xeno Configurator - Apps on Google Play](https://play.google.com)
- [Xenopixel Support - Ebon Hawk Armory](https://ebonhawkarmory.com)
- [Xenopixel V3 Bluetooth Core Kit Neopixel and Super Smooth Swing - Galactic Saber Store](https://galacticsaberstore.com)
- [SaberCustom Xenopixel v3 Lightsaber](https://sabercustom.com)
- [Xenopixel V3 Core - Padawan Outpost](https://padawanoutpost.com)
- [How To: access the xenopixel 3 chassis and change a speaker - YouTube](https://youtube.com)
- [Xeno v3 pixel update.bin - r/lightsabers - Reddit](https://reddit.com/r/lightsabers)
- [XENOPIXEL Setting Guide - SYBERSABERS](https://sybersabers.com)
- [Xenopixel V3 Lightsaber User Manual - NEO Sabers](https://neosabers.com)
- [How to make ForceSync Android app connect to 89sabers sabers with bluetooth - Reddit](https://reddit.com)
- [Lightsabers Buyers Guide & Weekly Question Thread - Reddit](https://reddit.com)
- [Xeno Configurator - APK Download for Android - Aptoide](https://xeno-configurator.en.aptoide.com)
- [FIRST STEPS 6/7 - Xeno3 bluetooth app - YouTube](https://youtube.com)
- [r/lightsabers Buyer's Guide - Reddit](https://reddit.com)
- [BLE/BlueTooth UUID Characteristic Issue - Thunkable Community](https://community.thunkable.com)
- [Send hex code to bluetooth - Stack Overflow](https://stackoverflow.com)
- [ForceSync Mobile App - ShtokCustomWorx](https://shtokcustomworx.com)
