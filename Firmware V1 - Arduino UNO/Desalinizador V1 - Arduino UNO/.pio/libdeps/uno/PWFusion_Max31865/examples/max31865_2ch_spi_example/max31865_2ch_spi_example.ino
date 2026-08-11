/***************************************************************************
* File Name: max31865_2ch_spi_example.ino
* Processor/Platform: Playing With Fusion R3aktor M0 (tested)
* Development Environment: Arduino 1.8.13
*
* Designed for use with with Playing With Fusion MAX31865 Resistance
* Temperature Device (RTD) breakout board: SEN-30202 (PT100 or PT1000)
*   ---> http://playingwithfusion.com/productview.php?pdid=25
*   ---> http://playingwithfusion.com/productview.php?pdid=26
*
* Copyright © 2014 Playing With Fusion, Inc.
* SOFTWARE LICENSE AGREEMENT: This code is released under the MIT License. 
* 
* Permission is hereby granted, free of charge, to any person obtaining a
* copy of this software and associated documentation files (the "Software"),
* to deal in the Software without restriction, including without limitation
* the rights to use, copy, modify, merge, publish, distribute, sublicense,
* and/or sell copies of the Software, and to permit persons to whom the
* Software is furnished to do so, subject to the following conditions:
* 
* The above copyright notice and this permission notice shall be included in
* all copies or substantial portions of the Software.
* 
* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
* IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
* FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
* AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
* LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
* FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
* DEALINGS IN THE SOFTWARE.
* **************************************************************************
* REVISION HISTORY:
* Author                        Date            Comments
* J. Steinlage                  2014Feb17       Original version
* J. Steinlage                  2014Aug07       Reduced SPI clock to 1MHz - fixed occasional missing bit
*                                               Fixed temp calc to give only unsigned resistance values
*                                               Removed unused #defines for chip config (they're hard coded) 
* J. Leonard                    2021Mar19       Updated to object-oriented MAX31865 library
*
* Playing With Fusion, Inc. invests time and resources developing open-source
* code. Please support Playing With Fusion and continued open-source 
* development by buying products from Playing With Fusion!
*
* **************************************************************************
* ADDITIONAL NOTES:
* This file configures then runs a program on PwFusion R3aktor to read a
* dual channel MAX31865 RTD-to-digital converter breakout board and print results
* to a serial port. Communication is via SPI built-in library.
*    - Configure Arduino Uno or PwFusion R3aktor
*    - Configure and read resistances and statuses from MAX31865 IC 
*      - Write config registers (MAX31865 starts up in a low-power state)
*      - RTD resistance register
*      - High and low status thresholds 
*      - Fault statuses
*    - Write formatted information to serial port
*  Circuit:
*    Arduino Uno   Arduino Mega   R3aktor M0      -->  SEN-30202
*    CS0:  pin  9  CS0:  pin  9   CS0: pin D9     -->  CS, CH0
*    CS1:  pin 10  CS1:  pin 10   CS0: pin D10    -->  CS, CH1
*    MOSI: pin 11  MOSI: pin 51   MOSI: pin MOSI  -->  SDI (must not be changed for hardware SPI)
*    MISO: pin 12  MISO: pin 50   MISO: pin MISO  -->  SDO (must not be changed for hardware SPI)
*    SCK:  pin 13  SCK:  pin 52   SCK:  pin SCK   -->  SCLK (must not be changed for hardware SPI)
*    GND           GND            GND             -->  GND
*    5V            5V             3.3V            -->  Vin (supply with same voltage as Arduino I/O, 5V or 3.3V)
***************************************************************************/

// the sensor communicates using SPI, so include the hardware SPI library:
#include <SPI.h>
// include Playing With Fusion MAX31865 library
#include <PwFusion_MAX31865.h> 

// CS pin used for the connection with the sensor
// other connections are controlled by the SPI library)
const int CS0_PIN = 9;
const int CS1_PIN = 10;

// Create instance of MAX31865 class
MAX31865 rtd0;
MAX31865 rtd1;

void setup() {
  Serial.begin(115200);
  Serial.println(F("Boot"));

  // setup for the the SPI library:
  SPI.begin();
  
  // initalize the chip select pin
  pinMode(CS0_PIN, OUTPUT);
  pinMode(CS1_PIN, OUTPUT);

  // configure rtd sensor channel 0
  rtd0.begin(CS0_PIN, RTD_3_WIRE, RTD_TYPE_PT100);

  // configure rtd sensor channel 1
  rtd1.begin(CS1_PIN, RTD_3_WIRE, RTD_TYPE_PT100);

  Serial.println(F("MAX31865 Configured"));
  
  // give the sensor time to set up
  delay(100);
}


void loop() 
{
  // Get the latest temperature and status values from the MAX31865
  rtd0.sample();
  rtd1.sample();
  
  // ******************** Print RTD 0 Information ********************
  Serial.println("RTD Sensor 0:");            // Print RTD0 header
  Serial.print("Resistance = ");                    // print RTD resistance heading
  Serial.print(rtd0.getResistance());                          // print RTD resistance
  Serial.println(" ohm");
  
  Serial.print("Temperature = ");                    // print RTD temperature heading
  Serial.print(rtd0.getTemperature());                          // print RTD resistance
  Serial.println(" deg C");                   // print RTD temperature heading
    
  // Print the Status bitmask
  Serial.print("Fault Status = ");
  PrintRTDStatus(rtd0.getStatus());
  Serial.println();
  
  
  // ******************** Print RTD 1 Information ********************
  Serial.println("RTD Sensor 1:");            // Print RTD0 header
  Serial.print("Resistance = ");                    // print RTD resistance heading
  Serial.print(rtd1.getResistance());                          // print RTD resistance
  Serial.println(" ohm");
  
  Serial.print("Temperature = ");                    // print RTD temperature heading
  Serial.print(rtd1.getTemperature());                          // print RTD resistance
  Serial.println(" deg C");                   // print RTD temperature heading
    
  // Print the Status bitmask
  Serial.print("Fault Status = ");
  PrintRTDStatus(rtd1.getStatus());
  Serial.println();
  Serial.println();
  
  
  // 500ms delay... can be much faster
  delay(500);    
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

