#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>
#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <Crypto.h>
#include <SHA256.h>
#include <HKDF.h>
#include <AES.h>
#include <GCM.h>
#include <math.h>
#include <time.h>
#include <esp_system.h>

// --- Hardware configuration ---
static const uint8_t LED_PIN = 14;            // WS2812B data pin
static const uint8_t LED_COUNT = 5;           // One LED per family location
static const uint8_t BUTTON_OK_PIN = 34;      // "I'm OK" button
static const uint8_t BUTTON_SOS_PIN = 35;     // "SOS" button
static const uint8_t BUTTON_ADMIN_PIN = 39;   // Concealed admin reset button

// TTGO T-Beam LoRa pins
static const uint8_t LORA_SS = 18;
static const uint8_t LORA_RST = 23;
static const uint8_t LORA_DIO0 = 26;

// --- Mesh configuration ---
static uint32_t g_nodeId = 0x4E435C01;               // Default to Newcastle HQ; override via provisioning
static const long FREQUENCY = 915E6;                 // Use 433E6 in regions where required
static const uint8_t DEFAULT_HOP_LIMIT = 5;
static const uint32_t HB_INTERVAL_MIN = 15;          // Auto heartbeat every 15 minutes
static const uint32_t HEARTBEAT_TIMEOUT_MS = 24UL * 60UL * 60UL * 1000UL;  // 24 hours
static const uint32_t SOS_HOLD_MS = 2000;            // Require 2 second hold for SOS
static const uint32_t ADMIN_HOLD_MS = 3000;          // Require 3 second hold for admin reset

// --- Crypto material (loaded from NVS during provisioning) ---
static uint8_t g_familyKey[32];
static uint8_t g_nodeKey[32];
static uint8_t g_sessionKey[32];
static bool g_sessionReady = false;
static uint32_t g_sessionCounter = 1;
static const char PROVISION_ACK[] = "OK\n";
static const char PROVISION_ERR[] = "ER\n";

Preferences g_prefs;
Adafruit_NeoPixel g_strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

struct NodeMapping {
    uint32_t nodeId;
    uint8_t ledIndex;
};

static const NodeMapping NODE_MAP[] = {
    {0x4E435C01, 0}, // Newcastle HQ
    {0x504C4156, 1}, // Placerville
    {0x43495448, 2}, // Citrus Heights
    {0x524F5356, 3}, // Roseville
    {0x414E5445, 4}  // Antelope
};

struct NodeStatus {
    bool seen = false;
    bool sosActive = false;
    uint32_t lastHeartbeatMs = 0;
    uint32_t lastCounter = 0;
};

static NodeStatus g_status[LED_COUNT];

// Button state
static bool g_okDown = false;
static bool g_sosDown = false;
static bool g_adminDown = false;
static uint32_t g_okPressStart = 0;
static uint32_t g_sosPressStart = 0;
static uint32_t g_adminPressStart = 0;
static bool g_localSosLatched = false;

static uint32_t g_lastHeartbeatSentMs = 0;
static uint32_t g_nextLedUpdateMs = 0;

// --- Utility helpers ---
static uint8_t findIndexForNode(uint32_t nodeId) {
    for (const auto &entry : NODE_MAP) {
        if (entry.nodeId == nodeId) {
            return entry.ledIndex;
        }
    }
    return UINT8_MAX;
}

static void applyDefaultKeys() {
    // Default placeholder keys for development; replace during provisioning.
    const uint8_t defaultFamily[32] = {
        0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88,
        0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x10,
        0x21, 0x32, 0x43, 0x54, 0x65, 0x76, 0x87, 0x98,
        0xA9, 0xBA, 0xCB, 0xDC, 0xED, 0xFE, 0x0F, 0x1F
    };
    const uint8_t defaultNode[32] = {
        0x20, 0x19, 0x72, 0x46, 0x3C, 0xAF, 0x55, 0x03,
        0xBA, 0xDC, 0x87, 0x19, 0x24, 0x68, 0xCE, 0xFA,
        0x11, 0x9B, 0x40, 0x07, 0x88, 0x11, 0xEE, 0x4A,
        0x7C, 0x6D, 0x5E, 0x3F, 0x10, 0x90, 0xAB, 0xCD
    };
    memcpy(g_familyKey, defaultFamily, sizeof(defaultFamily));
    memcpy(g_nodeKey, defaultNode, sizeof(defaultNode));
}

static bool loadKeysFromPrefs() {
    bool loaded = false;
    if (g_prefs.begin("crypto", true)) {
        size_t fam = g_prefs.getBytes("family", g_familyKey, sizeof(g_familyKey));
        size_t node = g_prefs.getBytes("node", g_nodeKey, sizeof(g_nodeKey));
        uint32_t storedId = g_prefs.getULong("nodeid", g_nodeId);
        g_nodeId = storedId;
        loaded = (fam == sizeof(g_familyKey) && node == sizeof(g_nodeKey));
        g_prefs.end();
    }
    if (!loaded) {
        applyDefaultKeys();
    }
    return loaded;
}

