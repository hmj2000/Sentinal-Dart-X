#include <Arduino.h>

// motor 1 pins
#define EN 13
#define DIR 12
#define PUL 14

// motor 2 pins
#define EN2 27
#define DIR2 26
#define PUL2 25

#define GUN 23
#define FIRE_RATE_MS 1000

#define SPEED 700
#define SPEED_REDUCTION 3

// Task handles
TaskHandle_t Task1;
TaskHandle_t Task2;

void roam()
{
    tone(PUL, SPEED/SPEED_REDUCTION);
    tone(PUL2, SPEED/SPEED_REDUCTION);
    digitalWrite(EN, LOW);
    digitalWrite(DIR, LOW);
    digitalWrite(EN2, LOW);
    digitalWrite(DIR2, LOW);
}


void Task1MotorController(void * parameter)
{
    pinMode(EN, OUTPUT);
    pinMode(DIR, OUTPUT);
    pinMode(PUL, OUTPUT);

    pinMode(EN2, OUTPUT);
    pinMode(DIR2, OUTPUT);
    pinMode(PUL2, OUTPUT);

    pinMode(GUN, OUTPUT);
    digitalWrite(GUN, HIGH);

    int firelock = 0;

    while (1)
    {
        if (Serial.available())
        {
            char input = Serial.read(); // Read serial input

            // go backwards
            if (input == 'w')
            {
                tone(PUL, SPEED);
                tone(PUL2, SPEED);
                digitalWrite(EN, LOW);
                digitalWrite(DIR, HIGH);
                digitalWrite(EN2, LOW);
                digitalWrite(DIR2, LOW);
                firelock = 0;
            }
            // turn left
            else if (input == 'd')
            {
                tone(PUL, SPEED/SPEED_REDUCTION);
                tone(PUL2, SPEED/SPEED_REDUCTION);
                digitalWrite(EN, LOW);
                digitalWrite(DIR, HIGH);
                digitalWrite(EN2, LOW);
                digitalWrite(DIR2, HIGH);
                firelock = 0;
            }
            // turn right
            else if (input == 'a')
            {
                tone(PUL, SPEED/SPEED_REDUCTION);
                tone(PUL2, SPEED/SPEED_REDUCTION);
                digitalWrite(EN, LOW);
                digitalWrite(DIR, LOW);
                digitalWrite(EN2, LOW);
                digitalWrite(DIR2, LOW);
                firelock = 0;
            }
            // go forwards
            else if (input == 's')
            {

                tone(PUL, SPEED);
                tone(PUL2, SPEED);
                digitalWrite(EN, LOW);
                digitalWrite(DIR, LOW);
                digitalWrite(EN2, LOW);
                digitalWrite(DIR2, HIGH);
                firelock = 0;
            }
            // firing the gun
            else if (input == 'f' && firelock == 0)
            {
                firelock = 1;
                digitalWrite(EN, HIGH);
                digitalWrite(EN2, HIGH);
                digitalWrite(GUN, LOW);
                vTaskDelay( FIRE_RATE_MS / portTICK_PERIOD_MS);
                digitalWrite(GUN, HIGH);
            }
            // roam
            else if (input == 'r')
            {
                roam();
                firelock = 0;
            }
            // stop
            else if (input == 'q')
            {
                digitalWrite(EN, HIGH);
                digitalWrite(EN2, HIGH);
                firelock = 0;
            }
            // stop
            else
            {
                digitalWrite(EN, HIGH);
                digitalWrite(EN2, HIGH);
            }
        }

        vTaskDelay(10 / portTICK_PERIOD_MS); //gives the task some delay

    }

}

void Task2ReadSensor(void * parameter)
{

//    Serial.println("Reading Sensor Data");

}


void setup()
{

    Serial.begin(9600);
    Serial.println("<Arduino is ready>");

    // Motor Controller with stack 1000 pin to core 0
    xTaskCreatePinnedToCore(Task1MotorController, "Task1MotorController", 1000, NULL, 1, &Task1, 0);
    // Read Sensor with stack 1000 pin to core 1
    //xTaskCreatePinnedToCore(Task2ReadSensor, "Task2ReadSensor", 1000, NULL, 1, &Task2, 1);
}

void loop()
{
    //tasks are hendled by RTOS

}
