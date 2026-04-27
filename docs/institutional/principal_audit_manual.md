# ClassAudit AI Principal Audit Manual
**Document ID:** MAN-AUD-006  
**Version:** 2.0  
**Effective Date:** January 1, 2026  
**Last Reviewed:** April 15, 2026  
**Authority:** Principal's Office, Institutional Governance Board  

---

## 1. PURPOSE

This Audit Manual is exclusively for the use of school Principals. It defines how to use the ClassAudit AI system to monitor, review, and act upon teacher attendance and performance data. It covers the audit workflow, warning issuance criteria, disciplinary escalation process, and report generation procedures.

---

## 2. ACCESSING THE PRINCIPAL PORTAL

### 2.1 Login Procedure
1. Navigate to the ClassAudit AI homepage.
2. Click **"Principal Login"** from the navigation bar.
3. Enter your registered **Username** and **Password** (Face Login is not available for Principals).
4. Click **"Login"** — you will be redirected to the **Principal Dashboard**.

### 2.2 Dashboard Overview
The Principal Dashboard provides a real-time snapshot:
- **Total Teachers Registered:** Count of all active teachers.
- **Present Today:** Teachers who have marked attendance via face recognition today.
- **Absent Today:** Teachers with no check-in for the current day.
- **Department View:** Teachers grouped by department for quick review.

---

## 3. HOW THE PRINCIPAL REVIEWS TEACHER ATTENDANCE

### 3.1 Individual Teacher Reports
To view a specific teacher's attendance record:
1. Go to **Principal Dashboard**.
2. Locate the teacher by name or department from the department cards.
3. Click on the teacher's name to open their profile.
4. Click **"View Reports"** — this opens the **Teacher Reports** page.
5. Use the filters to view data by **Date**, **Month/Year**, or the full history.

### 3.2 What the Report Shows
The Teacher Report includes:
- **Date of each class session.**
- **Subject taught.**
- **Session Start and End Time.**
- **Total Active Duration** (time the teacher was verified present during the class).
- **Expected Duration** (scheduled class duration from timetable).
- **Active Duration Efficiency %** — Sessions below 60% are highlighted in red.
- **Attendance Check-in Time and Status** (Present / Late).

### 3.3 Department-Wide Analysis
To review performance across a department:
1. Navigate to **Principal Portal > Analysis**.
2. This page displays:
   - **Department Distribution Chart** — Pie chart of teacher counts per department.
   - **Top Teachers** — Ranked by attendance rate and active class hours.
   - **Total Active Hours** — Aggregate class hours per department.
3. Click on **"Teacher Analysis"** for an individual teacher to see:
   - Monthly attendance history.
   - Session-by-session breakdown.
   - Late arrival frequency chart.

### 3.4 Audit Criteria Checklist
When auditing a teacher's record, verify the following:

| Audit Criterion | Acceptable Standard | Flag if |
|---|---|---|
| Monthly Attendance Rate | ≥ 85% | < 85% |
| Late Arrivals per Month | ≤ 2 | ≥ 3 |
| Active Duration Efficiency | ≥ 60% per session | < 60% on 3+ sessions |
| Monitoring Resumption Count | ≤ 3 per session | > 5 per session |
| Consecutive Absences | ≤ 2 days | ≥ 3 consecutive days |

---

## 4. WARNING CRITERIA

### 4.1 Verbal Warning Criteria
A **Verbal Warning** is the first level of intervention. It is issued when:
- Monthly attendance rate is between **75% and 84%**.
- Late arrivals are between **3 and 4 times** in a month.
- Active Duration Efficiency falls below 60% in **1 or 2 sessions** in a month.

**Process:**
1. The Principal or Head of Department meets with the teacher.
2. The concern is communicated verbally and documented in the system with a note.
3. The teacher is given a **30-day improvement window**.

### 4.2 Written Warning Criteria
A **Written Warning** is the second level. It is issued when:
- Monthly attendance rate falls between **65% and 74%**.
- Late arrivals are **5 to 6 times** in a month.
- Active Duration Efficiency below 60% in **3 or more sessions** in a month.
- **No improvement** observed after a prior verbal warning.

**Process:**
1. Principal issues a formal written warning letter.
2. The letter is acknowledged and signed by the teacher.
3. A copy is placed in the teacher's HR record.
4. The teacher is given a **60-day improvement window** with specific targets.