static void persistKey(const char *name, const uint8_t *data, size_t len) {
    if (len != 32) {
        return;
    }
    if (g_prefs.begin("crypto", false)) {
        g_prefs.putBytes(name, data, len);
        g_prefs.end();
    }
}

static void persistNodeId(uint32_t nodeId) {
    if (g_prefs.begin("crypto", false)) {
        g_prefs.putULong("nodeid", nodeId);
        g_prefs.end();
    }
}

static bool deriveSessionKey() {
    static const char salt[] = "NewcastleMeshv1";
    HKDF<SHA256> hkdf;
    hkdf.begin(g_familyKey, sizeof(g_familyKey), g_nodeKey, sizeof(g_nodeKey),
               reinterpret_cast<const uint8_t *>(salt), sizeof(salt) - 1);
    hkdf.generate(g_sessionKey, sizeof(g_sessionKey));
    g_sessionReady = true;
    return true;
}

static uint32_t currentEpochMinutes() {
    time_t now = time(nullptr);
    if (now > 0) {
        return static_cast<uint32_t>(now / 60);
    }
    return millis() / 60000;
}

static void setAllLeds(uint32_t color) {
    for (uint8_t i = 0; i < LED_COUNT; ++i) {
        g_strip.setPixelColor(i, color);
    }
    g_strip.show();
}

static uint32_t colorFromRGB(uint8_t r, uint8_t g, uint8_t b) {
    return g_strip.Color(r, g, b);
}

static bool readExact(uint8_t *buffer, uint16_t len) {
    uint16_t offset = 0;
    uint32_t start = millis();
    while (offset < len && (millis() - start) < 1000) {
        if (Serial.available()) {
            buffer[offset++] = static_cast<uint8_t>(Serial.read());
        } else {
            delay(5);
        }
    }
    return offset == len;
}

static void processSerialProvisioning() {
    while (Serial.available() >= 5) {
        uint8_t cmd[3];
        if (Serial.readBytes(reinterpret_cast<char *>(cmd), sizeof(cmd)) != sizeof(cmd)) {
            return;
        }
        uint8_t lenBytes[2];
        if (Serial.readBytes(reinterpret_cast<char *>(lenBytes), sizeof(lenBytes)) != sizeof(lenBytes)) {
            return;
        }
        uint16_t len = static_cast<uint16_t>(lenBytes[0] | (lenBytes[1] << 8));
        if (len > 256) {
            Serial.write(PROVISION_ERR, sizeof(PROVISION_ERR) - 1);
            continue;
        }
        uint8_t payload[256];
        if (!readExact(payload, len)) {
            return;
        }

        bool ok = false;
        if (memcmp(cmd, "FAM", 3) == 0 && len == 32) {
            memcpy(g_familyKey, payload, 32);
            persistKey("family", payload, 32);
            ok = true;
            g_sessionReady = false;
        } else if (memcmp(cmd, "NOD", 3) == 0 && len == 32) {
            memcpy(g_nodeKey, payload, 32);
            persistKey("node", payload, 32);
            ok = true;
            g_sessionReady = false;
        } else if (cmd[0] == 'I' && cmd[1] == 'D' && len == 4) {
            uint32_t nodeId = payload[0] | (payload[1] << 8) | (payload[2] << 16) | (payload[3] << 24);
            g_nodeId = nodeId;
            persistNodeId(nodeId);
            ok = true;
        } else if (memcmp(cmd, "COM", 3) == 0 && len == 0) {
            deriveSessionKey();
            g_sessionCounter = 1;
            markLocalHeartbeat();
            ok = true;
        }

        if (ok) {
            Serial.write(PROVISION_ACK, sizeof(PROVISION_ACK) - 1);
        } else {
            Serial.write(PROVISION_ERR, sizeof(PROVISION_ERR) - 1);
        }
    }
}

static void refreshLeds() {
    if (!g_sessionReady) {
        setAllLeds(colorFromRGB(0x00, 0x30, 0xFF)); // Soft blue while waiting for session
        return;
    }

    uint32_t now = millis();
    for (uint8_t i = 0; i < LED_COUNT; ++i) {
        NodeStatus &st = g_status[i];
        bool missing = !st.seen || (now - st.lastHeartbeatMs) > HEARTBEAT_TIMEOUT_MS;
        uint32_t color = 0;
        if (st.sosActive) {
            float phase = static_cast<float>((now % 2000UL)) / 2000.0f;
            uint8_t level = static_cast<uint8_t>(127.0f * (sinf(phase * TWO_PI) + 1.0f));
            color = colorFromRGB(level, 0, 0);
        } else if (missing) {
            color = colorFromRGB(0xFF, 0xAA, 0x00); // Yellow
        } else {
            color = colorFromRGB(0x00, 0xFF, 0x00); // Green
        }
        g_strip.setPixelColor(i, color);
    }
    g_strip.show();
}

