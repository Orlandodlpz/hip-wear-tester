// Top Arduino firmware - hip wear tester
// Drives Top Left (S1) and Top Right (S2) NEMA 23 stepper motors via external drivers.
//
// CYCLE DEFINITION (as of 2026-05-05):
//   One top cycle is THREE legs centered around home for whichever motor(s)
//   are active in the current mode:
//     leg 1: 9 deg forward (160 pulses)
//     leg 2: 18 deg backward (320 pulses, through home to opposite extreme)
//     leg 3: 9 deg forward (160 pulses, back to home)
//   Cycle counter increments after each three-leg motion.
//
// SYNC WITH LATERAL ARDUINO:
//   Both firmwares now use a hand-tuned per-pulse pace and a 20 ms settling
//   delay after every direction change. Wall-clock cycle times are similar
//   but no longer pinned to an exact target — the Pi-side gating on
//   min(lat_cycle, top_cycle) handles GUI counter sync.
//
// ANTI-DRIFT DESIGN:
//   The 20 ms delay() after each direction change lets the rotor physically
//   settle to a stop before reversing. This eliminated home-position drift
//   on the lateral motor caused by impact shock at fast reversals. The same
//   pattern is used here for the top motors.
//
// DRIVER MICROSTEPPING:
//   Top motor drivers are set to 6400 pulses per revolution
//   (1/32 microstep on a 1.8 deg motor). 9 deg = 6400 * 9 / 360 = 160 pulses.
//
// SERIAL PROTOCOL (unchanged - Python side does not need updates):
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

  // ---------- Pin assignments ----------
  const int TOP_LEFT_DIR   = 2;
  const int TOP_LEFT_STEP  = 3;
  const int TOP_RIGHT_DIR  = 4;
  const int TOP_RIGHT_STEP = 5;

  const bool USE_ENA = false;
  const int TOP_LEFT_ENA   = 6;
  const int TOP_RIGHT_ENA  = 7;

  // ---------- Cycle geometry ----------
  // Outer leg = DEG_PER_LEG. Middle leg = 2 * DEG_PER_LEG.
  const float DEG_PER_LEG     = 9.0f;
  const long  PULSES_PER_REV  = 3200;        // 1/32 microstep on a 1.8 deg motor
  // 6400 * 9/360 = 80 pulses per outer leg (exact)
  const long PULSES_PER_LEG = (long)(PULSES_PER_REV * DEG_PER_LEG / 360.0f);

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

  // ---------- moveSteps: one motor ----------
  // Mirrors the lateral firmware's moveSteps function:
  //   - Set DIR
  //   - 20 ms delay so the rotor physically settles before stepping resumes
  //   - Pulse STEP `steps` times with 490 us LOW + 490 us HIGH per pulse
  //     (~980 us total per pulse, identical pacing to the lateral firmware
  //     for visual/audio symmetry between motors)
  void moveSteps(int steps, bool dir, int dirPin, int stepPin) {
    digitalWrite(dirPin, dir);
    delay(17);

    for (int i = 0; i < steps; i++) {
      digitalWrite(stepPin, LOW);
      delayMicroseconds(1460);
      digitalWrite(stepPin, HIGH);
      delayMicroseconds(1460);
    }
  }

  // ---------- moveSteps: both motors simultaneously ----------
  // BOTH mode: pulse the two STEP pins on the same edge so the motors step
  // in lockstep. Same 20 ms settling delay after the DIR change.
  void moveStepsBoth(int steps, bool dir) {
    digitalWrite(TOP_LEFT_DIR,  dir), digitalWrite(TOP_RIGHT_DIR, dir);
    delay(17);

    for (int i = 0; i < steps; i++) {
      digitalWrite(TOP_LEFT_STEP,  LOW);
      digitalWrite(TOP_RIGHT_STEP, LOW);
      delayMicroseconds(1460);
      digitalWrite(TOP_LEFT_STEP,  HIGH);
      digitalWrite(TOP_RIGHT_STEP, HIGH);
      delayMicroseconds(1460);
    }
  }

  // ---------- Per-mode three-leg cycles ----------
  void runStation1Cycle() {
    moveSteps(80, LOW,  TOP_LEFT_DIR, TOP_LEFT_STEP);
    moveSteps(160, HIGH, TOP_LEFT_DIR, TOP_LEFT_STEP);
    moveSteps(80, LOW,  TOP_LEFT_DIR, TOP_LEFT_STEP);
  }

  void runStation2Cycle() {
    moveSteps(80, LOW,  TOP_RIGHT_DIR, TOP_RIGHT_STEP);
    moveSteps(160, HIGH, TOP_RIGHT_DIR, TOP_RIGHT_STEP);
    moveSteps(80, LOW,  TOP_RIGHT_DIR, TOP_RIGHT_STEP);
  }

  void runBothCycle() {
    moveStepsBoth(80, LOW);
    moveStepsBoth(160, HIGH);
    moveStepsBoth(80, LOW);
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
