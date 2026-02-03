# iRecover - PPT Presentation (4 Slides)

---

## SLIDE 1: Problem & Solution

### 🔴 The Problem: Air Cargo Disruption Crisis

| Pain Point                     | Impact                              |
| ------------------------------ | ----------------------------------- |
| 30% of cargo flights disrupted | Cargo stranded, connections missed  |
| Manual recovery: 2-4 hours     | 24/7 ops staff, high costs          |
| Sensitive cargo at risk        | Pharma spoilage, animal welfare     |
| Reactive communication         | Customer dissatisfaction, churn     |
| **$10B+ lost annually**        | SLA penalties, operational overhead |

### 🟢 Our Solution: iRecover

> **Multi-agent AI system that automatically detects, analyzes, and recovers disrupted cargo—escalating to humans only for sensitive shipments.**

**Core Innovation:** Not just answering questions—**REASONING, DECIDING, and ACTING**

| Before iRecover   | After iRecover             |
| ----------------- | -------------------------- |
| 3+ hours recovery | **15 minutes**             |
| 100% manual       | **80% automated**          |
| Reactive alerts   | **Proactive recovery**     |
| All cases = human | **Only sensitive → human** |

---

## SLIDE 2: GenAI & Agentic Architecture

### 🤖 6 Specialized AI Agents (Not One Mega-Prompt)

```
┌────────────────── ROOT ORCHESTRATOR ──────────────────┐
│     State management • Rollback • Audit trail         │
└───────────────────────────────────────────────────────┘
         │
  DETECT → IMPACT → REPLAN → APPROVE → EXECUTE → NOTIFY
    │        │        │         │         │         │
 Weather   AWB/SLA   Alt.    LLM-based  Booking   Email/
 News      Analysis  Flights  Routing   APIs      SMS
```

| Agent            | AI Capability                                         | Goes Beyond Simple Prompts                 |
| ---------------- | ----------------------------------------------------- | ------------------------------------------ |
| **Detection**    | Classifies disruption from flights, weather, news     | Multi-source reasoning, severity scoring   |
| **Impact**       | Evaluates SLA breach risk, revenue impact             | Cargo-specific constraint understanding    |
| **Replan**       | Generates recovery scenarios (rebook, reroute, truck) | Cost-benefit scoring, capacity validation  |
| **Approval**     | Routes to auto-approve vs. human queue                | Domain rules: cargo type, value thresholds |
| **Execution**    | Atomic rebooking with rollback                        | Transactional safety, priority ordering    |
| **Notification** | Contextual stakeholder updates                        | Personalized, proactive messaging          |

### 🎯 Intelligent Human-AI Collaboration

```
GENERAL, PERISHABLE, MAIL (80%) ──→ AUTO-APPROVED by agents ──→ Instant execution
LIVE_ANIMALS, HUMAN_REMAINS,   ──→ HUMAN APPROVAL required ──→ Manager/Executive
PHARMA, DANGEROUS_GOODS (20%)
```

**Key:** LLM evaluates cargo sensitivity, value ($100K+ threshold), constraint satisfaction → decides routing

---

## SLIDE 3: Technical Excellence & Market Value

### ⚙️ Architecture & Tech Stack

| Layer         | Technology               | Why                            |
| ------------- | ------------------------ | ------------------------------ |
| **Backend**   | FastAPI + Async Python   | High concurrency, real-time    |
| **Frontend**  | React + TypeScript + MUI | Rich approval UI, workflow viz |
| **Database**  | SQLite/PostgreSQL        | Production-ready schema        |
| **LLM**       | Gemini / AWS Bedrock     | Pluggable providers            |
| **Real-time** | WebSocket                | Live workflow updates          |

**Production-Ready Features:**

- ✅ Workflow state snapshots for replay
- ✅ Atomic execution with rollback capability
- ✅ Complete audit trail at every step
- ✅ Async throughout for scalability

### 💰 Market Potential & ROI