### 4.3 Show Cause Notice Criteria
A **Show Cause Notice (SCN)** is a legal document requesting the teacher to provide justification. It is issued when:
- Monthly attendance rate falls **below 65%** (Defaulter status).
- Late arrivals exceed **7 times** in a month.
- **3 or more consecutive unauthorized absences**.
- No improvement after a written warning period.
- Suspected fraud (e.g., camera spoofing attempts detected).

**Process:**
1. Principal drafts and issues the SCN.
2. The teacher has **5 working days** to submit a written response.
3. The response is reviewed by the Principal and Disciplinary Committee.

---

## 5. DISCIPLINARY WORKFLOW

### 5.1 Standard Escalation Path

```
1. Verbal Warning (Level 1)
         │
         ▼ (No improvement after 30 days)
2. Written Warning (Level 2)
         │
         ▼ (No improvement after 60 days)
3. Show Cause Notice (Level 3)
         │
         ▼ (Response reviewed — inadequate)
4. Disciplinary Committee Hearing
         │
    ┌────┴─────────────┐
    │                            │
Penalty Imposed       Cleared/Case Closed
(Suspension / Termination)
```

### 5.2 Disciplinary Committee Hearing
- The committee consists of the Principal, two senior department heads, and an HR representative.
- The teacher has the right to present their case and produce evidence.
- The committee must deliver its decision within **10 working days** of the hearing.
- Possible outcomes: Counseling, Salary Deduction, Suspension, Termination.

### 5.3 Termination Process
Termination may be immediate (without prior warning) in cases of:
- Proven academic fraud (falsifying attendance records).
- Physical misconduct toward students or staff.
- Repeated deliberate camera spoofing (identity fraud on the system).
- Absence for 10+ consecutive working days without any communication.

For all other cases, the standard escalation path (Section 5.1) must be followed before termination.

---

## 6. REPORT GENERATION RULES

### 6.1 Available Reports in ClassAudit AI

| Report Type | Location | Description |
|---|---|---|
| Teacher Attendance Report | Principal Dashboard > Reports > [Teacher] | Per-teacher attendance with month/date filter |
| Defaulter Report (CSV) | Principal Dashboard > Export Defaulters | List of all defaulters filtered by department, day, month, year |
| Department Analysis | Principal Dashboard > Analysis | Departmental statistics and charts |
| Individual Teacher Analysis | Principal Dashboard > Teacher Analysis > [Teacher] | Full profile with session breakdown |
| Class Session Report | View Teacher Reports > [Teacher] | Session-by-session active duration and efficiency |

### 6.2 Generating the Defaulter CSV Report
1. Navigate to **Principal Dashboard**.
2. Click **"Export Defaulters"** from the top action panel.
3. Apply filters: **Department, Day, Month, Year**.
4. Click **"Download CSV"**.
5. The downloaded file includes: Teacher Name, Department, Attendance %, Late Count, Absent Days.

### 6.3 Report Retention and Sharing Rules
- All reports generated are institutional records and must be stored securely.
- Reports containing teacher performance data must not be shared publicly or with non-management staff.
- Monthly reports should be reviewed by the Principal no later than the **5th of the following month**.
- Annual audit reports must be compiled and submitted to the Institutional Governing Board by **March 31** each year.

### 6.4 Report Accuracy and Disputes
- If a teacher disputes a data point in a report, the Principal must cross-verify against the system logs (attendance timestamps, face recognition logs) within **5 working days**.
- Corrections to records can only be made by the Principal after verification. All corrections must be documented.

---

## 7. TEACHER MANAGEMENT

### 7.1 Adding a New Teacher
1. Navigate to **Principal Dashboard > Add Teacher**.
2. Enter teacher name, username, department, and create a password.
3. Capture the teacher's face via webcam (5 images captured automatically).
4. Click **"Register Teacher"**.

### 7.2 Deleting a Teacher
1. Navigate to the teacher's profile on the Dashboard.
2. Click **"Delete Teacher"**.
3. Confirm the action. This permanently removes the teacher's account, attendance records, and face data.

### 7.3 Managing Timetables
1. On the Dashboard, click **"Schedule"** next to the teacher's name.
2. Add class slots by entering Subject, Day, Start Time, and End Time.
3. Remove individual slots or clear the entire schedule using the delete options.

---
*End of Document: MAN-AUD-006 — Principal Audit Manual*
