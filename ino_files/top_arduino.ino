// Top Arduino firmware - hip wear tester
// Drives Top Left (S1) and Top Right (S2) NEMA 23 stepper motors via external drivers.
//
// CYCLE DEFINITION (as of 2026-04-24):
//   One top cycle = 9 deg forward + 9 deg backward (one back-and-forth).
//   No inner-rep loop. The cycle counter increments after each back-and-forth.
//
// SYNC WITH LATERAL ARDUINO:
//   Each leg (forward, backward) has a fixed wall-time target (LEG_DURATION_MS) so the
//   lateral firmware can match it and both Arduinos reverse direction at the same instant.
//   Default: 100 ms per leg -> 200 ms per cycle -> 5 Hz cycle rate.
//
// DRIVER MICROSTEPPING:
//   Top motor drivers are set to 6400 pulses per revolution
//   (equivalent to 1/32 microstepping on a 1.8 deg/step NEMA 23).
//   9 deg = 6400 * 9 / 360 = 160 pulses (exact).
//
// SERIAL PROTOCOL (unchanged from previous firmware - Python side does not need updates):
//   Commands:
//     START:S1:<cycles>     run Station 1 (top left only) for <cycles> overall cycles
//     START:S2:<cycles>     run Station 2 (top right only)
//     START:BOTH:<cycles>   run both top motors simultaneously
//     STOP                  immediately stop and reset
//   Responses:
//     STARTED:TOP:<mode>:<cycles>
//     CYCLE:<n>             one per completed cycle
//     DONE:TOP              all <cycles> completed
//     STOPPED:TOP           STOP acknowledged
//     ERR:<reason>

  // ---------- Pin assignments (unchanged) ----------
  const int TOP_LEFT_DIR   = 2;
  const int TOP_LEFT_STEP  = 3;
  const int TOP_RIGHT_DIR  = 4;
  const int TOP_RIGHT_STEP = 5;

  const bool USE_ENA = false;
  const int TOP_LEFT_ENA   = 6;
  const int TOP_RIGHT_ENA  = 7;

  // ---------- Cycle geometry ----------
  // Change these constants if the angle, driver pulses/rev, or timing changes.
  const float DEG_PER_LEG     = 9.0f;     // degrees per direction (9 forward, 9 back)
  const long  PULSES_PER_REV  = 6400;     // driver "pulses/rev" DIP setting
                                          // (6400 P/R = 1/32 microstep on a 1.8 deg NEMA 23)
  // Pulses per direction = pulses_per_rev * (deg / 360)
  // For 9 deg at 6400 P/R: 6400 * 9/360 = 160 pulses (exact)
  const long PULSES_PER_LEG = (long)(PULSES_PER_REV * DEG_PER_LEG / 360.0f);

  // ---------- Timing ----------
  // Each leg (forward or backward) takes this long. The lateral firmware uses the same
  // value so both Arduinos reverse at the same instant.
  const unsigned long LEG_DURATION_MS = 100;

  // Per-pulse delay derived from leg duration. Total microseconds per pulse =
  //   LEG_DURATION_MS * 1000 / PULSES_PER_LEG. We split it into a HIGH width and a LOW gap.
  // For 100 ms / 160 pulses = 625 us/pulse total -> 50 us HIGH + 575 us LOW.
  const unsigned long TOTAL_US_PER_PULSE = ((unsigned long)LEG_DURATION_MS * 1000UL) / PULSES_PER_LEG;
  const int PULSE_WIDTH_US = 50;  // step pulse HIGH width (driver requires >= ~5 us, 50 is comfortable)
  const int STEP_DELAY_US  = (int)(TOTAL_US_PER_PULSE - PULSE_WIDTH_US);

  // Integer-rounding compensation. PULSES_PER_LEG * (PULSE_WIDTH_US +
  // STEP_DELAY_US) can be slightly less than LEG_DURATION_MS * 1000 because
  // the total-us-per-pulse calculation rounds down. We pad each leg with the
  // shortfall so wall-time matches the lateral firmware exactly. At the
  // current 9 deg / 6400 P/R settings, 100 ms / 160 pulses divides cleanly
  // and LEG_PAD_US is 0 — the pad is a no-op. It exists so changing the
  // angle or microstepping later can't reintroduce drift.
  const long ACTUAL_US_PER_LEG  = PULSES_PER_LEG * (long)(PULSE_WIDTH_US + STEP_DELAY_US);
  const long TARGET_US_PER_LEG  = (long)LEG_DURATION_MS * 1000L;
  const long LEG_PAD_US         = TARGET_US_PER_LEG - ACTUAL_US_PER_LEG;

  // ---------- Run state ----------
  const unsigned long MAX_CYCLES = 5000000;

  String command = "";

  enum TopMode {
    MODE_NONE,
    MODE_S1,
    MODE_S2,
    MODE_BOTH
  };

  TopMode currentMode = MODE_NONE;

  bool isRunning = false;
  unsigned long currentCycle = 0;
  unsigned long targetCycles = 0;

  // ---------- Pulse helpers ----------
  void pulseStep(int stepPin) {
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(PULSE_WIDTH_US);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(STEP_DELAY_US);
  }

  void pulseBoth() {
    digitalWrite(TOP_LEFT_STEP, HIGH);
    digitalWrite(TOP_RIGHT_STEP, HIGH);
    delayMicroseconds(PULSE_WIDTH_US);
    digitalWrite(TOP_LEFT_STEP, LOW);
    digitalWrite(TOP_RIGHT_STEP, LOW);
    delayMicroseconds(STEP_DELAY_US);
  }

  void enableAllTop() {
    if (USE_ENA) {
      digitalWrite(TOP_LEFT_ENA, LOW);
      digitalWrite(TOP_RIGHT_ENA, LOW);
    }
  }

  void disableAllTop() {
    if (USE_ENA) {
      digitalWrite(TOP_LEFT_ENA, HIGH);
      digitalWrite(TOP_RIGHT_ENA, HIGH);
    }
  }

  // ---------- One cycle = one back-and-forth ----------
  // Each function below executes EXACTLY one overall cycle for its mode:
  //   forward leg (PULSES_PER_LEG pulses) -> reverse direction -> backward leg (PULSES_PER_LEG pulses)

  void runStation1Cycle() {
    digitalWrite(TOP_LEFT_DIR, HIGH);
    for (long i = 0; i < PULSES_PER_LEG; i++) pulseStep(TOP_LEFT_STEP);
    if (LEG_PAD_US > 0) delayMicroseconds((unsigned int)LEG_PAD_US);

    digitalWrite(TOP_LEFT_DIR, LOW);
    for (long i = 0; i < PULSES_PER_LEG; i++) pulseStep(TOP_LEFT_STEP);
    if (LEG_PAD_US > 0) delayMicroseconds((unsigned int)LEG_PAD_US);
  }

  void runStation2Cycle() {
    digitalWrite(TOP_RIGHT_DIR, HIGH);
    for (long i = 0; i < PULSES_PER_LEG; i++) pulseStep(TOP_RIGHT_STEP);
    if (LEG_PAD_US > 0) delayMicroseconds((unsigned int)LEG_PAD_US);

    digitalWrite(TOP_RIGHT_DIR, LOW);
    for (long i = 0; i < PULSES_PER_LEG; i++) pulseStep(TOP_RIGHT_STEP);
    if (LEG_PAD_US > 0) delayMicroseconds((unsigned int)LEG_PAD_US);
  }

  void runBothCycle() {
    digitalWrite(TOP_LEFT_DIR, HIGH);
    digitalWrite(TOP_RIGHT_DIR, HIGH);
    for (long i = 0; i < PULSES_PER_LEG; i++) pulseBoth();
    if (LEG_PAD_US > 0) delayMicroseconds((unsigned int)LEG_PAD_US);

    digitalWrite(TOP_LEFT_DIR, LOW);
    digitalWrite(TOP_RIGHT_DIR, LOW);
    for (long i = 0; i < PULSES_PER_LEG; i++) pulseBoth();
    if (LEG_PAD_US > 0) delayMicroseconds((unsigned int)LEG_PAD_US);
  }

  void runOneCycle() {
    if (currentMode == MODE_S1) {
      runStation1Cycle();
    } else if (currentMode == MODE_S2) {
      runStation2Cycle();
    } else if (currentMode == MODE_BOTH) {
      runBothCycle();
    } else {
      isRunning = false;
      Serial.println("ERR:NO_MODE");
      return;
    }

    currentCycle++;
    Serial.print("CYCLE:");
    Serial.println(currentCycle);

    if (currentCycle >= targetCycles) {
      isRunning = false;
      disableAllTop();
      Serial.println("DONE:TOP");
    }
  }

  // ---------- Command parsing ----------
  TopMode parseMode(String s) {
    if (s == "S1") return MODE_S1;
    if (s == "S2") return MODE_S2;
    if (s == "BOTH") return MODE_BOTH;
    return MODE_NONE;
  }

  void handleCommand(String cmd) {
    cmd.trim();

    if (cmd == "STOP") {
      isRunning = false;
      currentMode = MODE_NONE;
      currentCycle = 0;
      targetCycles = 0;
      disableAllTop();
      Serial.println("STOPPED:TOP");
      return;
    }

    if (isRunning && cmd.startsWith("START:")) {
      Serial.println("ERR:ALREADY_RUNNING");
      return;
    }

    if (cmd.startsWith("START:")) {
      int firstColon = cmd.indexOf(':');
      int secondColon = cmd.indexOf(':', firstColon + 1);

      if (secondColon == -1) {
        Serial.println("ERR:BAD_FORMAT");
        return;
      }

      String modeStr = cmd.substring(firstColon + 1, secondColon);
      String cyclesStr = cmd.substring(secondColon + 1);

      TopMode mode = parseMode(modeStr);
      unsigned long cycles = cyclesStr.toInt();

      if (mode == MODE_NONE) {
        Serial.println("ERR:BAD_MODE");
        return;
      }

      if (cycles == 0 || cycles > MAX_CYCLES) {
        Serial.println("ERR:BAD_CYCLES");
        return;
      }

      currentMode = mode;
      currentCycle = 0;
      targetCycles = cycles;
      isRunning = true;
      enableAllTop();

      Serial.print("STARTED:TOP:");
      Serial.print(modeStr);
      Serial.print(":");
      Serial.println(targetCycles);
      return;
    }

    Serial.println("ERR:UNKNOWN_COMMAND");
  }

  // ---------- Setup / loop ----------
  void setup() {
    pinMode(TOP_LEFT_DIR, OUTPUT);
    pinMode(TOP_LEFT_STEP, OUTPUT);
    pinMode(TOP_RIGHT_DIR, OUTPUT);
    pinMode(TOP_RIGHT_STEP, OUTPUT);

    if (USE_ENA) {
      pinMode(TOP_LEFT_ENA, OUTPUT);
      pinMode(TOP_RIGHT_ENA, OUTPUT);
    }

    digitalWrite(TOP_LEFT_DIR, LOW);
    digitalWrite(TOP_LEFT_STEP, LOW);
    digitalWrite(TOP_RIGHT_DIR, LOW);
    digitalWrite(TOP_RIGHT_STEP, LOW);
    disableAllTop();

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
