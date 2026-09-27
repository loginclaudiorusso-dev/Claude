/**
 * Domain model for Pulse. Every data source (HealthKit, Health Auto Export
 * JSON/CSV) is normalised into these shapes before any scoring happens.
 *
 * Conventions:
 * - `Timestamp` is Unix epoch in milliseconds.
 * - `DayKey` is a local calendar day `YYYY-MM-DD`. A night's sleep belongs to
 *   the day on which it ends (the morning you wake up).
 * - Energy in kcal, durations in minutes unless the field name says otherwise.
 */

export type Timestamp = number;
export type DayKey = string;

// ---------------------------------------------------------------------------
// Raw samples
// ---------------------------------------------------------------------------

export type DataSource = 'healthkit' | 'import' | 'demo';

export interface HeartRateSample {
  timestamp: Timestamp;
  bpm: number;
}

/** Apple Health stores HRV as SDNN in milliseconds. */
export interface HrvSample {
  timestamp: Timestamp;
  sdnnMs: number;
}

/**
 * Sleep stages as reported by Apple Watch (iOS 16+). `asleep` covers
 * unspecified sleep from older devices/third-party sources without staging.
 */
export type SleepStage = 'inBed' | 'awake' | 'asleep' | 'core' | 'deep' | 'rem';

export interface SleepSegment {
  start: Timestamp;
  end: Timestamp;
  stage: SleepStage;
}

export interface SleepSession {
  start: Timestamp;
  end: Timestamp;
  segments: SleepSegment[];
}

export type WorkoutType =
  | 'running'
  | 'cycling'
  | 'walking'
  | 'hiking'
  | 'swimming'
  | 'strength'
  | 'hiit'
  | 'yoga'
  | 'rowing'
  | 'other';

export interface Workout {
  id: string;
  type: WorkoutType;
  /** Original activity name from the source, e.g. "Traditional Strength Training". */
  name?: string;
  start: Timestamp;
  end: Timestamp;
  activeEnergyKcal: number;
  avgHeartRate?: number;
  maxHeartRate?: number;
  distanceMeters?: number;
}

/** Everything we know about one calendar day. */
export interface DailyHealthData {
  date: DayKey;
  source: DataSource;
  hrvSamples: HrvSample[];
  /** Apple's daily resting heart rate estimate (bpm). */
  restingHeartRate?: number;
  heartRateSamples: HeartRateSample[];
  /** The main sleep session that ended on this day. */
  sleep?: SleepSession;
  steps: number;
  activeEnergyKcal: number;
  basalEnergyKcal?: number;
  vo2Max?: number;
  respiratoryRate?: number;
  workouts: Workout[];
}

// ---------------------------------------------------------------------------
// User profile & baselines
// ---------------------------------------------------------------------------

export type BiologicalSex = 'female' | 'male' | 'other';

export interface UserProfile {
  birthYear?: number;
  sex?: BiologicalSex;
  /** Measured max heart rate; estimated from age (Tanaka) if absent. */
  maxHeartRate?: number;
  /** Personal baseline sleep need in minutes (default 480 = 8 h). */
  sleepNeedMinutes?: number;
}

/** Rolling statistics over the baseline window (default: previous 7 days). */
export interface MetricBaseline {
  mean: number;
  sd: number;
  /** Number of days that contributed. */
  n: number;
}

export interface Baselines {
  /** Computed on ln(SDNN), the standard way to normalise skewed HRV data. */
  lnHrv?: MetricBaseline;
  /** Linear-scale HRV mean for human-readable "x % below average" messages. */
  hrvMs?: MetricBaseline;
  restingHeartRate?: MetricBaseline;
  sleepMinutes?: MetricBaseline;
}

// ---------------------------------------------------------------------------
// Scores
// ---------------------------------------------------------------------------

/** `calibrating` until enough days exist to build a personal baseline. */
export type ScoreConfidence = 'calibrating' | 'low' | 'high';

export type RecoveryZone = 'green' | 'yellow' | 'red';

export interface ReadinessComponents {
  /** 0–100 sub-score, or undefined if that input was missing. */
  hrv?: number;
  restingHeartRate?: number;
  sleep?: number;
}