**Target Users:** Cargo airlines, freight forwarders, ground handlers (Emirates, DHL, Swissport)

| Stakeholder    | Value Delivered                             |
| -------------- | ------------------------------------------- |
| **Operations** | 80% less manual work, no 24/7 monitoring    |
| **Finance**    | $5.4M/year savings (100 disruptions/day)    |
| **Customers**  | Proactive updates, faster recovery          |
| **Compliance** | Full audit trail, sensitive cargo protocols |

**ROI Math:** 3hrs × $50/hr × 100/day = $15K → 15min × $50/hr × 20/day = $250 → **$14,750/day saved**

---

## SLIDE 4: Live Demo & Key Takeaways

### 🎬 Demo Flow (What You'll See)

1. **Disruption:** Flight 6E100 BOM→JFK cancelled → 5 AWBs impacted (2 PHARMA + 3 GENERAL)
2. **Detection Agent:** Classifies as HIGH severity, identifies sensitive cargo
3. **Impact Agent:** Calculates risk factors from actual booking_summary data (no hardcoding)
4. **Replan Agent:** Generates 3 recovery scenarios, scores and recommends best option
5. **Approval Routing:**
   - GENERAL cargo → **Auto-approved** → Rebooked in seconds
   - PHARMA cargo → **Manager queue** with LLM reasoning displayed
6. **Human Action:** Manager reviews, sees "Cold chain integrity risk" rationale, approves
7. **Execution:** Cargo rebooked to 6E102, customers notified with new ETAs

### 📊 Demonstrated Results

| Metric                 | Achievement                     |
| ---------------------- | ------------------------------- |
| Recovery time          | 3 hours → **15 minutes**        |
| Auto-processing rate   | **80%** (general cargo)         |
| Human oversight        | **20%** (sensitive only)        |
| Rollback success       | **100%** (no orphaned bookings) |
| Sensitive cargo safety | **Zero auto-processed**         |

### 🚀 Key Takeaways

1. **Agentic, not just generative** — AI reasons, decides, acts through 6 specialized agents
2. **Human-in-the-loop where it matters** — Smart escalation based on cargo sensitivity
3. **Real data, real decisions** — All values from booking_summary, not hardcoded
4. **Production-ready** — Rollback capability, audit trails, async architecture
5. **Massive ROI** — From hours to minutes, 80% automation, $5M+/year savings

> **iRecover:** Transforming cargo disruption from reactive firefighting to intelligent, automated recovery.

---

## Quick Reference: Key Phrases for Q&A

- "Our LLM doesn't just answer—it **reasons, decides, and acts**"
- "**80% automated, 100% auditable**—best of both worlds"
- "Only **sensitive cargo** needs humans—LIVE_ANIMALS, HUMAN_REMAINS, PHARMA, DG"
- "**6 specialized agents**, not one mega-prompt—better reasoning through specialization"
- "**From hours to minutes**—measurable, real-world impact"
  | Notification | 0.7 | Natural language |

### Sensitive Cargo Rules:

```python
SENSITIVE_CARGO_TYPES = [
    'LIVE_ANIMALS',    # → MANAGER approval
    'HUMAN_REMAINS',   # → EXECUTIVE approval
    'PHARMA',          # → SUPERVISOR/MANAGER approval
    'DANGEROUS_GOODS'  # → MANAGER approval
]
```

### Data Flow:

```
booking_summary → disruptions → awb_impacts →
recovery_scenarios → approvals → execution_steps → notifications
```

---

## Key Phrases to Remember

1. **"Agentic, not just generative"** - Our AI reasons, decides, acts
2. **"Human-in-the-loop where it matters"** - Smart escalation
3. **"From hours to minutes"** - Measurable impact
4. **"No hardcoded values"** - Real data, real decisions
5. **"Multi-agent orchestration"** - Specialized experts, coordinated workflow
6. **"Rollback capability"** - Production-ready reliability
7. **"80% automated, 100% auditable"** - Best of both worlds
