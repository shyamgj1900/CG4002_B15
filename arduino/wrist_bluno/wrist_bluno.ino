// CONFIG VARS: Set these variables here accordingly
//   DATACOLLECTION - true if glove is wired for data collection, false for actual runs/bluetooth tests
//   DEBUG          - true if DATACOLLECTION and if we need debug information
//   GLOVE_ID       - 'R' or 'B', check the white tag on the wrist strap

bool DATACOLLECTION = false;
bool DEBUG = DATACOLLECTION && false; // DEBUG only possible if DATACOLLECTION is true
char GLOVE_ID = 'B';


// LIBRARIES

// For calculating CRC
#include "CRC8.h"
// For timing 0.1s windows for sample aggregation
#include <arduino-timer.h>
// For queueing packets
#include <cppQueue.h>
// For communication with MPU6050 and DMP
#include "I2Cdev.h"
#include "MPU6050_6Axis_MotionApps20.h"
#if I2CDEV_IMPLEMENTATION == I2CDEV_ARDUINO_WIRE
#include "Wire.h"
#endif


// The MPU6050 interface
MPU6050 mpu;

// Timer object for aggregating samples
// 1 concurrent task, using millis as resolution
Timer<1> timer;

#define INTERRUPT_PIN 2  // use pin 2 on Arduino Uno & most boards

// MPU control/status vars
bool dmpReady = false;  // set true if DMP init was successful
uint8_t mpuIntStatus;   // holds actual interrupt status byte from MPU
uint8_t devStatus;      // return status after each device operation (0 = success, !0 = error)
uint16_t packetSize;    // expected DMP packet size (default is 42 bytes)
uint16_t fifoCount;     // count of all bytes currently in FIFO
uint8_t fifoBuffer[64]; // FIFO storage buffer

// orientation/motion vars
Quaternion q;           // [w, x, y, z]         quaternion container
VectorInt16 aa;         // [x, y, z]            accel sensor measurements
VectorInt16 aaReal;     // [x, y, z]            gravity-free accel sensor measurements
VectorInt16 aaWorld;    // [x, y, z]            world-frame accel sensor measurements
VectorFloat gravity;    // [x, y, z]            gravity vector
float euler[3];         // [psi, theta, phi]    Euler angle container
float ypr[3];           // [yaw, pitch, roll]   yaw/pitch/roll container and gravity vector

// for aggregating the samples
long aggAaWorld[3];
float aggYpr[3];

// for averaging the samples
long aveAaWorld[3];
float aveYpr[3];

// for buffering packets
struct movement {
  long accel_x;
  long accel_y;
  long accel_z;
  float gyro_y;
  float gyro_p;
  float gyro_r;
  bool reload;
  bool onset;
  long guid;
};
cppQueue movementBuffer(sizeof(movement), 10, FIFO);
volatile long guidCounter = 0;

// for onset detection
int BLACKOUT_PERIOD = 30;
int onsetCounter = 0;
volatile int blackoutCounter = 0;
bool send10PacketsFlag = false;


// ================================================================
// ===               INTERRUPT DETECTION ROUTINE                ===
// ================================================================

volatile bool mpuInterrupt = false;     // indicates whether MPU interrupt pin has gone high
void dmpDataReady() {
  mpuInterrupt = true;
}


// ================================================================
// ===                      INITIAL SETUP                       ===
// ================================================================

