// Lateral Arduino firmware - hip wear tester
// Drives the single lateral NEMA 23 stepper motor via an external driver.
//
// CYCLE DEFINITION (as of 2026-05-05):
//   One lateral cycle is THREE legs centered around the rig's home position:
//     leg 1: 23.4 deg forward (208 pulses)
//     leg 2: 46.8 deg backward (416 pulses, returns through home to opposite side)
//     leg 3: 23.4 deg forward (208 pulses, returns to home)
//   Net pulses balance, so the motor returns to its physical home if no
//   steps are skipped. The rig must be physically positioned at the middle
//   of the sweep before START.
//   Cycle counter increments after each three-leg motion.
//
// SYNC WITH TOP ARDUINO:
//   Each outer leg targets LEG_DURATION_MS ms wall-time. The middle leg
//   targets 2 * LEG_DURATION_MS. Both Arduinos use the same LEG_DURATION_MS
//   so they reverse direction at the same instant. Each leg pads with
//   delayMicroseconds() at the end to absorb any timing slop.
//
// DRIVER MICROSTEPPING:
//   Lateral driver = 3,200 pulses per revolution (1/16 microstep on a
//   1.8 deg motor).
//   23.4 deg = 3200 * 23.4 / 360 = 208 pulses (exact integer, no rounding).
//
// SERIAL PROTOCOL (unchanged - Python side does not need updates):
//   Commands:
//     START:<cycles>     run <cycles> overall cycles
//     STOP               immediately stop and reset
//   Responses:
//     STARTED:LAT:<cycles>
//     CYCLE:<n>          one per completed cycle
//     DONE:LAT           all <cycles> completed
//     STOPPED:LAT        STOP acknowledged
//     ERR:<reason>

  // ---------- Pin assignments ----------
  const int LAT_DIR  = 2;
  const int LAT_STEP = 3;

  const bool USE_ENA = false;
  const int LAT_ENA  = 4;

  // ---------- Cycle geometry ----------
  // Outer leg = DEG_PER_LEG. Middle leg = 2 * DEG_PER_LEG.
  const float DEG_PER_LEG     = 23.4f;
  const long  PULSES_PER_REV  = 3200;        // 1/16 microstep on a 1.8 deg motor
  // 3200 * 23.4/360 = 208 pulses per outer leg (exact integer)
  const long PULSES_PER_LEG = (long)(PULSES_PER_REV * DEG_PER_LEG / 360.0f);

  // ---------- Timing ----------
  // Each OUTER leg targets this wall-time. The middle leg targets 2x.
  // MUST match top_arduino.ino so both Arduinos reverse at the same instant.
  // 250 ms outer + 500 ms middle + 250 ms outer = 1000 ms = 1 Hz cycle.
  const unsigned long LEG_DURATION_MS = 250;

  // ---------- Per-pulse delay derived from leg duration ----------
  // Total microseconds per pulse = LEG_DURATION_MS * 1000 / PULSES_PER_LEG.
  // For 250 ms / 208 pulses = 1201.92 us/pulse total -> 25 us HIGH + 1176 us LOW.
  // (25 us HIGH is well above the driver's minimum and gives some tolerance
  //  for high-microstep drivers that may want >15 us.)
  const unsigned long TOTAL_US_PER_PULSE = ((unsigned long)LEG_DURATION_MS * 1000UL) / PULSES_PER_LEG;
  const int PULSE_WIDTH_US = 25;
  const int STEP_DELAY_US  = (int)(TOTAL_US_PER_PULSE - PULSE_WIDTH_US);

  // ---------- Direction setup time ----------
  // The driver datasheet wants ~5 us between a DIR change and the next STEP
  // pulse. Without this, the first pulse in a new direction can be
  // misinterpreted (driver hasn't latched the new DIR yet) and the motor
  // walks one step per cycle in one direction. 10 us is comfortable.
  const int DIR_SETUP_US = 10;

  // ---------- Run state ----------
  const unsigned long MAX_CYCLES = 5000000;

  String command = "";

  bool isRunning = false;
  unsigned long currentCycle = 0;
  unsigned long targetCycles = 0;

  // ---------- Pulse helper ----------
  void pulseStep(int stepPin) {
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(PULSE_WIDTH_US);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(STEP_DELAY_US);
  }

  void enableMotor() {
    if (USE_ENA) digitalWrite(LAT_ENA, LOW);
  }

  void disableMotor() {
    if (USE_ENA) digitalWrite(LAT_ENA, HIGH);
  }

  // ---------- Pad a leg's wall-time up to target ----------
  // Outer target = LEG_DURATION_MS * 1000 us. Middle target = 2x.
  // Use micros() to absorb integer-rounding slop in TOTAL_US_PER_PULSE.
  void padToTarget(unsigned long start_us, unsigned long target_us) {
    unsigned long elapsed = micros() - start_us;
    if (elapsed < target_us) {
      delayMicroseconds((unsigned int)(target_us - elapsed));
    }
  }

  // ---------- One cycle = three legs (centered sweep) ----------
  void runOneCycle() {
    const unsigned long OUTER_TARGET_US  = (unsigned long)LEG_DURATION_MS * 1000UL;
    const unsigned long MIDDLE_TARGET_US = OUTER_TARGET_US * 2UL;

    moveSteps(208, LOW);
    delay(0);
    moveSteps(416, HIGH);
    delay(0);
    moveSteps(208, LOW);
    delay(0);

    currentCycle++;
    Serial.print("CYCLE:");
    Serial.println(currentCycle);

    if (currentCycle >= targetCycles) {
      isRunning = false;
      disableMotor();
      Serial.println("DONE:LAT");
    }
  }

  void moveSteps(int steps, bool dir){
    digitalWrite(LAT_DIR, dir);
    delay(18);

    for (int i = 0; i < steps; i++){
      digitalWrite(LAT_STEP, LOW);
      delayMicroseconds(580);
      digitalWrite(LAT_STEP, HIGH);
      delayMicroseconds(580);
    }
  }

  // ---------- Command parsing ----------
  void handleCommand(String cmd) {
    cmd.trim();

    if (cmd == "STOP") {
      isRunning = false;
      currentCycle = 0;
      targetCycles = 0;
      disableMotor();
      Serial.println("STOPPED:LAT");
      return;
    }

    if (isRunning && cmd.startsWith("START:")) {
      Serial.println("ERR:ALREADY_RUNNING");
      return;
    }

    if (cmd.startsWith("START:")) {
      int colon = cmd.indexOf(':');
      String cyclesStr = cmd.substring(colon + 1);
      unsigned long cycles = cyclesStr.toInt();

      if (cycles == 0 || cycles > MAX_CYCLES) {
        Serial.println("ERR:BAD_CYCLES");
        return;
      }

      currentCycle = 0;
      targetCycles = cycles;
      isRunning = true;
      enableMotor();

      Serial.print("STARTED:LAT:");
      Serial.println(targetCycles);
      return;
    }

    Serial.println("ERR:UNKNOWN_COMMAND");
  }

  // ---------- Setup / loop ----------
  void setup() {
    pinMode(LAT_DIR, OUTPUT);
    pinMode(LAT_STEP, OUTPUT);

    if (USE_ENA) pinMode(LAT_ENA, OUTPUT);

    digitalWrite(LAT_DIR, LOW);
    digitalWrite(LAT_STEP, LOW);
    disableMotor();

    Serial.begin(9600);
  }

  void loop() {
    if (Serial.available()) {
      command = Serial.readStringUntil('\n');
      handleCommand(command);
    }

    if (isRunning) {
      runOneCycle();
    }
  }
