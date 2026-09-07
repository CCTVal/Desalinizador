#include <Arduino.h>

// MAX31865 uses SPI
#include <SPI.h>
// include Playing With Fusion MAX31865 library
//#include <PwFusion_MAX31865.h>
#include "I2CScanner.h"
#include <Adafruit_MAX31865.h>

// PINs config
//const int CS_PIN_RTD = 10; // Chip select pin for MAX31865
const int interruptPin_pulsecounter = 2;
const int analogPin_presure1 = A0;
const int analogPin_presure2 = A1;

// Use software SPI: CS, DI, DO, CLK
Adafruit_MAX31865 thermo = Adafruit_MAX31865(10, 12, 11, 13);
// use hardware SPI, just pass in the CS pin
//Adafruit_MAX31865 thermo = Adafruit_MAX31865(10);

// The value of the Rref resistor. Use 430.0 for PT100 and 4300.0 for PT1000
#define RREF      4300.0
// The 'nominal' 0-degrees-C resistance of the sensor
// 100.0 for PT100, 1000.0 for PT1000
#define RNOMINAL  1000.0

// Classes 
I2CScanner scanner;
//MAX31865 rtd0;

// handlers 
unsigned long last_millis_sensors = 0;
unsigned long last_millis_print = 0;
unsigned long actual_millis = 0;
volatile unsigned long int pulse_counter = 0;
unsigned long int last_pulses = 0;
unsigned long int diff_pulses = 0;

//Sensor values
int presure1 = 0;
int presure2 = 0;
float I_presure1_out = 0.0;
float I_presure2_out = 0.0;
float Vref = 5.0; // Reference voltage for the ADC on Arduino
float R_med = 200.0; // Resistance of the shunt resistor in oh

// Function definitions
void PrintRTDStatus(uint8_t status);
void IR_pulse_counter();


void setup()
{
    Serial.begin(115200);
    Serial.println(F("Boot"));

    // setup for the the SPI library for max31865
    //SPI.begin();
    // initalize the chip select pin for max31865
    //pinMode(CS_PIN_RTD, OUTPUT);

    // configure pt100 sensor - this can be a macro. I'll do it other day
    //rtd0.begin(CS_PIN_RTD, RTD_3_WIRE, RTD_TYPE_PT1000);
    //rtd0.setLowFaultTemperature(10);  // Set the low fault threshold to 30 degrees C
    //rtd0.setHighFaultTemperature(70); // Set the high fault threshold to 70 degrees C
    
    thermo.begin(MAX31865_3WIRE);  // set to 2WIRE or 4WIRE as necessary
    
    Serial.println(F("MAX31865 Configured"));
    // give the sensor time to set up
    delay(100);

    // Init i2c scanner
    // scanner.Init();

    // Configure interruptions
    pinMode(interruptPin_pulsecounter, INPUT);
    attachInterrupt(digitalPinToInterrupt(interruptPin_pulsecounter), IR_pulse_counter, RISING);
}

void loop()
{
    uint16_t rtd = thermo.readRTD();
    // Get the latest temperature and status values from the MAX31865
    actual_millis = millis();
    if (actual_millis - last_millis_sensors > 200) // measure sensors every 200ms, is it ok? lets see
    {
        last_millis_sensors = actual_millis;
        // rtd0.sample();
        presure1 = analogRead(analogPin_presure1);
        presure2 = analogRead(analogPin_presure2);
    }
    if (actual_millis - last_millis_print > 1000) // Serial print every second with usefull information of sensors
    {
        last_millis_print = actual_millis;
        noInterrupts();
        diff_pulses = pulse_counter;
        pulse_counter = 0;
        I_presure1_out=(Vref*presure1)/(1023.0*R_med)*1000.0; // convert to mA
        I_presure2_out=(Vref*presure2)/(1023.0*R_med)*1000.0; // convert to mA
        interrupts();
        //rtd0.sample();
        Serial.print(diff_pulses);
        Serial.print(";");
        Serial.print(I_presure1_out);
        Serial.print(";");
        Serial.print(presure1);
        Serial.print(";");
        Serial.print(I_presure2_out);
        Serial.print(";");
        Serial.print(presure2);
        Serial.print(";");
        //Serial.println(rtd0.getTemperature());
        Serial.println(thermo.temperature(RNOMINAL, RREF));
    }
}

/*
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
}*/

void IR_pulse_counter()
{
    pulse_counter++;
}