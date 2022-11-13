#include "CRC8.h"
#include <Arduino.h>
#define BAUD_RATE 115200
#define ACK_TIMEOUT 500

// ================================================================
// ===                 IR EMITTER DATA_TYPES                   ===
// ================================================================

//#define SEND_PWM_BY_TIMER         // Disable carrier PWM generation in software and use (restricted) hardware PWM.
//#define USE_NO_SEND_PWM           // Use no carrier PWM, just simulate an active low receiver signal. Overrides SEND_PWM_BY_TIMER definition

#include "PinDefinitionsAndMore.h" // Define macros for input and output pin etc.
#include <IRremote.hpp>
#define BUTTON_PIN 4

/*
   Set up the data to be sent.
   For most protocols, the data is build up with a constant 8 (or 16 byte) address
   and a variable 8 bit command.
   There are exceptions like Sony and Denon, which have 5 bit address.
*/
uint16_t sAddress = 0x0102;
uint8_t sCommand = 0x68; // Player 1
//uint8_t sCommand = 0x97; // Player 2
uint8_t sRepeats = 0;

// ================================================================
// ===                  HANDSHAKE DATA_TYPES                    ===
// ================================================================
unsigned long currentTime = 0;
unsigned long packetSentTime = 0;
unsigned static long currentBTime = 0;
unsigned static long lastBTime = 0;
const int BUFFER_SIZE = 20;
byte buf[BUFFER_SIZE];

int received_ACK = 0;
int static isShoot = 0;
CRC8 crc;

//Struct for handshake
struct Handshake_Data {
  int8_t packet_type;
  int8_t checksum;
};

//Struct for IR_emitter
struct Gun_Data {
  int8_t packet_type;
  int8_t sequence_number;
  int8_t prev_sequence_number;
  int8_t shoot;
  int8_t checksum;
};

struct Gun_Data gun_data;
struct Handshake_Data handshake_data;

// ================================================================
// ===                    HANDSHAKE FUNCTIONS                    ===
// ================================================================
void serialWriteBuffer(int n) {
  for (int i = 0; i < n; i++) {
    Serial.write(0);
    crc.add(0);
  }
}

// send A
void transmitHandshake() {
  crc.restart();// Restart crc caclulation
  // One byte packet type and add to CRC
  handshake_data.packet_type = 'A';
  Serial.write(handshake_data.packet_type);
  crc.add(handshake_data.packet_type);
  serialWriteBuffer(18);
  handshake_data.checksum = crc.getCRC(); // One byte checksum
  Serial.write(handshake_data.checksum);
  // Restart crc caclulation
  Serial.flush();
}

// * Reset Beetle Programmatically
void (* resetBeetle) (void) = 0;

// ================================================================
// ===                   IR_EMITTER FUNCTIONS                  ===
// ================================================================
void transmitGunData() {
  crc.restart();// Restart crc caclulation
  gun_data.packet_type = 'G';
  Serial.write(gun_data.packet_type);
  crc.add(gun_data.packet_type);
  Serial.write(gun_data.sequence_number);
  crc.add(gun_data.sequence_number);
  //is shoot = 1
  Serial.write(1);
  crc.add(1);

  serialWriteBuffer(16);
  gun_data.checksum = crc.getCRC(); // One byte checksum
  Serial.write(gun_data.checksum);
  Serial.flush();
}

void checkIrEmitter() {
  if (buttonPressed(BUTTON_PIN)) {
    isShoot = 0;
    //send shoot stuff
    //    Serial.println("BANG");
    //    Serial.println();
    //    Serial.print(F("Send now: address=0x"));
    //    Serial.print(sAddress, HEX);
    //    Serial.print(F(" command=0x"));
    //    Serial.print(sCommand, HEX);
    //    Serial.print(F(" repeats="));
    //    Serial.print(sRepeats);
    //    Serial.println();

    //    Serial.println(F("Send NEC with 16 bit address"));
    //    Serial.flush();

    // Receiver output for the first loop must be: Protocol=NEC Address=0x102 Command=0x34 Raw-Data=0xCB340102 (32 bits)
    IrSender.sendNEC(sAddress, sCommand, sRepeats);
    isShoot = 1;
    playShootSound();
    delay(150);  // delay must be greater than 5 ms (RECORD_GAP_MICROS), otherwise the receiver sees it as one long signal
  }
}

int buttonPressed(uint8_t button) {
  static uint16_t lastStates = 0;
  uint8_t state = digitalRead(button);
  if (state != ((lastStates >> button) & 1)) {
    lastStates ^= 1 << button;
    return state == LOW;
  }
  return false;
}

void playShootSound() {
  for (int i = 0; i < 50; i++) {
    tone(A0, 4000 - (50 * i), 5);
    delay(5);
  }
}
// ================================================================
// ===                         SETUP                            ===
// ================================================================
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(IR_SEND_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  Serial.begin(115200);

  // Just to know which program is running on my Arduino
  //  Serial.println(F("START " __FILE__ " from " __DATE__ "\r\nUsing library version " VERSION_IRREMOTE));

  /*
     The IR library setup. That's all!
  */
  IrSender.begin(); // Start with IR_SEND_PIN as send pin and if NO_LED_FEEDBACK_CODE is NOT defined, enable feedback LED at default feedback LED pin

  //  Serial.print(F("Ready to send IR signals at pin "));
  //  Serial.println(IR_SEND_PIN);
  tone(A0, 5000, 500); 
}

// ================================================================
// ===                    MAIN PROGRAM LOOP                     ===
// ================================================================
void loop() {
  checkIrEmitter();
  int static startHandshake = 0;
  int static endHandshake = 0;
  byte packetType = buf[0];
  if (Serial.available() > 0) {
    //    byte packetType = Serial.read() & 255;
    int rlen = Serial.readBytes(buf, BUFFER_SIZE);
    
  }

  if (endHandshake == 1) {
    //check shoot

    if (packetType == 'A') {
      //receive ack bluno-pc connection
      received_ACK = 1;
      gun_data.sequence_number = gun_data.prev_sequence_number + 1;
    }

    //new data coming in and the prev data ack has been received
    if (isShoot && received_ACK == 1) {
      received_ACK = 0;
      transmitGunData();
      isShoot = 0;
      packetSentTime = millis();
      gun_data.prev_sequence_number = gun_data.sequence_number;

    }
    currentTime = millis();
    if ((currentTime - packetSentTime > ACK_TIMEOUT) && (received_ACK == 0)) {
      gun_data.sequence_number = gun_data.prev_sequence_number;
      transmitGunData();
    }

  }//end of if endhandshake

  if (packetType == 'R') {
    resetBeetle();
  }
  if (packetType == 'H') {
    currentBTime = millis();
    if(currentBTime-lastBTime>350){
      transmitHandshake();
      startHandshake = 1;
      endHandshake = 0;
      lastBTime = currentBTime;
    }
  }
  if (packetType == 'A' && startHandshake == 1) {
    //receive ack bluno-pc connection
    received_ACK = 1;
    startHandshake = 0;
    endHandshake = 1;
  }

}//end of loop
