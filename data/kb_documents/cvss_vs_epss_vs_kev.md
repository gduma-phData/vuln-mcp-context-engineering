# Critical Semantic Distinctions: CVSS vs EPSS vs KEV

## The Three Dimensions of Vulnerability Assessment

These three scoring/classification systems measure fundamentally different things and MUST NOT be conflated in any semantic model.

### CVSS (Common Vulnerability Scoring System)
- Measures: SEVERITY (how bad the vulnerability could be IF exploited)
- Scale: 0-10 numeric score
- Nature: Theoretical technical potential
- Question answered: "How damaging could this be?"
- CVSS is NOT risk. CVSS is NOT exploit probability.

### EPSS (Exploit Prediction Scoring System)
- Measures: PROBABILITY (likelihood of exploitation in the next 30 days)
- Scale: 0-1 probability
- Nature: Predictive, data-driven, updated daily
- Question answered: "How likely is this to be exploited?"
- A low-CVSS vulnerability can have high EPSS if exploit code is widely available.

### CISA KEV (Known Exploited Vulnerabilities)
- Measures: CONFIRMED EXPLOITATION (binary: is or is not being exploited in the wild)
- Scale: Boolean (on the list or not)
- Nature: Historical/present fact, confirmed by CISA
- Question answered: "Is this being exploited RIGHT NOW?"
- Many KEV entries have Medium CVSS scores. KEV != Critical severity.

## Why This Matters for Semantic Modeling

When a user asks about "exploitability":
- CVSS exploitability subscore = theoretical ease of exploitation (technical metric)
- EPSS score = predicted probability of actual exploitation (statistical model)
- KEV status = confirmed active exploitation (observed fact)

These are THREE DIFFERENT CONCEPTS sharing similar terminology.

When a user asks about "risk":
- CVSS is NOT risk (it is severity only)
- True risk = severity (CVSS) x probability (EPSS) x asset value (context-dependent)
- No single score captures "risk" -- it requires combining multiple dimensions

When a user asks about "critical":
- CVSS Critical = base score 9.0-10.0 (technical severity band)
- Business-critical = context-dependent asset importance
- Always qualify: critical severity vs critical asset vs critical path