void setup() {
  // join I2C bus (I2Cdev library doesn't do this automatically)
#if I2CDEV_IMPLEMENTATION == I2CDEV_ARDUINO_WIRE
  Wire.begin();
  Wire.setClock(400000); // 400kHz I2C clock. Comment this line if having compilation difficulties
#elif I2CDEV_IMPLEMENTATION == I2CDEV_BUILTIN_FASTWIRE
  Fastwire::setup(400, true);
#endif

  // initialize serial communication
  Serial.begin(115200);

  // initialize device
  if (DEBUG) Serial.println("DEBUG MODE!");
  if (DATACOLLECTION) Serial.println(F("Initializing I2C devices..."));
  mpu.initialize();
  // pinMode(INTERRUPT_PIN, INPUT);

  if (DATACOLLECTION) {
    // verify connection
    Serial.println(F("Testing device connections..."));
    Serial.println(mpu.testConnection() ? F("MPU6050 connection successful") : F("MPU6050 connection failed"));

    // wait for ready
    Serial.println(F("\nSend any character to begin DMP programming and demo: "));
    while (Serial.available() && Serial.read()); // empty buffer
    while (!Serial.available());                 // wait for data
    while (Serial.available() && Serial.read()); // empty buffer again

    // load and configure the DMP
    Serial.println(F("Initializing DMP..."));
  }
  devStatus = mpu.dmpInitialize();

  // offsets obtained from the calibration sketch
  if (DATACOLLECTION) {
    Serial.print("Calibrating as ");
    Serial.println(GLOVE_ID);
  }
  if (GLOVE_ID == 'B') {
    mpu.setXGyroOffset(-45);
    mpu.setYGyroOffset(-116);
    mpu.setZGyroOffset(9);
    mpu.setXAccelOffset(-6244);
    mpu.setYAccelOffset(-208);
    mpu.setZAccelOffset(2963);
  } else {  // R BAND
    mpu.setXGyroOffset(140);
    mpu.setYGyroOffset(57);
    mpu.setZGyroOffset(-18);
    mpu.setXAccelOffset(-3564);
    mpu.setYAccelOffset(-3099);
    mpu.setZAccelOffset(3577);
  }

  // make sure it worked (returns 0 if so)
  if (devStatus == 0) {

    // generate offsets and calibrate our MPU6050
    mpu.CalibrateAccel(6);
    mpu.CalibrateGyro(6);
    mpu.PrintActiveOffsets();

    // turn on the DMP, now that it's ready
    if (DATACOLLECTION) Serial.println(F("Enabling DMP..."));
    mpu.setDMPEnabled(true);

    // enable Arduino interrupt detection
    //    if (DATACOLLECTION) {
    //      Serial.print(F("Enabling interrupt detection (Arduino external interrupt "));
    //      Serial.print(digitalPinToInterrupt(INTERRUPT_PIN));
    //      Serial.println(F(")..."));
    //    }
    //    attachInterrupt(digitalPinToInterrupt(INTERRUPT_PIN), dmpDataReady, RISING);
    //    mpuIntStatus = mpu.getIntStatus();
    //    if (DATACOLLECTION) Serial.println(mpuIntStatus);

    // set our DMP Ready flag so the main loop() function knows it's okay to use it
    if (DATACOLLECTION) Serial.println(F("DMP ready, start testing!"));
    dmpReady = true;

    // get expected DMP packet size for later comparison
    packetSize = mpu.dmpGetFIFOPacketSize();
  } else {
    // ERROR!
    // 1 = initial memory load failed
    // 2 = DMP configuration updates failed
    // (if it's going to break, usually the code will be 1)
    if (DATACOLLECTION) {
      Serial.print(F("DMP Initialization failed (code "));
      Serial.print(devStatus);
      Serial.println(F(")"));
    }
  }

  // power saving
  powerSavingSetup();

  // print headers for csv if it's data collection
  if (DATACOLLECTION && !DEBUG) Serial.println("\ny\tp\tr\tx\ty\tz\tnumber");

  // finally, make the timer run the sample aggregation method every 0.1s
  timer.every(100, aggregateSamples);
}

void powerSavingSetup() {
  PRR |= 0b01001001; // Disable some timer 1 and 2 and ADC
  ADCSRA = 0; // To disable ADC too
}

// ================================================================
// ===                      MPU6050 / ONSET                     ===
// ================================================================

// To be run each loop to aggregate data from DMP
void readWristData() {
  // if programming failed, don't try to do anything
  if (!dmpReady) return;
  // read a packet from FIFO
  if (mpu.dmpGetCurrentFIFOPacket(fifoBuffer)) { // Get the Latest packet

    // read the FIFO buffer and get key values
    mpu.dmpGetQuaternion(&q, fifoBuffer);
    mpu.dmpGetGravity(&gravity, &q);
    mpu.dmpGetAccel(&aa, fifoBuffer);

    // calculate YPR angles in degrees
    mpu.dmpGetYawPitchRoll(ypr, &q, &gravity);
    aggYpr[0] += ypr[0] * 180 / M_PI; // yaw
    aggYpr[1] += ypr[1] * 180 / M_PI; // pitch
    aggYpr[2] += ypr[2] * 180 / M_PI; // roll

    // calculate real acceleration, adjusted to remove gravity
    mpu.dmpGetLinearAccel(&aaReal, &aa, &gravity);
    mpu.dmpGetLinearAccelInWorld(&aaWorld, &aaReal, &q);
    aggAaWorld[0] += (long)aaWorld.x;
    aggAaWorld[1] += (long)aaWorld.y;
    aggAaWorld[2] += (long)aaWorld.z;
  }
}