export interface ReadinessResult {
  /** 0–100 %. */
  score: number;
  zone: RecoveryZone;
  confidence: ScoreConfidence;
  components: ReadinessComponents;
  /** Today's nightly HRV (SDNN ms). */
  hrvMs?: number;
  /** Relative deviation of today's HRV from the baseline mean, in %. */
  hrvDeviationPct?: number;
  restingHeartRate?: number;
  /** Today's RHR minus baseline mean (bpm); positive = elevated. */
  restingHeartRateDeviationBpm?: number;
}

export type HeartRateZone = 1 | 2 | 3 | 4 | 5;
export type ZoneMinutes = Record<HeartRateZone, number>;

export type StrainLevel = 'light' | 'moderate' | 'high' | 'allOut';

export interface StrainResult {
  /** 0–21, logarithmic like Whoop: each point is harder to earn. */
  score: number;
  level: StrainLevel;
  /** Banister TRIMP accumulated over the day (cardiovascular load units). */
  trimp: number;
  /** Portion of the TRIMP that happened during workouts. */
  workoutTrimp: number;
  zoneMinutes: ZoneMinutes;
  /** How the load was derived. */
  method: 'heartRate' | 'workoutEstimate' | 'energyEstimate';
}

export interface StrainTarget {
  min: number;
  max: number;
}

export interface SleepStageMinutes {
  awake: number;
  core: number;
  deep: number;
  rem: number;
  /** Sleep without stage information. */
  unspecified: number;
}

export interface SleepAnalysis {
  timeInBedMinutes: number;
  totalSleepMinutes: number;
  stages: SleepStageMinutes;
  /** Share of total sleep per stage (0–1). Undefined when unstaged. */
  stageShare?: { core: number; deep: number; rem: number };
  /** totalSleep / timeInBed (0–1). */
  efficiency: number;
  /** Tonight's need: base need + strain adjustment + debt repayment. */
  sleepNeedMinutes: number;
  /** Actual vs. need, 0–100 %. */
  performancePct: number;
  /** Rolling sleep debt after this night (minutes, decays ~15 %/day). */
  debtMinutes: number;
  /** Overall 0–100 quality score (duration, efficiency, architecture). */
  score: number;
  bedtime: Timestamp;
  wakeTime: Timestamp;
}

export interface BodyBatteryPoint {
  timestamp: Timestamp;
  /** 0–100. */
  level: number;
}

export interface BodyBatteryResult {
  points: BodyBatteryPoint[];
  /** Level at wake-up. */
  startLevel: number;
  /** Level at the end of the evaluated window (now, or midnight for past days). */
  currentLevel: number;
  charged: number;
  drained: number;
  min: number;
  max: number;
}

// ---------------------------------------------------------------------------
// Aggregates
// ---------------------------------------------------------------------------

export interface DailyMetrics {
  hrvMs?: number;
  restingHeartRate?: number;
  steps: number;
  activeEnergyKcal: number;
  vo2Max?: number;
  respiratoryRate?: number;
  workoutMinutes: number;
  workoutCount: number;
}

export interface DailySummary {
  date: DayKey;
  metrics: DailyMetrics;
  baselines: Baselines;
  readiness?: ReadinessResult;
  strain: StrainResult;
  /** Strain range recommended for today given readiness. */
  strainTarget?: StrainTarget;
  sleep?: SleepAnalysis;
  bodyBattery?: BodyBatteryResult;
}

export type TrendDirection = 'up' | 'down' | 'flat';

export interface TrendPoint {
  date: DayKey;
  value: number | null;
}

export interface MetricTrend {
  points: TrendPoint[];
  average: number | null;
  /** Least-squares slope per day. */
  slopePerDay: number | null;
  direction: TrendDirection;
  /** Change along the regression line over the window, relative to the mean, in %. */
  changePct: number | null;
}

export type TrendWindow = 7 | 30;

export interface TrendReport {
  window: TrendWindow;
  hrv: MetricTrend;
  restingHeartRate: MetricTrend;
  readiness: MetricTrend;
  strain: MetricTrend;
  sleepMinutes: MetricTrend;
  deepSleepMinutes: MetricTrend;
  remSleepMinutes: MetricTrend;
  /** Acute (7 d) : chronic (28 d) strain ratio; 0.8–1.3 is the "sweet spot". */
  acuteChronicRatio: number | null;
}
