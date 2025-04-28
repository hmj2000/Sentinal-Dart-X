#include <Arduino.h>

// MOTOR CONFIG
// Motor 1 pins
#define EN 23
#define DIR 4
#define PUL 5

// Motor 2 pins
#define EN2 27
#define DIR2 26
#define PUL2 25

// GUN CONFIG
#define GUN 33
#define FIRE_RATE_MS 1000

// ROBOT CONFIG
#define SPEED 750
#define SPEED_REDUCTION 1

// SENSOR CONFIG
#define TRIG_PIN {17, 18, 19, 21, 22}
#define ECHO_PIN {16, 34, 35, 36, 39}
#define WALL_LIMIT 4000

char motion = 'f';
char old_motion = 'a';
char roam_en = '0';


// Task Handles
TaskHandle_t Task1;
TaskHandle_t Task2;

//////////////////////////////////////////////////////////////////////
////////////////////// ULTRASONIC ////////////////////////////////////
//////////////////////////////////////////////////////////////////////
volatile unsigned long echo_init[] = {0,0,0,0,0};
volatile unsigned long echo_time[] = {0,0,0,0,0};

// ultra_trig fires all of the ultrasonic sensors
void ultra_trig()
{
    char pins[] = TRIG_PIN;
    for (char i = 0; i < 5; i++)
    {
        digitalWrite(pins[i], HIGH);
        delayMicroseconds(10);
        digitalWrite(pins[i], LOW);
    }
}

// echo_handler calculates the time difference when the echo
// is recieved
void echo_handler(char index)
{
    char pins[] = ECHO_PIN;
    switch (digitalRead(pins[index]))
    {
      case HIGH:
          echo_init[index] = micros();
          break;
      case LOW:
          echo_time[index] = micros() - echo_init[index];
          //is_echos[index] = 1;
          break;
    }
}

void pindex0ISR() {echo_handler(0);}

void pindex1ISR() {echo_handler(1);}

void pindex2ISR() {echo_handler(2);}

void pindex3ISR() {echo_handler(3);}

void pindex4ISR() {echo_handler(4);}

char init_ultrasonic()
{
    char e_pins[] = ECHO_PIN;
    char t_pins[] = TRIG_PIN;

    for (char e_pin : e_pins)
    {
        pinMode(e_pin, INPUT);
    }

    attachInterrupt(e_pins[0], pindex0ISR, CHANGE);
    attachInterrupt(e_pins[1], pindex1ISR, CHANGE);
    attachInterrupt(e_pins[2], pindex2ISR, CHANGE);
    attachInterrupt(e_pins[3], pindex3ISR, CHANGE);
    attachInterrupt(e_pins[4], pindex4ISR, CHANGE);

    for (char t_pin : t_pins)
    {
        pinMode(t_pin, OUTPUT);
        digitalWrite(t_pin, LOW);
    }

    return 0;
}

void roam(char motion)
{

    tone(PUL, SPEED/SPEED_REDUCTION);
    tone(PUL2, SPEED/SPEED_REDUCTION);
    digitalWrite(EN, LOW);
    digitalWrite(EN2, LOW);

    switch (motion) {
        case 'f':
            // Forward motion logic
            //Serial.println("Moving Forward");
            //tone(PUL, SPEED/SPEED_REDUCTION);
            //tone(PUL2, SPEED/SPEED_REDUCTION);
            //digitalWrite(EN, LOW);
            digitalWrite(DIR, HIGH);
            //digitalWrite(EN2, LOW);
            digitalWrite(DIR2, LOW);
            //firelock = 0;
            break;
        case 'l':
            // Right turn logic
            //tone(PUL, SPEED/SPEED_REDUCTION);
            //tone(PUL2, SPEED/SPEED_REDUCTION);
            //digitalWrite(EN, LOW);
            digitalWrite(DIR, HIGH);
            //digitalWrite(EN2, LOW);
            digitalWrite(DIR2, HIGH);
            //firelock = 0;
            break;
        case 'r':
            // Left turn logic
            //tone(PUL, SPEED/SPEED_REDUCTION);
            //tone(PUL2, SPEED/SPEED_REDUCTION);
            //digitalWrite(EN, LOW);
            digitalWrite(DIR, LOW);
            //digitalWrite(EN2, LOW);
            digitalWrite(DIR2, LOW);
            //firelock = 0;
            break;
        default:
            // Optional: handle unknown motion
            Serial.println("Unknown motion");
            break;
    }
}

