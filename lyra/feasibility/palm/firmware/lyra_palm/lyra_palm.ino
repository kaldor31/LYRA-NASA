/*
  LYRA — прошивка станции ладони (ESP32 DevKit, Arduino IDE).

  Библиотеки (Arduino Library Manager):
    • "SparkFun MAX3010x Pulse and Proximity Sensor Library"  — MAX30102 (пульс, SpO2)
    • "Adafruit MLX90614 Library"                              — ИК-термометр
    • "HX711" (Bogdan Necula)                                  — тензодатчик хвата

  Подключение — docs/drawings/wiring.svg:
    I2C: SDA=GPIO21, SCL=GPIO22 (MAX30102 0x57, MLX90614 0x5A), питание 3V3
    HX711: DT=GPIO16, SCK=GPIO4

  Вывод в Serial 115200, одна JSON-строка в секунду:
    {"finger":1,"hr":72,"hr_ok":1,"spo2":98,"spo2_ok":1,"temp":33.21,"grip":0.12}
  Команды из Serial: 't' — обнулить тензодатчик (рукоять не трогать).

  Калибровка хвата: положите груз известной массы (напр. 5 кг), посмотрите сырое
  значение и подберите GRIP_CAL так, чтобы "grip" показывал 5.0.
*/
#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"
#include <Adafruit_MLX90614.h>
#include "HX711.h"

const int PIN_SDA = 21, PIN_SCL = 22;
const int HX_DT = 16, HX_SCK = 4;
const int LED_PIN = 2;
float GRIP_CAL = 21000.0;          // единиц АЦП на 1 кг — подобрать калибровкой
const uint32_t FINGER_IR = 50000;  // ниже — пальца на датчике нет

MAX30105 ppg;
Adafruit_MLX90614 mlx;
HX711 scale;

const int32_t BUF = 100;           // 4 секунды при 25 отсчётах/с
uint32_t irBuf[BUF], redBuf[BUF];
bool ppgOk = false, mlxOk = false;

void readSample(int i) {
  while (!ppg.available()) ppg.check();
  redBuf[i] = ppg.getRed();
  irBuf[i] = ppg.getIR();
  ppg.nextSample();
}

void printNum(const char* key, float v, bool ok, int digits) {
  Serial.print("\""); Serial.print(key); Serial.print("\":");
  if (ok && !isnan(v)) Serial.print(v, digits); else Serial.print("null");
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  Wire.begin(PIN_SDA, PIN_SCL);

  ppgOk = ppg.begin(Wire, I2C_SPEED_FAST);
  if (ppgOk) {
    // яркость LED, усреднение 4, режим 2 (красный+ИК), 100 Гц → 25 отсч/с после усреднения,
    // ширина импульса 411 мкс, диапазон АЦП 4096
    ppg.setup(60, 4, 2, 100, 411, 4096);
    for (int i = 0; i < BUF; i++) readSample(i);
  }
  mlxOk = mlx.begin();
  scale.begin(HX_DT, HX_SCK);
  scale.set_scale(GRIP_CAL);
  scale.tare(20);

  Serial.print("{\"boot\":1,\"ppg\":"); Serial.print(ppgOk);
  Serial.print(",\"mlx\":"); Serial.print(mlxOk); Serial.println("}");
}

void loop() {
  if (Serial.available() && Serial.read() == 't') scale.tare(20);

  int32_t spo2 = 0, hr = 0;
  int8_t spo2Ok = 0, hrOk = 0;
  bool finger = false;

  if (ppgOk) {
    // сдвигаем окно на 25 отсчётов (1 секунда) и дочитываем новые
    for (int i = 25; i < BUF; i++) { redBuf[i - 25] = redBuf[i]; irBuf[i - 25] = irBuf[i]; }
    for (int i = 75; i < BUF; i++) readSample(i);
    finger = irBuf[BUF - 1] > FINGER_IR;
    if (finger) {
      maxim_heart_rate_and_oxygen_saturation(irBuf, BUF, redBuf, &spo2, &spo2Ok, &hr, &hrOk);
    }
  } else {
    delay(1000);
  }

  float temp = mlxOk ? mlx.readObjectTempC() : NAN;
  float grip = scale.is_ready() ? scale.get_units(3) : NAN;

  digitalWrite(LED_PIN, finger ? HIGH : LOW);

  Serial.print("{\"finger\":"); Serial.print(finger ? 1 : 0); Serial.print(",");
  printNum("hr", hr, finger && hrOk, 0);     Serial.print(",\"hr_ok\":"); Serial.print(finger && hrOk ? 1 : 0); Serial.print(",");
  printNum("spo2", spo2, finger && spo2Ok, 0); Serial.print(",\"spo2_ok\":"); Serial.print(finger && spo2Ok ? 1 : 0); Serial.print(",");
  printNum("temp", temp, mlxOk, 2);          Serial.print(",");
  printNum("grip", grip, true, 2);
  Serial.println("}");
}