static bool encryptPayload(const uint8_t *plaintext, size_t len, const uint8_t *nonce,
                           uint8_t *ciphertext, uint8_t *tag) {
    if (!g_sessionReady) {
        return false;
    }
    GCM<AES256> gcm;
    if (!gcm.setKey(g_sessionKey, sizeof(g_sessionKey))) {
        return false;
    }
    if (!gcm.setIV(nonce, 12)) {
        return false;
    }
    gcm.encrypt(ciphertext, plaintext, len);
    gcm.computeTag(tag, 16);
    return true;
}

static bool decryptPayload(const uint8_t *ciphertext, size_t len, const uint8_t *nonce,
                           const uint8_t *tag, uint8_t *plaintext) {
    if (!g_sessionReady) {
        return false;
    }
    GCM<AES256> gcm;
    if (!gcm.setKey(g_sessionKey, sizeof(g_sessionKey))) {
        return false;
    }
    if (!gcm.setIV(nonce, 12)) {
        return false;
    }
    gcm.decrypt(plaintext, ciphertext, len);
    return gcm.checkTag(tag, 16);
}

static void markLocalHeartbeat() {
    uint8_t idx = findIndexForNode(g_nodeId);
    if (idx != UINT8_MAX) {
        g_status[idx].seen = true;
        g_status[idx].sosActive = false;
        g_status[idx].lastHeartbeatMs = millis();
        g_status[idx].lastCounter = g_sessionCounter;
    }
}

static void markLocalSos(bool active) {
    uint8_t idx = findIndexForNode(g_nodeId);
    if (idx != UINT8_MAX) {
        g_status[idx].seen = true;
        g_status[idx].sosActive = active;
        g_status[idx].lastHeartbeatMs = millis();
        g_status[idx].lastCounter = g_sessionCounter;
    }
    g_localSosLatched = active;
}

enum class MessageKind : uint8_t {
    Heartbeat,
    Sos
};

static void sendStatus(MessageKind kind, bool sosActive) {
    if (!g_sessionReady) {
        Serial.println("WARN: Session not ready; skipping send");
        return;
    }

    StaticJsonDocument<256> doc;
    doc["node"] = g_nodeId;
    doc["ctr"] = g_sessionCounter++;
    doc["hop"] = DEFAULT_HOP_LIMIT;
    doc["ts"] = currentEpochMinutes();

    switch (kind) {
        case MessageKind::Heartbeat:
            doc["type"] = "hb";
            break;
        case MessageKind::Sos:
            doc["type"] = "sos";
            doc["active"] = sosActive;
            break;
    }

    uint8_t plaintext[256];
    size_t len = serializeJson(doc, plaintext, sizeof(plaintext));
    if (len == 0 || len > 200) {
        Serial.println("ERROR: Payload too large");
        return;
    }

    uint8_t nonce[12];
    for (uint8_t i = 0; i < sizeof(nonce); ++i) {
        nonce[i] = static_cast<uint8_t>(esp_random() & 0xFF);
    }

    uint8_t ciphertext[256];
    uint8_t tag[16];
    if (!encryptPayload(plaintext, len, nonce, ciphertext, tag)) {
        Serial.println("ERROR: Encryption failed");
        return;
    }

    LoRa.beginPacket();
    LoRa.write(static_cast<uint8_t>(0x01)); // protocol version
    LoRa.write(nonce, sizeof(nonce));
    LoRa.write(static_cast<uint8_t>(len));
    LoRa.write(ciphertext, len);
    LoRa.write(tag, sizeof(tag));
    LoRa.endPacket();

    if (kind == MessageKind::Heartbeat) {
        Serial.println("INFO: Heartbeat sent");
        markLocalHeartbeat();
    } else {
        Serial.printf("INFO: SOS state broadcast (active=%d)\n", sosActive);
        markLocalSos(sosActive);
    }
}

