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
  // 3200 * 9/360 = 80 pulses per outer leg (exact)
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
