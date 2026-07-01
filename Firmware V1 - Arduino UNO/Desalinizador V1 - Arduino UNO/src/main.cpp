#include <Arduino.h>

// the sensor communicates using SPI, so include the hardware SPI library:
#include <SPI.h>
// include Playing With Fusion MAX31865 library
#include <PwFusion_MAX31865.h> 
#include "I2CScanner.h"

// CS pin used for the connection with the sensor
// other connections are controlled by the SPI library)
const int CS_PIN = 9;
I2CScanner scanner;
// Create instance of MAX31865 class
MAX31865 rtd0;

void PrintRTDStatus(uint8_t status);
  
void setup() {
  Serial.begin(9600);
  Serial.println(F("Boot"));

  // setup for the the SPI library:
  SPI.begin();

  // initalize the chip select pin
  pinMode(CS_PIN, OUTPUT);

  // configure rtd sensor
  rtd0.begin(CS_PIN, RTD_4_WIRE, RTD_TYPE_PT100);
  rtd0.setLowFaultTemperature(30);  // Set the low fault threshold to 30 degrees C
  rtd0.setHighFaultTemperature(70); // Set the high fault threshold to 70 degrees C

  Serial.println(F("MAX31865 Configured"));
  // give the sensor time to set up
  delay(100);
  
  // Init i2c scanner
  scanner.Init();


}


void loop() 
{
  // Get the latest temperature and status values from the MAX31865
  rtd0.sample();
  // Print the current values to the serial port
  /*
  Serial.print(rtd0.getResistance());
  Serial.print(F(" Ohms,   "));
  Serial.print(rtd0.getTemperature());
  Serial.print(F(" C,   "));
  // Print the Status bitmask
  PrintRTDStatus(rtd0.getStatus());
  // can be faster
  delay(100);
  */
  scanner.Scan();
  delay(5000);
}

void PrintRTDStatus(uint8_t status)
{
  // status will be 0 if no faults are active
  if (status == 0)
  {
    Serial.print(F("OK"));
  }
  else 
  {
    // status is a bitmask, so multiple faults may be active at the same time    
    // The RTD temperature is above the threshold set by setHighFaultTemperature()
    if (status & RTD_FAULT_TEMP_HIGH)
    {
      Serial.print(F("RTD High Threshold Met, "));
    }

    // The RTD temperature is below the threshold set by setHLowFaultTemperature()
    if (status & RTD_FAULT_TEMP_LOW)
    {
      Serial.print(F("RTD Low Threshold Met, "));
    }

    // The RefIn- is > 0.85 x Vbias
    if (status & RTD_FAULT_REFIN_HIGH)
    {
      Serial.print(F("REFin- > 0.85 x Vbias, "));
    }

    // The RefIn- or RtdIn- pin is < 0.85 x Vbia
    if (status & (RTD_FAULT_REFIN_LOW_OPEN | RTD_FAULT_RTDIN_LOW_OPEN))
    {
      Serial.print(F("FORCE- open, "));
    }

    // The measured voltage at the RTD sense pins is too high or two low
    if (status & RTD_FAULT_VOLTAGE_OOR)
    {
      Serial.print(F("Voltage out of range fault, "));
    }
  }

  Serial.println();
}