static void handleInboundPacket(int packetSize) {
    if (packetSize < 1 + 12 + 1 + 16) {
        return; // malformed
    }

    uint8_t version = LoRa.read();
    if (version != 0x01) {
        return;
    }

    uint8_t nonce[12];
    LoRa.readBytes(nonce, sizeof(nonce));
    uint8_t len = LoRa.read();
    if (len > 200 || len + 16 > packetSize - 13) {
        return;
    }

    uint8_t ciphertext[256];
    uint8_t tag[16];
    LoRa.readBytes(ciphertext, len);
    LoRa.readBytes(tag, sizeof(tag));

    uint8_t plaintext[256];
    if (!decryptPayload(ciphertext, len, nonce, tag, plaintext)) {
        Serial.println("WARN: Auth failure");
        return;
    }

    StaticJsonDocument<256> doc;
    DeserializationError err = deserializeJson(doc, plaintext, len);
    if (err) {
        Serial.printf("WARN: JSON parse error %s\n", err.c_str());
        return;
    }

    uint32_t sender = doc["node"] | 0;
    uint8_t idx = findIndexForNode(sender);
    if (idx == UINT8_MAX) {
        Serial.println("WARN: Unknown node ID");
        return;
    }

    uint32_t ctr = doc["ctr"] | 0;
    if (ctr <= g_status[idx].lastCounter) {
        Serial.println("WARN: Replay detected");
        return;
    }

    g_status[idx].lastCounter = ctr;
    g_status[idx].seen = true;
    g_status[idx].lastHeartbeatMs = millis();

    const char *type = doc["type"] | "";
    if (strcmp(type, "hb") == 0) {
        g_status[idx].sosActive = false;
        Serial.printf("INFO: Heartbeat from 0x%08lX\n", sender);
    } else if (strcmp(type, "sos") == 0) {
        bool active = doc["active"].as<bool>();
        g_status[idx].sosActive = active;
        Serial.printf("INFO: SOS %s from 0x%08lX\n", active ? "ACTIVE" : "CLEARED", sender);
        if (sender == g_nodeId && !active) {
            g_localSosLatched = false;
        }
    }
}

static void processLoRa() {
    int packetSize = LoRa.parsePacket();
    if (packetSize) {
        handleInboundPacket(packetSize);
    }
}

static void processButtons() {
    bool okState = digitalRead(BUTTON_OK_PIN) == LOW;
    bool sosState = digitalRead(BUTTON_SOS_PIN) == LOW;
    bool adminState = digitalRead(BUTTON_ADMIN_PIN) == LOW;
    uint32_t now = millis();

    // OK button (short press)
    if (okState && !g_okDown) {
        g_okDown = true;
        g_okPressStart = now;
    } else if (!okState && g_okDown) {
        g_okDown = false;
        if ((now - g_okPressStart) > 50) { // debounce threshold
            sendStatus(MessageKind::Heartbeat, false);
            g_lastHeartbeatSentMs = now;
        }
    }

    // SOS button (long press)
    if (sosState && !g_sosDown) {
        g_sosDown = true;
        g_sosPressStart = now;
    } else if (!sosState && g_sosDown) {
        bool longPress = (now - g_sosPressStart) >= SOS_HOLD_MS;
        g_sosDown = false;
        if (longPress) {
            bool newState = !g_localSosLatched;
            sendStatus(MessageKind::Sos, newState);
        }
    }

    // Admin button clears SOS and acknowledges alerts
    if (adminState && !g_adminDown) {
        g_adminDown = true;
        g_adminPressStart = now;
    } else if (!adminState && g_adminDown) {
        bool longPress = (now - g_adminPressStart) >= ADMIN_HOLD_MS;
        g_adminDown = false;
        if (longPress) {
            sendStatus(MessageKind::Sos, false);
            Serial.println("INFO: Admin reset issued");
        }
    }
}

static void housekeeping() {
    uint32_t now = millis();
    if ((now - g_lastHeartbeatSentMs) > (HB_INTERVAL_MIN * 60000UL)) {
        sendStatus(MessageKind::Heartbeat, false);
        g_lastHeartbeatSentMs = now;
    }
}

void setup() {
    Serial.begin(115200);
    delay(200);

    pinMode(BUTTON_OK_PIN, INPUT_PULLUP);
    pinMode(BUTTON_SOS_PIN, INPUT_PULLUP);
    pinMode(BUTTON_ADMIN_PIN, INPUT_PULLUP);

    g_strip.begin();
    g_strip.clear();
    g_strip.show();

    bool keysLoaded = loadKeysFromPrefs();
    deriveSessionKey();
    Serial.printf("INFO: Keys %sloaded\n", keysLoaded ? "" : "NOT ");

    SPI.begin(5, 19, 27, LORA_SS);
    LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
    if (!LoRa.begin(FREQUENCY)) {
        Serial.println("ERROR: LoRa init failed");
        while (true) {
            delay(1000);
        }
    }
    LoRa.enableCrc();
    Serial.println("INFO: LoRa ready");

    markLocalHeartbeat();
    g_lastHeartbeatSentMs = millis();
    g_nextLedUpdateMs = 0;
}

void loop() {
    processLoRa();
    processButtons();
    processSerialProvisioning();
    housekeeping();

    uint32_t now = millis();
    if (now - g_nextLedUpdateMs >= 100) {
        refreshLeds();
        g_nextLedUpdateMs = now;
    }
}