void Task2ReadSensor(void * parameter)
{
    //char motion = 'f';
    init_ultrasonic();

    while (1)
    {
        int a = echo_time[0];
        int b = echo_time[1];
        int c = echo_time[2];
        int d = echo_time[3];
        int e = echo_time[4];

        int center = c;
        int left = a + b / 2;
        int right = d + e / 2;

        if (center < WALL_LIMIT)
        {
            if (left < right)
            {
                motion = 'r';
            } else
            {
                motion = 'r';
            }
        } else
        {
            motion = 'f';
        }

//        Serial.println(a);

        ultra_trig();

        vTaskDelay(10 / portTICK_PERIOD_MS); //gives the task some delay
    }
}

//////////////////////////////////////////////////////////////////////
////////////////////// Robot /////////////////////////////////////////
//////////////////////////////////////////////////////////////////////


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
    char lastChar = '\0';

    while (1)
    {

//        Serial.println(motion);

        if (Serial.available())
        {
            char input = Serial.read(); // Read serial input
            Serial.flush();
            // go backwards
            if (input == 'w' && input != lastChar)
            {
                roam_en = '0';
                tone(PUL, SPEED);
                tone(PUL2, SPEED);
                digitalWrite(EN, LOW);
                digitalWrite(DIR, HIGH);
                digitalWrite(EN2, LOW);
                digitalWrite(DIR2, LOW);
                firelock = 0;
                lastChar = input;
            }
            // turn left
            else if (input == 'd' && input != lastChar)
            {
                roam_en = '0';
                tone(PUL, SPEED/SPEED_REDUCTION);
                tone(PUL2, SPEED/SPEED_REDUCTION);
                digitalWrite(EN, LOW);
                digitalWrite(DIR, HIGH);
                digitalWrite(EN2, LOW);
                digitalWrite(DIR2, HIGH);
                firelock = 0;
                lastChar = input;
            }
            // turn right
            else if (input == 'a' && input != lastChar)
            {
                roam_en = '0';
                tone(PUL, SPEED/SPEED_REDUCTION);
                tone(PUL2, SPEED/SPEED_REDUCTION);
                digitalWrite(EN, LOW);
                digitalWrite(DIR, LOW);
                digitalWrite(EN2, LOW);
                digitalWrite(DIR2, LOW);
                firelock = 0;
                lastChar = input;
            }
            // go forwards
            else if (input == 's' && input != lastChar)
            {
                roam_en = '0';
                tone(PUL, SPEED);
                tone(PUL2, SPEED);
                digitalWrite(EN, LOW);
                digitalWrite(DIR, LOW);
                digitalWrite(EN2, LOW);
                digitalWrite(DIR2, HIGH);
                firelock = 0;
                lastChar = input;
            }
            // firing the gun
            else if (input == 'f' && firelock == 0 && input != lastChar)
            {
                roam_en = '0';
                firelock = 1;
                digitalWrite(EN, HIGH);
                digitalWrite(EN2, HIGH);
                digitalWrite(GUN, LOW);
                vTaskDelay( FIRE_RATE_MS / portTICK_PERIOD_MS);
                digitalWrite(GUN, HIGH);
                lastChar = input;
            }
            // roam
            else if (input == 'r' && input != lastChar)
            {
                roam_en = '1';
                //roam(motion);
                firelock = 0;
                lastChar = input;
            }
            // stop
            else if (input == 'q' && input != lastChar)
            {
                roam_en = '0';
                digitalWrite(EN, HIGH);
                digitalWrite(EN2, HIGH);
                firelock = 0;
                lastChar = input;
            }
            // stop
            else if (input != lastChar)
            {
                roam_en = '0';
                digitalWrite(EN, HIGH);
                digitalWrite(EN2, HIGH);
                lastChar = input;
            }
        }

        if (roam_en == '1' && (old_motion != motion))
        {
            old_motion = motion;
            Serial.print(old_motion);
            Serial.print(" ");
            Serial.print(motion);
            Serial.println(" motion changed");
            roam(motion);
            //lastChar = input;
        }

        vTaskDelay(100 / portTICK_PERIOD_MS); //gives the task some delay
        Serial.flush();
    }

}

void setup()
{

    Serial.begin(9600);
    Serial.println("<Arduino is ready>");

    // Motor Controller with stack 1000 pin to core 0
    xTaskCreatePinnedToCore(Task1MotorController, "Task1MotorController", 1000, NULL, 1, &Task1, 0);
    // Read Sensor with stack 1000 pin to core 1
    xTaskCreatePinnedToCore(Task2ReadSensor, "Task2ReadSensor", 1000, NULL, 1, &Task2, 1);
}

void loop() {}
