#include <Arduino.h>  // Include the Arduino library for serial communication & GPIO control

// Define serial baud rate (communication speed)
#define BAUD_RATE 115200  // 115200 bits per second (fast and reliable for ESP32)

// Define GPIO pins for motors and Nerf gun
#define MOTOR_LEFT_PIN 5   // Left motor control pin (TBD)
#define MOTOR_RIGHT_PIN 6  // Right motor control pin (TBD)
#define GUN_TRIGGER_PIN 7  // Nerf gun trigger control pin (TBD)

// Structure representing the command packet received from Raspberry Pi
struct CommandPacket 
{
    uint8_t commandNumber;  // 8-bit unsigned integer for command ID
    uint16_t units;         // 16-bit unsigned integer for command parameter (e.g., speed)
    uint8_t terminator;     // Should always be '\n' (marks end of a valid packet)
};


//Function to process received command that executes appropriate actions based on command number

void processCommand(const CommandPacket& cmd) 
{
    // Debugging: Print received command and parameter value
    Serial.print("Received Command: ");
    Serial.print(cmd.commandNumber);
    Serial.print(" | Units: ");
    Serial.println(cmd.units);

    switch (cmd.commandNumber) 
    {
        case 0: // Stop Everything
            Serial.println("Executing: STOP EVERYTHING");
            digitalWrite(MOTOR_LEFT_PIN, LOW);   // Turn off left motor
            digitalWrite(MOTOR_RIGHT_PIN, LOW);  // Turn off right motor
            digitalWrite(GUN_TRIGGER_PIN, LOW);  // Turn off Nerf gun
            break;

        case 1: // Toggle Nerf Gun
            if (cmd.units == 1)  // If '1', fire the gun
            {  
                Serial.println("Executing: FIRE GUN");
                digitalWrite(GUN_TRIGGER_PIN, HIGH);
            } 
            
            else // If '0', stop firing
            {  
                Serial.println("Executing: STOP FIRING");
                digitalWrite(GUN_TRIGGER_PIN, LOW);
            }
            break;

        case 2: // Set Left Stepper Motor speed
            {
                int velocity = cmd.units - 32768; // Convert unsigned to signed velocity
                Serial.print("Executing: SET LEFT STEPPER at velocity ");
                Serial.println(velocity);

                if (velocity == 0) 
                {
                    digitalWrite(MOTOR_LEFT_PIN, LOW);
                } 
                
                else 
                {
                    digitalWrite(MOTOR_LEFT_PIN, HIGH);
                    delay(500);  // Simulated movement
                    digitalWrite(MOTOR_LEFT_PIN, LOW);
                }
            }
            break;

        case 3: // Set Right Stepper Motor speed
            {
                int velocity = cmd.units - 32768; // Convert unsigned to signed velocity
                Serial.print("Executing: SET RIGHT STEPPER at velocity ");
                Serial.println(velocity);

                if (velocity == 0) 
                {
                    digitalWrite(MOTOR_RIGHT_PIN, LOW);
                } 
                
                else {
                    digitalWrite(MOTOR_RIGHT_PIN, HIGH);
                    delay(500);  // Simulated movement
                    digitalWrite(MOTOR_RIGHT_PIN, LOW);
                }
            }
            break;

        default: // Handle unknown commands
            Serial.println("ERROR: Unknown Command Received!");
            break;
    }
}


// Function to read and parse a command packet from serial and returns true if a valid packet is received, false otherwise.

bool readCommandPacket(CommandPacket& cmd) 
{
    if (Serial.available() >= sizeof(CommandPacket)) // Ensure we have enough data
    {  
        Serial.readBytes(reinterpret_cast<uint8_t*>(&cmd), sizeof(CommandPacket));  // Read into struct
        
        if (cmd.terminator == '\n') // Validate termination character
        {  
            return true;  // Valid command received
        } 
        
        else 
        {
            Serial.println("ERROR: Invalid packet format!");  // Debugging message
            return false;
        }
    }
    return false;  // Not enough data received yet
}


// Setup function: Runs once at startup that initializes serial communication and configures GPIO pins
void setup() 
{
    Serial.begin(BAUD_RATE);  // Initialize serial communication with defined baud rate
    pinMode(MOTOR_LEFT_PIN, OUTPUT);   // Configure left motor pin as output
    pinMode(MOTOR_RIGHT_PIN, OUTPUT);  // Configure right motor pin as output
    pinMode(GUN_TRIGGER_PIN, OUTPUT);  // Configure Nerf gun pin as output

    Serial.println("ESP32 Ready to Receive Binary Commands from Raspberry Pi.");
}

// Main loop: Continuously checks for and processes incoming commands

void loop() 
{
    CommandPacket cmd;
    if (readCommandPacket(cmd)) // Check if a valid command is received
    {  
        processCommand(cmd);       // Execute the corresponding action
    }
}






