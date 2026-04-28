// Lateral Arduino firmware - hip wear tester
// Drives the single lateral NEMA 23 stepper motor via an external driver.
//
// CYCLE DEFINITION (as of 2026-04-27):
//   One lateral cycle = 23 deg forward + 23 deg backward (one back-and-forth).
//   No inner-rep loop. The cycle counter increments after each back-and-forth.
//
// SYNC WITH TOP ARDUINO:
//   Each leg (forward, backward) takes LEG_DURATION_MS milliseconds. The top
//   firmware uses the same value, so both Arduinos finish their forward leg
//   at the same instant and start their backward leg together.
//   Default: 100 ms per leg -> 200 ms per cycle -> 5 Hz cycle rate.
//
// DRIVER MICROSTEPPING:
//   The lateral driver is set to 25,000 pulses per revolution (a "pulses/rev"
//   labeled DM-style driver, equivalent to 1/125 microstepping on a 1.8 deg
//   step motor).
//   23 deg = 25000 * 23 / 360 = 1597.22 pulses -> rounded to 1597 (overshoots
//   target by 0.003 deg, well below mechanical play in the rig).
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

  // ---------- Pin assignments (unchanged) ----------
  const int LAT_DIR  = 3;
  const int LAT_STEP = 2;

  const bool USE_ENA = false;
  const int LAT_ENA  = 4;

  // ---------- Cycle geometry ----------
  // Change these constants if the angle, driver pulses/rev, or timing changes.
  const float DEG_PER_LEG     = 23.0f;     // degrees per direction (23 forward, 23 back)
  const long  PULSES_PER_REV  = 25000;     // driver "pulses/rev" DIP setting
  // Pulses per direction = pulses_per_rev * (deg / 360)
  // For 23 deg at 25000 P/R: 25000 * 23/360 = 1597.22 -> 1597 pulses
  const long PULSES_PER_LEG = (long)(PULSES_PER_REV * DEG_PER_LEG / 360.0f);

  // ---------- Timing ----------
  // Each leg (forward or backward) takes this long. MUST match top_arduino.ino
  // so both Arduinos reverse at the same instant. If you change this, change
  // it in BOTH .ino files.
  const unsigned long LEG_DURATION_MS = 100;

  // Per-pulse delay derived from leg duration. Total microseconds per pulse =
  //   LEG_DURATION_MS * 1000 / PULSES_PER_LEG. We split it into a HIGH width
  //   and a LOW gap.
  // For 100 ms / 1597 pulses = 62.6 us/pulse total -> 15 us HIGH + 47 us LOW.
  // (15 us HIGH is well above the driver's ~5 us minimum; 47 us LOW gives the
  // driver time to clock the next step.)
  const unsigned long TOTAL_US_PER_PULSE = ((unsigned long)LEG_DURATION_MS * 1000UL) / PULSES_PER_LEG;
  const int PULSE_WIDTH_US = 15;  // step pulse HIGH width (driver requires >= ~5 us)
  const int STEP_DELAY_US  = (int)(TOTAL_US_PER_PULSE - PULSE_WIDTH_US);

  // Integer-rounding compensation. PULSES_PER_LEG * (PULSE_WIDTH_US +
  // STEP_DELAY_US) is slightly less than LEG_DURATION_MS * 1000 because the
  // total-us-per-pulse calculation rounds down. We pad each leg with the
  // shortfall so the lateral cycle wall-time matches the top firmware exactly
  // (top hits 100.0 ms/leg; without this pad, lateral hits ~99.0 ms/leg).
  const long ACTUAL_US_PER_LEG  = PULSES_PER_LEG * (long)(PULSE_WIDTH_US + STEP_DELAY_US);
  const long TARGET_US_PER_LEG  = (long)LEG_DURATION_MS * 1000L;
  const long LEG_PAD_US         = TARGET_US_PER_LEG - ACTUAL_US_PER_LEG;

  // ---------- Run state ----------
  // Match top_arduino.ino so a START:<cycles> with the same N is accepted on
  // both sides.
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

  // ---------- One cycle = one back-and-forth ----------
  // Forward leg (PULSES_PER_LEG pulses) -> reverse direction -> backward leg.
  void runOneCycle() {
    // Forward 23 degrees
    digitalWrite(LAT_DIR, HIGH);
    for (long i = 0; i < PULSES_PER_LEG; i++) {
      pulseStep(LAT_STEP);
    }
    // Pad the forward leg up to LEG_DURATION_MS so the reversal happens at
    // the same wall-clock time as the top Arduino's reversal.
    if (LEG_PAD_US > 0) delayMicroseconds((unsigned int)LEG_PAD_US);

    // Backward 23 degrees
    digitalWrite(LAT_DIR, LOW);
    for (long i = 0; i < PULSES_PER_LEG; i++) {
      pulseStep(LAT_STEP);
    }
    // Pad the backward leg likewise so cycle completion lands at the same
    // wall-clock time as the top Arduino's cycle completion.
    if (LEG_PAD_US > 0) delayMicroseconds((unsigned int)LEG_PAD_US);

    currentCycle++;
    Serial.print("CYCLE:");
    Serial.println(currentCycle);

    if (currentCycle >= targetCycles) {
      isRunning = false;
      disableMotor();
      Serial.println("DONE:LAT");
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