// To be run by timer
// bool output is required by timer library
bool aggregateSamples(void *) {
  struct movement currentMvmt;
  currentMvmt.gyro_y = aggYpr[0] / 10;
  currentMvmt.gyro_p = aggYpr[1] / 10;
  currentMvmt.gyro_r = aggYpr[2] / 10;
  currentMvmt.accel_x = (aggAaWorld[0] / 10);
  currentMvmt.accel_y = (aggAaWorld[1] / 10);
  currentMvmt.accel_z = (aggAaWorld[2] / 10);
  aggYpr[0] = 0;
  aggYpr[1] = 0;
  aggYpr[2] = 0;
  aggAaWorld[0] = 0;
  aggAaWorld[1] = 0;
  aggAaWorld[2] = 0;

  currentMvmt.guid = guidCounter;
  guidCounter++;

  // 1. Onsets should be separated by at least 10 packets
  //    So, only try detecting onset if we are not in the blackout period
  //    We try to keep all uses of movementBuffer contained in this function
  // 2. The movement buffer should also be full, since the onset packet needs
  //    to be in the middle of 10 packets (a full buffer)

  if ((blackoutCounter == 0) && movementBuffer.isFull()) {
    struct movement previousMvmt;  // the latest packet
    struct movement previousMvmt2; // the second latest packet
    movementBuffer.peekIdx(&previousMvmt, 9);  // get last
    movementBuffer.peekIdx(&previousMvmt2, 8); // get second last
    int onsetVal = detectOnset(currentMvmt, previousMvmt, previousMvmt2);
    
    if (onsetVal == 2) currentMvmt.reload = true;
    else if (onsetVal == 1) currentMvmt.onset = true;
    
    if (currentMvmt.onset || currentMvmt.reload) blackoutCounter = BLACKOUT_PERIOD;
    if (currentMvmt.onset) send10PacketsFlag = true; // we only send 10 packets if it's a normal onset
  } else {
    currentMvmt.reload = false;
    currentMvmt.onset = false;
    if (blackoutCounter > 0) {
      blackoutCounter--;
      if (blackoutCounter == 0 && DATACOLLECTION) Serial.print("\tBlackout over!");
    }
  }

  // Add current movement to the buffer

  if (movementBuffer.isFull()) movementBuffer.drop();
  movementBuffer.push(&currentMvmt);


  // If the current movement's reload flag is set, we send a special reload packet
  // Else if the send10PacketsFlag is set, we only send the contents of the movement
  // buffer when the onset movement is the FIFTH item in the queue

  if (currentMvmt.reload) {
    if (DATACOLLECTION && DEBUG) Serial.println("RELOAD DETECTED");
    else transmitReload();
  } else if (send10PacketsFlag && blackoutCounter == BLACKOUT_PERIOD - 5) {
    send10PacketsFlag = false;
    struct movement packetToSend;
    while (!movementBuffer.isEmpty()) {
      movementBuffer.pop(&packetToSend);
      if (DATACOLLECTION) {
        Serial.println(""); // to separate each line of data
        printWristData(packetToSend); // print to serial
      } else {
        transmitWristData(packetToSend); // send over Bluetooth
      }
    }
  }

  

  return true; // to repeat the action
}


void printWristData(struct movement curr) {
  Serial.print(curr.gyro_y);
  Serial.print("\t");
  Serial.print(curr.gyro_p);
  Serial.print("\t");
  Serial.print(curr.gyro_r);
  Serial.print("\t");
  Serial.print(curr.accel_x);
  Serial.print("\t");
  Serial.print(curr.accel_y);
  Serial.print("\t");
  Serial.print(curr.accel_z);
  Serial.print("\t");
  Serial.print(onsetCounter);
  if (DEBUG) {
    Serial.print("\t");
    Serial.print(curr.guid);
  }
  // new line to be printed outside
}


int detectOnset(struct movement newMvmt,
                struct movement previousMvmt,
                struct movement previousMvmt2) {
  bool gyro_delta;
  bool accl_delta;
  bool reload_delta;

  gyro_delta = ((abs(previousMvmt2.gyro_y - newMvmt.gyro_y)) > 60) ||
               ((abs(previousMvmt2.gyro_p - newMvmt.gyro_p)) > 60) ||
               ((abs(previousMvmt2.gyro_r - newMvmt.gyro_r)) > 60);

  accl_delta = ((abs(previousMvmt.accel_x - newMvmt.accel_x)) > 12000) ||
               ((abs(previousMvmt.accel_y - newMvmt.accel_y)) > 12000) ||
               ((abs(previousMvmt.accel_z - newMvmt.accel_z)) > 12000);

  // currently using z-axis, axis depends on how the MPU-6050 is oriented
  // we expect sharp increase in z-axis accel, so we check for that here
  reload_delta = ((newMvmt.accel_z - previousMvmt.accel_z) > 3000) &&
                 ((abs(previousMvmt.gyro_y - newMvmt.gyro_y)) < 5) &&
                 ((abs(previousMvmt.gyro_p - newMvmt.gyro_p)) < 5) &&
                 ((abs(previousMvmt.gyro_r - newMvmt.gyro_r)) < 5);

  bool onsetDetected = reload_delta || (gyro_delta && accl_delta);
//  if (onsetDetected) {
  if (gyro_delta && accl_delta) {
    onsetCounter++;
    if (DATACOLLECTION && DEBUG) {
      Serial.print("Prev packet ID: ");
      Serial.print(previousMvmt.guid);
      Serial.print(", New packet ID: ");
      Serial.print(newMvmt.guid);
      Serial.print(" -> Reload: ");
      Serial.print(reload_delta);
      Serial.print(", Gyro: ");
      Serial.print(gyro_delta);
      Serial.print(", Accel: ");
      Serial.println(accl_delta);
    }
  }

  // return flag values
  //if (reload_delta) return 2;
  if (gyro_delta && accl_delta) return 1;
  else return 0;
}


