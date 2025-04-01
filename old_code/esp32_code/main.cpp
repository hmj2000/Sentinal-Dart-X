#include <Arduino.h>
#include <stdint.h>

#define LEFT_PULSE_PIN 14
#define LEFT_DIRECTION_PIN 12
#define LEFT_ENABLE_PIN 13

#define RIGHT_PULSE_PIN 25
#define RIGHT_DIRECTION_PIN 26
#define RIGHT_ENABLE_PIN 27

struct command {
    uint8_t command;
    uint8_t parameter;
    uint8_t newline;
};

void read_command(struct command * cmd) {
    Serial.readBytes((char *)cmd, 3);
    return;
}

void stop_everything(struct command * cmd) {
    //Does nothing right now
    return;
}

void toggle_nerf_gun(struct command * cmd) {
    //Does nothing right now
    return;
}

//USE RISING EDGE MODE FOR THE MOTORS, PLEASE CONFIGURE THIS CORRECTLY
void pulse_motor(struct command * cmd) {
    switch (cmd->parameter) {
        case 0x00:
            //Set Forward Direction
            digitalWrite(LEFT_DIRECTION_PIN, HIGH);
            delayMicroseconds(5);
            //Pulse
            digitalWrite(LEFT_PULSE_PIN, LOW);
            delayMicroseconds(3);
            digitalWrite(LEFT_PULSE_PIN, HIGH); 

        break;
        case 0x01:
            //Set Backward Direction
            digitalWrite(LEFT_DIRECTION_PIN, LOW);
            delayMicroseconds(5);
            //Pulse
            digitalWrite(LEFT_PULSE_PIN, LOW);
            delayMicroseconds(3);
            digitalWrite(LEFT_PULSE_PIN, HIGH); 

        break;
        case 0x02:
            //Set Forward Direction
            digitalWrite(RIGHT_DIRECTION_PIN, HIGH);
            delayMicroseconds(5);
            //Pulse
            digitalWrite(RIGHT_PULSE_PIN, LOW);
            delayMicroseconds(3);
            digitalWrite(RIGHT_PULSE_PIN, HIGH); 

        break;
        case 0x03:
            //Set Backward Direction
            digitalWrite(RIGHT_DIRECTION_PIN, LOW);
            delayMicroseconds(5);
            //Pulse
            digitalWrite(RIGHT_PULSE_PIN, LOW);
            delayMicroseconds(3);
            digitalWrite(RIGHT_PULSE_PIN, HIGH); 

        break;
    }
}

void exec_command(struct command * cmd) {
    switch(cmd->command) {
        case 0x00:
            stop_everything(cmd);
        break;
        case 0x01:
            toggle_nerf_gun(cmd); 
        break;
        case 0x02:
            pulse_motor(cmd);
        break;
    }
}

void setup()
{
    Serial.begin(115200);
    pinMode(LEFT_ENABLE_PIN, OUTPUT);
    pinMode(RIGHT_ENABLE_PIN, OUTPUT);
    digitalWrite(LEFT_ENABLE_PIN, LOW);
    digitalWrite(RIGHT_ENABLE_PIN, LOW);

    pinMode(LEFT_PULSE_PIN, OUTPUT);
    pinMode(RIGHT_PULSE_PIN, OUTPUT);
    digitalWrite(LEFT_PULSE_PIN, HIGH);
    digitalWrite(RIGHT_PULSE_PIN, HIGH);

    pinMode(LEFT_DIRECTION_PIN, OUTPUT);
    pinMode(RIGHT_DIRECTION_PIN, OUTPUT);
    digitalWrite(LEFT_DIRECTION_PIN, HIGH);
    digitalWrite(RIGHT_DIRECTION_PIN, HIGH);
}

void loop()
{
    struct command cmd;
    
    while(1) {
       if (Serial.available() >= 3) {
            read_command(&cmd);
            exec_command(&cmd);       
       }
    }
}
