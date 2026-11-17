#pragma once
#include <Arduino.h>
#include <math.h>

// Recibe valores ya convertidos y calibrados. NAN omite un sensor sin lectura válida.
// No asigna pines, no lee el ADC y no genera valores de demostración.
inline bool enviarSensores(Stream &salida, float presion103Bar, float presion106Bar,
                          float caudal136LMin, float temperatura120C) {
  const int piezas[] = {103, 106, 136, 120};
  const float valores[] = {presion103Bar, presion106Bar, caudal136LMin, temperatura120C};
  const char *unidades[] = {"bar", "bar", "L/min", "\\u00b0C"};
  bool alguno = false;
  for (int i = 0; i < 4; ++i) alguno |= isfinite(valores[i]);
  if (!alguno) return false;
  salida.print(F("{\"lecturas\":["));
  bool primero = true;
  for (int i = 0; i < 4; ++i) {
    if (!isfinite(valores[i])) continue;
    if (!primero) salida.print(',');
    primero = false;
    salida.print(F("{\"pieza\":")); salida.print(piezas[i]);
    salida.print(F(",\"valor\":")); salida.print(valores[i], 3);
    salida.print(F(",\"unidad\":\"")); salida.print(unidades[i]); salida.print(F("\"}"));
  }
  salida.println(F("]}"));
  return true;
}
