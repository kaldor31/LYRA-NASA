"""Local LYRA metric catalog (what is not in nasa_reference.json).

Name, unit, risks and the expected trajectory come from the NASA reference (its keys are canonical).
This file holds the engineering parameters: sensor group, harmful direction, measurement noise,
default value for the simulation, which session measures the metric, which module it belongs to,
and what to advise.

Modules:
  core      contactless channels of the LYRA station: RGB, structured IR light, depth (ToF).
            Only core metrics drive the overall result.
  research  optional contact research module: vertical grips in the side posts with Doppler
            ultrasound (hydrogel cassette), PPG/SpO2, palm temperature and a load cell.
            Shown separately and excluded from the overall result by default.
            LYRA makes no heart assessment through the palm.

Metrics listed in LOCAL_ONLY may be missing from data/nasa_reference.json; the code tolerates that.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DAILY, WEEKLY, SURVEY, IMPORT = "daily", "weekly", "survey", "import"
CORE, RESEARCH = "core", "research"


@dataclass(frozen=True)
class MetricSpec:
    key: str
    name: str            # fallback name if the reference has no name_ru
    unit: str
    group: str           # face | body | hands | self | dose
    zone: str            # zone on the 3D model: face | body | legs | hands | posture | none
    direction: str       # "up": growth is harmful, "down": decline is harmful, "both"
    noise: float         # measurement noise sigma; lower bound for the personal-norm sigma
    base: float          # typical pre-flight value (for the simulation)
    ref: tuple[float, float]  # population range used until 7 personal measurements exist
    decimals: int
    session: str = DAILY  # daily: every session, weekly: full test only
    advice: str = ""      # Repeat measurement: a concrete action from onboard countermeasures
    steps: tuple[str, ...] = field(default_factory=tuple)  # Refer to specialist: "what to do now"
    module: str = CORE
    risk_ids: tuple[str, ...] = ()  # fallback risk ids when the reference has none for this key


_CALL = "Tell the flight surgeon (the data has already been sent automatically)."

SPECS: dict[str, MetricSpec] = {s.key: s for s in [
    # ---- face: structured IR light + RGB ----
    MetricSpec("face_volume_ml", "Face volume", "mL", "face", "face", "up", 6.0, 1150, (1050, 1250), 0,
               advice="Check your fluid intake and dietary salt; repeat the scan tomorrow morning.",
               steps=("Note whether you have a headache or any change in vision.",
                      "Do the vision check with the onboard card (Amsler grid).", _CALL)),
    MetricSpec("periorbital_puffiness_mm", "Puffiness around the eyes", "mm", "face", "face", "up", 0.15, 2.0,
               (1.0, 3.5), 1,
               advice="Note your sleep quality; repeat the scan in the morning after waking up.",
               steps=("Check your vision with the onboard card.", "If you have a headache, mark it in the survey.",
                      _CALL)),
    MetricSpec("blink_rate", "Blink rate", "/min", "face", "face", "both", 2.5, 15, (8, 25), 0,
               advice="Take a break from screens and moisten your eyes as the onboard procedure describes."),
    MetricSpec("perclos", "Eye closure (PERCLOS)", "%", "face", "face", "up", 1.5, 4.0, (0, 12), 1,
               advice="Possible sign of fatigue: take it into account when planning complex tasks, and review sleep.",
               steps=("Avoid critical operations for the next hour.", "Rest and repeat the scan.", _CALL)),
    MetricSpec("yawn_count", "Yawning", "count", "face", "face", "up", 0.7, 0, (0, 1), 0,
               advice="Possible sign of fatigue: review your sleep over the last 24 hours."),
    MetricSpec("facial_tension", "Possible signs of strain (facial expression)", "index 0-1", "face", "face", "up",
               0.06, 0.25, (0, 0.5), 2,
               advice="Possible signs of strain. Take a short pause and a breathing exercise; "
                      "a call with the psychologist is available if you want one."),
    MetricSpec("hr_rppg", "Pulse (camera, rPPG)", "bpm", "face", "face", "both", 3.0, 64, (50, 100), 0,
               advice="Repeat the measurement after 10 minutes at rest, face toward the mirror, good light."),
    # ---- body: depth (ToF) + skeletal keypoints from 3 synced views ----
    MetricSpec("leg_volume_ml", "Lower leg volume", "mL", "body", "legs", "down", 15.0, 2400, (2000, 2800), 0,
               advice="Check this week's leg exercise (treadmill, squats on ARED).",
               steps=("Repeat the scan standing straight in the foot restraints.",
                      "Review the strength training plan.", _CALL)),
    MetricSpec("body_volume_l", "Total body volume", "L", "body", "body", "down", 0.25, 72, (55, 95), 1,
               advice="Compare your intake with the onboard nutrition plan (calories)."),
    MetricSpec("height_cm", "Height", "cm", "body", "body", "up", 0.25, 176, (155, 195), 1,
               advice="Spinal elongation is expected. If your back hurts, do the core stabilization exercises.",
               steps=("Mark back pain in the survey.", "Do not move heavy loads without restraint.", _CALL)),
    MetricSpec("head_forward_deg", "Head tilt forward", "°", "body", "posture", "up", 1.5, 8, (0, 20), 1,
               advice="Neck and shoulder warm-up; check the ergonomics of your workstation."),
    MetricSpec("shoulder_asym_deg", "Shoulder height difference", "°", "body", "posture", "up", 0.6, 1.2, (0, 4), 1,
               advice="Shoulder warm-up, then repeat the scan."),
    MetricSpec("trunk_tilt_deg", "Trunk tilt", "°", "body", "posture", "up", 1.2, 3.0, (0, 12), 1,
               advice="Trunk mobility exercise, then repeat the scan with palms on the marked mirror zones.",
               risk_ids=("sensorimotor",)),
    MetricSpec("pelvis_tilt_deg", "Pelvis tilt", "°", "body", "posture", "up", 1.0, 2.0, (0, 10), 1,
               advice="Hip and core exercise, then repeat the scan standing in the foot restraints.",
               risk_ids=("sensorimotor",)),
    MetricSpec("scapula_asym_mm", "Back and scapula asymmetry", "mm", "body", "posture", "up", 1.5, 4.0, (0, 15), 1,
               advice="Shoulder blade mobility exercise, then repeat the scan.", risk_ids=("bone_muscle",)),
    MetricSpec("spine_length_mm", "Spine keypoint distance (C7 to pelvis)", "mm", "body", "posture", "up", 2.0, 520,
               (440, 600), 0,
               advice="Spinal elongation is expected in weightlessness; if your back hurts, mark it in the survey.",
               risk_ids=("bone_muscle",)),
    MetricSpec("pose_return_s", "Time to return to usual pose", "s", "body", "posture", "up", 0.3, 2.0, (0.5, 5), 1,
               advice="Possible sensorimotor adaptation: move slowly and repeat the scan later today.",
               risk_ids=("sensorimotor",)),
    # ---- research module (contact grips): load cell, Doppler, PPG ----
    MetricSpec("grip_left_kg", "Grip strength (left)", "kg", "hands", "hands", "down", 0.8, 40, (20, 70), 1,
               module=RESEARCH,
               advice="Functional marker of muscle mass: check that strength training was done.",
               steps=("Repeat 2 squeezes after 15 minutes of rest.", "Check the ARED training schedule.", _CALL)),
    MetricSpec("grip_right_kg", "Grip strength (right)", "kg", "hands", "hands", "down", 0.8, 43, (20, 70), 1,
               module=RESEARCH,
               advice="Functional marker of muscle mass: check that strength training was done.",
               steps=("Repeat 2 squeezes after 15 minutes of rest.", "Check the ARED training schedule.", _CALL)),
    MetricSpec("doppler_flow_left_cms", "Palm blood flow (left, research)", "cm/s", "hands", "hands", "down", 1.2, 22,
               (12, 35), 1, module=RESEARCH,
               advice="Warm your hands and repeat at rest in 15 minutes.",
               steps=("Repeat at rest with both hands on the grips.",
                      "Look at the hand: swelling, pain, color change?", _CALL)),
    MetricSpec("doppler_flow_right_cms", "Palm blood flow (right, research)", "cm/s", "hands", "hands", "down", 1.2, 23,
               (12, 35), 1, module=RESEARCH,
               advice="Warm your hands and repeat at rest in 15 minutes.",
               steps=("Repeat at rest with both hands on the grips.",
                      "Look at the hand: swelling, pain, color change?", _CALL)),
    MetricSpec("flow_asymmetry_pct", "Left/right flow asymmetry (research)", "%", "hands", "hands", "up", 1.5, 4,
               (0, 12), 1, module=RESEARCH,
               advice="Repeat; make sure both palms rest firmly on the Doppler windows.",
               steps=("Repeat the measurement.", "Look at both arms and the neck: swelling, pain, heaviness?", _CALL)),
    MetricSpec("hr_palm", "Pulse (grip PPG, research)", "bpm", "hands", "hands", "both", 3.0, 63, (50, 100), 0,
               module=RESEARCH,
               advice="Repeat after 10 minutes at rest, with no exercise beforehand.",
               steps=("Sit or restrain yourself, breathe calmly for 5 minutes.", "Repeat the session.", _CALL)),
    MetricSpec("hrv_rmssd_ms", "Pulse variability (RMSSD, research)", "ms", "hands", "hands", "down", 5.0, 45, (20, 90),
               0, module=RESEARCH, advice="Possible sign of fatigue or stress: review sleep and workload."),
    MetricSpec("spo2", "Blood oxygen SpO₂ (research)", "%", "hands", "hands", "down", 0.7, 98, (95, 100), 0,
               module=RESEARCH,
               advice="Check finger position and repeat; check the module atmosphere readings.",
               steps=("Repeat the measurement.", "Check module O₂/CO₂ on the life support panel.", _CALL)),
    MetricSpec("skin_temp", "Palm temperature (research)", "°C", "hands", "hands", "both", 0.3, 33.4, (31, 35.5), 1,
               module=RESEARCH, advice="Depends on module temperature: repeat in 15 minutes."),
    MetricSpec("handgrip_hr_response_bpm", "Pulse response to the handgrip test (research)", "bpm", "hands", "hands",
               "both", 2.5, 14, (5, 25), 0, session=WEEKLY, module=RESEARCH,
               advice="Repeat the full test in 1 to 2 days, at rest."),
    MetricSpec("handgrip_recovery_s", "Recovery after the handgrip test (research)", "s", "hands", "hands", "up", 8.0,
               60, (30, 120), 0, session=WEEKLY, module=RESEARCH,
               advice="Repeat the full test in 1 to 2 days; check aerobic training."),
    # ---- self-report (15 s voice survey) ----
    MetricSpec("sleep_score", "Sleep (self-rating)", "1-5", "self", "none", "down", 0.6, 4, (3, 5), 0, session=SURVEY,
               advice="Check your routine: darkness, noise, no screens before sleep."),
    MetricSpec("wellbeing_score", "Wellbeing (self-rating)", "1-5", "self", "none", "down", 0.6, 4, (3, 5), 0,
               session=SURVEY, advice="Plan rest or a call with family; a talk with the psychologist is available."),
    MetricSpec("symptoms_flag", "Symptoms (self-report)", "yes/no", "self", "none", "up", 0.3, 0, (0, 0), 0,
               session=SURVEY, advice="Describe the symptoms by voice: the recording goes to the flight surgeon."),
    MetricSpec("back_pain_flag", "Back pain (self-report, optional)", "yes/no", "self", "none", "up", 0.3, 0, (0, 0), 0,
               session=SURVEY, advice="Do the core stabilization exercises; the note goes to the flight surgeon.",
               risk_ids=("bone_muscle",)),
    # ---- dosimeter import (LYRA does not measure radiation) ----
    MetricSpec("radiation_dose_msv", "Accumulated dose (station dosimeter)", "mSv", "dose", "none", "up", 0.1, 0,
               (0, 600), 1, session=IMPORT),
]}

# Metrics defined only here; data/nasa_reference.json may or may not describe them.
LOCAL_ONLY = frozenset({"trunk_tilt_deg", "pelvis_tilt_deg", "scapula_asym_mm", "spine_length_mm", "pose_return_s",
                        "back_pain_flag"})
POSTURE_KEYS = [k for k, s in SPECS.items() if s.zone == "posture"]
SURVEY_KEYS = [k for k, s in SPECS.items() if s.session == SURVEY]
SENSOR_KEYS = [k for k, s in SPECS.items() if s.session in (DAILY, WEEKLY)]
RESEARCH_KEYS = [k for k, s in SPECS.items() if s.module == RESEARCH]


def keys_for_mode(mode: str) -> list[str]:
    """Sensor metrics a session captures: daily is the express scan, weekly is the full test."""
    allowed = {DAILY} if mode == DAILY else {DAILY, WEEKLY}
    return [k for k in SENSOR_KEYS if SPECS[k].session in allowed]
