# ClassAudit AI Live Monitoring Standard Operating Procedure
**Document ID:** SOP-MON-004  
**Version:** 2.1  
**Effective Date:** February 1, 2026  
**Last Reviewed:** April 5, 2026  
**Authority:** Office of the Principal, IT Department  

---

## 1. OVERVIEW AND PURPOSE

This Standard Operating Procedure (SOP) governs the use of the **Live Class Monitoring** feature within the ClassAudit AI system. The live monitoring system uses real-time face recognition to verify that the registered teacher is actively present during a class session. This document describes how the system works, the rules for handling interruptions, and the consequences for violations.

---

## 2. HOW LIVE MONITORING WORKS

### 2.1 Session Initiation
1. After a teacher starts a class via **Teacher Portal > Dashboard > Start Class**, the system creates an **active Class Session** record.
2. The teacher is redirected to the **Live Monitoring Page**, which activates the device's front-facing camera.
3. The system displays a **live video feed** from the camera and begins the automated face verification cycle.

### 2.2 Automated Verification Cycle
- The ClassAudit AI system captures a webcam frame every **5 seconds**.
- This frame is sent to the face recognition engine, which compares it against the teacher's stored **128-dimensional face embedding** (registered during teacher onboarding).
- The match threshold is set at a **face distance of 0.45** — any match with a distance below this threshold is considered a successful verification.
- **Successful Match:** The system increments the teacher's `total_active_duration` by 5 seconds.
- **Failed Match:** The system logs a warning but does not immediately terminate the session (see Section 4 — Absence During Class Policy).

### 2.3 Active Duration Tracking
- `Total Active Duration` is the cumulative sum of all 5-second intervals where a successful face match occurred.
- This metric is displayed in real-time on the monitoring page for the teacher's awareness.
- At class end, the total active duration is saved to the **Class Session** record and is visible to the Principal.
- **Active Duration Efficiency (%) = (Total Active Duration / Total Session Duration) × 100**
- A session with efficiency below **60%** is flagged as a **Low Attendance Session** in the Principal's reports.

---

## 3. REJOINING A CLASS SESSION (REJOIN RULES)

### 3.1 What is a Monitoring Resumption?
A **Monitoring Resumption** occurs when a teacher navigates back to the Live Monitoring page after leaving it (e.g., refreshing the browser, temporarily closing the tab, or rejoining after a disconnect).

### 3.2 Rejoining Procedure
1. The teacher navigates to **Teacher Portal > Dashboard**.
2. If an **Ongoing** class session exists for the teacher, a **"Rejoin Live Monitoring"** button will be displayed prominently.
3. Clicking this button resumes the existing session — the `total_active_duration` continues from where it was paused.
4. The system logs each rejoin as a **Monitoring Resumption Event**, and the count is stored in the Class Session record.

### 3.3 Resumption Count Tracking
- Each time the monitoring page is loaded for an ongoing session, the `monitoring_resumption_count` field is incremented by 1.
- A session with more than **5 resumptions** is flagged for Principal review, as it may indicate the teacher is repeatedly leaving and re-entering the monitoring view.
- The first time the monitoring page is loaded for a session counts as resumption count 1 (initial start).

### 3.4 Rejoin Time Limit
- A teacher can rejoin an ongoing session at any point during the session duration.
- If a session is accidentally marked as "Completed" (i.e., the teacher clicked "End Class" by mistake), they may request the Principal to reopen the session within **30 minutes**.

---

## 4. CAMERA FAILURE POLICY

### 4.1 What Constitutes a Camera Failure?
Camera failure includes:
- Physical webcam malfunction.
- Browser permissions for camera access denied.
- Camera disconnection (e.g., USB camera unplugged).
- Driver failure causing no video feed.

### 4.2 Immediate Steps on Camera Failure
1. The system will display a **"Camera Not Detected"** error on the monitoring page.
2. The teacher must attempt to resolve the issue immediately (check browser permissions, reconnect camera).
3. If the issue persists beyond **5 minutes**, the teacher must report it immediately to the IT support helpdesk.

### 4.3 Grace Period for Camera Failure
- A camera failure that is resolved and monitoring is resumed within **10 minutes** is treated as a brief interruption. The gap in monitoring is NOT counted as absence.
- A camera failure lasting more than **10 minutes** will result in the unmonitored period being excluded from the `total_active_duration`.

### 4.4 Reporting and Documentation
- Upon resolution, the teacher must submit a **Camera Failure Incident Report** via the Help module within the same working day.
- The report must include: Time of failure, duration, steps taken, and resolution method.
- The Principal reviews all camera failure reports and may verify with the IT department.

### 4.5 Repeated Camera Failures
- **3 or more camera failures in a single month** — The IT department will inspect and certify the teacher's device.
- **Unresolved or suspicious camera failures** — Principal may require the teacher to use an institutional device for monitoring.

---

## 5. ABSENCE DURING CLASS POLICY

### 5.1 Definition of Absence During Class
A teacher is considered **Absent During Class** when the face recognition system fails to detect a matching face for a **continuous period of 2 minutes or more** during an active session.

### 5.2 Warning System
- **30 seconds of failed detection:** A yellow warning appears on the monitoring screen prompting the teacher to position their face correctly.
- **60 seconds of failed detection:** An orange alert is displayed, urging immediate action.
- **120 seconds of failed detection:** The system logs an **In-Class Absence Event** and the period is excluded from active duration.

### 5.3 Consequences of In-Class Absence Events

| In-Class Absence Events Per Session | Action |
|---|---|
| 1 absence event (< 2 min) | Logged; No immediate action |
| 2 absence events | Session flagged; Teacher notified via dashboard |
| 3 or more absence events | Session marked as "Low Presence"; Visible to Principal |
| Active Duration Efficiency below 60% | Session marked as "Low Attendance"; Included in defaulter analysis |

---

## 6. INTERRUPTION HANDLING

### 6.1 Acceptable Interruptions
The following are classified as **Acceptable Interruptions** and are managed through temporary camera absence (up to 10 minutes with valid reason):
- Taking a phone call related to institution matters.
- Stepping out briefly to manage a student issue in the corridor.
- Administrative tasks at the class door.
- Technical adjustments to classroom equipment.

### 6.2 Managing an Acceptable Interruption
1. The teacher should note the time they leave the camera view.
2. Upon returning, normal face verification resumes automatically.
3. Periods of absence lasting under **10 minutes** and not forming a pattern are not penalized.

### 6.3 Unacceptable Interruptions
- Leaving the classroom for extended periods (more than 10 minutes) without a valid institutional reason.
- Deliberate attempts to place another person's face in front of the camera.
- Using a photograph or pre-recorded video to deceive the face recognition system.

### 6.4 Consequences of Unacceptable Interruptions
- **First Instance:** Formal written warning from the Principal.
- **Second Instance:** Show Cause notice issued. Disciplinary Committee review initiated.
- **Fraud Detection (Photo/Video Spoofing):** Immediate termination of employment. The matter is referred to institutional management for legal action if warranted.

---

## 7. SESSION TERMINATION

### 7.1 Normal Session End
- The teacher clicks the **"End Class"** button on the monitoring page at the conclusion of the class.
- The system timestamps the session end and saves all data.
- The session status is updated to **"Completed"**.

### 7.2 Automatic Session Termination
- If a session has not received any face verification data for **30 minutes** continuously, the system automatically marks the session as **"Stalled"** and alerts the Principal's dashboard.
- Stalled sessions can be reviewed and either completed or extended by the Principal.

---
*End of Document: SOP-MON-004 — Live Monitoring Standard Operating Procedure*
