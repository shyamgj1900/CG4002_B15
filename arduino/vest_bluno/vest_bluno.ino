#include "CRC8.h"
#define BAUD_RATE 115200
#define ACK_TIMEOUT 500
// ================================================================
// ===                 IR RECEIVER DATA_TYPES                   ===
// ================================================================
/*
   Specify which protocol(s) should be used for decoding.
   If no protocol is defined, all protocols are active.
*/
//#define DECODE_DENON        // Includes Sharp
//#define DECODE_JVC
//#define DECODE_KASEIKYO
//#define DECODE_PANASONIC    // the same as DECODE_KASEIKYO
//#define DECODE_LG
#define DECODE_NEC          // Includes Apple and Onkyo
//#define DECODE_SAMSUNG
//#define DECODE_SONY
//#define DECODE_RC5
//#define DECODE_RC6

//#define DECODE_BOSEWAVE
//#define DECODE_LEGO_PF
//#define DECODE_MAGIQUEST
//#define DECODE_WHYNTER

//#define DECODE_DISTANCE     // universal decoder for pulse distance protocols
//#define DECODE_HASH         // special decoder for all protocols

#define DEBUG               // Activate this for lots of lovely debug output from the decoders.

#include <Arduino.h>

#define BUZZER_PIN A1
#define LED_PIN 3
#include "PinDefinitionsAndMore.h" // Define macros for input and output pin etc.
#include <IRremote.hpp>

int repeat = 0;

uint8_t sCommand = 0x68; // Player 1 shoots this, so upload this for Player 2
//uint8_t sCommand = 0x97; // Player 2 shoots this, so upload this for Player 1

// ================================================================
// ===                  HANDSHAKE DATA_TYPES                    ===
// ================================================================
unsigned long currentTime = 0;
unsigned long packetSentTime = 0;
unsigned static long currentBTime = 0;
unsigned static long lastBTime = 0;
const int BUFFER_SIZE = 20;
byte buf[BUFFER_SIZE];
int static isHit = 0;
int received_ACK = 0;
CRC8 crc;

//Struct for handshake
struct Handshake_Data {
  int8_t packet_type;
  int8_t checksum;
};

//Struct for IR_receiver
struct Vest_Data {
  int8_t packet_type;
  int8_t sequence_number = 1;
  int8_t prev_sequence_number = 0;
  int8_t hit;
  int8_t checksum;
};

struct Vest_Data vest_data;
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

//bool simulateHit() {
//  unsigned long t1 = millis();
//  if (t1 - t2 >= 3000) {
//    t2 = t1;
//    return true;
//  }
//  return false;
//}

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
// ===                   IR_RECEIVER FUNCTIONS                  ===
// ================================================================
void transmitVestData() {
  crc.restart();// Restart crc caclulation
  vest_data.packet_type = 'V';
  Serial.write(vest_data.packet_type);
  crc.add(vest_data.packet_type);
  Serial.write(vest_data.sequence_number);
  crc.add(vest_data.sequence_number);
  //is hit = 1
  Serial.write(1);
  crc.add(1);

  serialWriteBuffer(16);
  vest_data.checksum = crc.getCRC(); // One byte checksum
  Serial.write(vest_data.checksum);
  Serial.flush();
}

void checkIrReceiver() {
  /*
       Check if received data is available and if yes, try to decode it.
       Decoded result is in the IrReceiver.decodedIRData structure.

       E.g. command is in IrReceiver.decodedIRData.command
       address is in command is in IrReceiver.decodedIRData.address
       and up to 32 bit raw data in IrReceiver.decodedIRData.decodedRawData
  */


  if (IrReceiver.decode()) {
    isHit = 0;

    // Print a short summary of received data
    //    IrReceiver.printIRResultShort(&Serial);
    //    IrReceiver.printIRSendUsage(&Serial);
    if (IrReceiver.decodedIRData.protocol == UNKNOWN) {
      //      Serial.println(F("Received noise or an unknown (or not yet enabled) protocol"));
      // We have an unknown protocol here, print more info
      //      IrReceiver.printIRResultRawFormatted(&Serial, true);
    }
    //    Serial.println();

    /*
       !!!Important!!! Enable receiving of the next value,
       since receiving has stopped after the end of the current received data packet.
    */
    IrReceiver.resume(); // Enable receiving of the next value

    /*
       Finally, check the received data and perform actions according to the received command
       Command should be 0x68 for the second set
    */
    if (IrReceiver.decodedIRData.command == sCommand) {
      IrReceiver.stop();
      isHit = 1;
      playHitSound();
      delay(8);
      IrReceiver.start(8000); // to compensate for 8 ms stop of receiver. This enables a correct gap measurement.
    } else if (IrReceiver.decodedIRData.command == 0x11) {
      // do something else
    }
  }
}
void playHitSound() {
  digitalWrite(LED_PIN, HIGH);
  for (int i = 0; i < 100; i++) {
    tone(BUZZER_PIN, 1000 + (2 * i), 5);
    delay(5);
  }
  digitalWrite(LED_PIN, LOW);
}
// ================================================================
// ===                         SETUP                            ===
// ================================================================
void setup() {
  // put your setup code here, to run once:

  pinMode(LED_PIN, OUTPUT);
  Serial.begin(115200);
  tone(BUZZER_PIN, 5000, 500);
  digitalWrite(LED_PIN, HIGH);
  delay(500);
  digitalWrite(LED_PIN, LOW);
  // Just to know which program is running on my Arduino
  //  Serial.println(F("START " __FILE__ " from " __DATE__ "\r\nUsing library version " VERSION_IRREMOTE));

  // Start the receiver and if not 3. parameter specified, take LED_BUILTIN pin from the internal boards definition as default feedback LED
  IrReceiver.begin(IR_RECEIVE_PIN, ENABLE_LED_FEEDBACK);

  //  Serial.print(F("Ready to receive IR signals of protocols: "));
  //  printActiveIRProtocols(&Serial);
  //  Serial.println(F("at pin " STR(IR_RECEIVE_PIN)));
}

// ================================================================
// ===                    MAIN PROGRAM LOOP                     ===
// ================================================================
void loop() {
  checkIrReceiver();
  int static startHandshake = 0;
  int static endHandshake = 0;
  byte packetType = buf[0];
  if (Serial.available()) {
    //    byte packetType = Serial.read() & 255;
    int rlen = Serial.readBytes(buf, BUFFER_SIZE);
    //    byte received_ACK = buff[1];

  }
  
  if (endHandshake == 1) {
    if (packetType == 'A') {
      //data received correctly
      received_ACK = 1;
      vest_data.sequence_number = vest_data.prev_sequence_number + 1;
    }

    //new data coming in and the prev data ack has been received
    if (isHit && received_ACK == 1) {
      received_ACK = 0;
      transmitVestData();
      isHit = 0;
      packetSentTime = millis();
      vest_data.prev_sequence_number = vest_data.sequence_number;
    }
    currentTime = millis();
    if ((currentTime - packetSentTime > ACK_TIMEOUT) && (received_ACK == 0)) {
      vest_data.sequence_number = vest_data.prev_sequence_number;
      transmitVestData();
    }

  }//end of if handshake
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
    startHandshake = 0;
    endHandshake = 1;

  }
}
