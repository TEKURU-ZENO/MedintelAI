# Demo & Showcase Guide

This document provides structured narratives to use when demonstrating the platform to clients, mentors, or educational stakeholders.

## 1. Setup

If the platform has just been deployed, run the seed script to populate the database with perfect demo data:
```bash
docker-compose exec backend python app/scripts/seed_demo.py
```
This generates the "Struggling Learner" telemetry profile required for Flow 2.

---

## 2. Demo Flow 1: The Showcase Interface
**Target Audience**: Mentors & Investors (High-level architecture).

**The Action**: Navigate to `/showcase`.
**The Narrative**: 
- Explain that this is the visual representation of the Phase 7 Adaptive Curriculum Engine. 
- Point out the **Curriculum Graph**. Show how "Straight Lines" are mastered, unlocking "Angular Capitals". 
- Explain that the recommendation engine is not picking random items. It evaluates Mastery Decay and Confidence Variance to suggest the *exact* next learning step (e.g., "Deep Mastery for CVC Words").

---

## 3. Demo Flow 2: The Emotional Tutor
**Target Audience**: Educational Clients & Parents (UX & AI).

**The Action**: Log in as a Child Profile. Click "Alphabet Practice".
**The Narrative**:
1. **The Good Trace**: Trace the letter perfectly.
   - *Highlight*: Notice the `<16ms` local rendering, the green checkmark, and the bouncy dopamine micro-animation.
2. **The Frustrated Trace**: Trace the letter backwards or intentionally scribble outside the lines.
   - *Highlight*: Notice that the audio engine does not yell or beep loudly. It plays a gentle correction. Wait 5 seconds.
3. **The Ghost Replay**: Let the canvas sit idle.
   - *Highlight*: The system detects hesitation/frustration and automatically deploys the animated Ghost Guide to physically show the child what to do. Explain that this prevents the child from hitting an educational wall.

---

## 4. Demo Flow 3: The Parent Dashboard
**Target Audience**: Parents & Stakeholders.

**The Action**: Navigate to the `/insights` Dashboard.
**The Narrative**:
- Explain that the dashboard is not a corporate BI tool. It is an empathetic reflection of the child's mind.
- Show the **Recommendations Card**. Point out that it doesn't just say "Practice A". It says *"Priority: High. Reason: Ready for double letters. Session Length: 5 mins."*
- Conclude that AksharabyasaAI takes the anxiety out of homeschooling by converting raw analytics into actionable, emotionally aware tutoring plans.
