# STUDY PROTOCOL FOR X FEED CAPTURE

This protocol ensures consistent, unbiased, and replicable data collection for analysing personalised recommendation feeds on X.

---

STUDY SCOPE INTERPRETATION

This study should be understood as a proof of concept designed to demonstrate a controlled methodology for analysing personalised recommendation systems.

The experiment was conducted using two accounts only, and therefore the results are not intended to be generalisable or definitive. Instead, the findings provide indicative insights into how recommendation systems may respond to identity signals and user behaviour under controlled conditions.

The primary contribution of this work lies in the design and implementation of a reproducible experimental framework, which can be scaled in future research to include larger sample sizes and more diverse user profiles.

---

PHASE 1 — Baseline Data Collection (Pre-Gender Assignment)

1. Account Creation

Two separate X accounts were created to evaluate potential differences in recommendation behaviour under controlled conditions.

Accounts:
- girluser112
- boyuser112

Controlled Setup:
Both accounts were configured identically to minimise initial algorithmic divergence.

Initial Interests Selected for BOTH accounts:
- News
- Movies & TV
- Technology
- Business & Finance
- Career
- Gaming
- Health & Fitness
- Memes
- Education
- Science
- Religion

At this stage, no explicit gender signals were assigned.

---

2. Data Collection Environment

To ensure consistency:
- Same physical device
- Same browser (Chrome)
- Same network connection
- No additional browser extensions
- No manual interaction outside defined protocol

---

3. Image Capturing Procedure

For each capture session:
1. Log in to the designated account immediately before capture
2. Navigate to the “For You” feed
3. Initiate automated scrolling via the Chrome extension
4. No manual interaction (no likes, clicks, or hovers)
5. Screenshots captured continuously for 2 minutes
6. Log out immediately after capture
7. Repeat for the second account under identical conditions

---

PHASE 2 — Gender Assignment

- boyuser112 assigned gender: Male  
- girluser112 assigned gender: Female  

No behavioural interactions introduced.

Purpose:
To isolate the effect of explicit gender signals on recommendation output.

---

PHASE 3 — Gendered Username Assignment

Usernames updated to reflect gender identity more strongly:
- Male account -> briansmith2211
- Female account -> rachelsmith221

All other variables remain unchanged.

Purpose:
To strengthen identity signals provided to the recommendation system.

---

PHASE 4 — Controlled Posting

Both accounts posted identical neutral content designed to introduce light engagement signals (general interest of politics).

Conditions:
- Same post content across both accounts
- No additional interaction beyond posting

Purpose:
To observe whether posting behaviour influences feed composition.

---

PHASE 5 — Controlled Engagement (Liking)

Both accounts liked the same selected tweet (e.g a politically aligned post).

Conditions:
- Same tweet liked by both accounts
- No additional engagement beyond this interaction

Purpose:
To introduce a minimal but explicit behavioural signal into the system.

---

PHASE 6 — Following Political Accounts (Balanced Input)

Both accounts followed the same set of political accounts:
- Equal number of left-leaning and right-leaning accounts

Conditions:
- Identical follow list across both accounts
- No additional interaction beyond following

Purpose:
To test whether balanced ideological input produces balanced recommendation output.

---

PHASE 7 — Strong Engagement Signals (Divergent Input)

Accounts were assigned opposing ideological signals:

- Male account followed predominantly left-leaning accounts
- Female account followed predominantly right-leaning accounts

Conditions:
- Clear ideological separation between accounts
- Continued automated capture under same conditions

Purpose:
To observe whether strong and opposing engagement signals lead to aligned recommendation outputs.

---

GENERAL CONTROL MEASURES (ALL PHASES)

- Identical capture conditions across accounts
- Same device, browser, and network
- No uncontrolled interactions outside defined actions
- Phases applied sequentially with only one variable changed at a time (where possible)

---

LIMITATIONS NOTE

While the protocol aims to isolate individual variables, later phases introduce controlled interactions (posting, liking, following) to simulate realistic user behaviour. These interactions were applied systematically across both accounts to maintain comparability.