// ================================================================
// ===                   BLUETOOTH FUNCTIONS                    ===
// ================================================================


CRC8 crc;


// Struct for handshake
struct Handshake_Data {
  int8_t packet_type;
  int8_t checksum;
};


// Struct for wrist
struct Wrist_Data {
  int8_t packet_type;
  int16_t  x_acceleration;
  int16_t  y_acceleration;
  int16_t  z_acceleration;
  int16_t  row;
  int16_t  pitch;
  int16_t  yaw;
  int8_t checksum;
};


byte twoByteBuf[2];
struct Wrist_Data wrist_data;
struct Handshake_Data handshake_data;
const int BUFFER_SIZE = 20;
byte buf[BUFFER_SIZE];


void serialWriteBuffer(int n) {
  for (int i = 0; i < n; i++) {
    Serial.write(0);
    crc.add(0);
  }
}


void writeIntToSerial(int16_t data) {
  twoByteBuf[1] = data & 255;
  twoByteBuf[0] = (data >> 8) & 255;
  Serial.write(twoByteBuf, sizeof(twoByteBuf));
  crc.add(twoByteBuf, sizeof(twoByteBuf));
}


// * Reset Beetle Programmatically
void (* resetBeetle) (void) = 0;


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

// send R
void transmitReload() {
  crc.restart();// Restart crc caclulation
  // One byte packet type and add to CRC
  handshake_data.packet_type = 'R';
  Serial.write(handshake_data.packet_type);
  crc.add(handshake_data.packet_type);
  serialWriteBuffer(18);
  handshake_data.checksum = crc.getCRC(); // One byte checksum
  Serial.write(handshake_data.checksum);
  // Restart crc caclulation
  Serial.flush();
}


void transmitWristData(struct movement curr) {
  crc.restart();// Restart crc caclulation
  wrist_data.packet_type = 'W'; //
  // to change to actual data
  readWristData();
  Serial.write(wrist_data.packet_type);
  crc.add(wrist_data.packet_type);

  writeIntToSerial(int16_t(curr.gyro_y * 100));
  writeIntToSerial(int16_t(curr.gyro_p * 100));
  writeIntToSerial(int16_t(curr.gyro_r * 100));
  writeIntToSerial(int16_t(curr.accel_x));
  writeIntToSerial(int16_t(curr.accel_y));
  writeIntToSerial(int16_t(curr.accel_z));

  serialWriteBuffer(6);
  wrist_data.checksum = crc.getCRC(); // One byte checksum
  Serial.write(wrist_data.checksum);

  Serial.flush();
}


void bluetoothLoop() {
  int static startHandshake = 0;
  int static endHandshake = 0;
  unsigned static long currentTime = 0;
  unsigned static long lastTime = 0;
  int static i = 0;
  byte buf[BUFFER_SIZE];
  byte packetType = buf[0];
  if (Serial.available() > 0) {
    int rlen = Serial.readBytes(buf, BUFFER_SIZE);
    packetType = buf[0];
  }

  if (packetType == 'R') {
    resetBeetle();
  }

  if (packetType == 'H') {
    currentTime = millis();
    if(currentTime-lastTime>350){
      transmitHandshake();
      startHandshake = 1;
      endHandshake = 0;
      lastTime = currentTime;
    }
  }

  if (packetType == 'A' && startHandshake == 1) {
    //receive ack bluno-pc connection
    startHandshake = 0;
    endHandshake = 1;
  }

  if (endHandshake == 1) {
    currentTime = millis();
    readWristData();
  }
}


// ================================================================
// ===                    MAIN PROGRAM LOOP                     ===
// ================================================================

void loop() {
  if (DATACOLLECTION) {
    readWristData();
  } else {
    bluetoothLoop(); // readWristData is inside bluetoothLoop
  }

  // Tick tock
  timer.tick();
}
