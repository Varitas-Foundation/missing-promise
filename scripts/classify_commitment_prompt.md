You are classifying a privacy policy statement using speech act theory.

STATEMENT:
"{statement_text}"

COMPANY: {company}

TASK: Classify this statement into exactly ONE of three categories.

## Categories

**COMPANY_COMMITMENT** — A commissive speech act where the company binds itself to a limitation or promise about data handling. The company is constraining its OWN future behavior.

Key markers:
- Company negation: "does not sell", "will not share", "never collects"
- Protective promises: "we protect", "we ensure", "we guarantee"
- Self-imposed limitations: "we only use", "limited to", "restricted to"
- The company is the agent making a binding statement about what it WILL or WILL NOT do

**PRACTICE** — An assertive speech act describing what the company does, how it handles data, or factual statements about its operations. No binding promise is made.

Key markers:
- Data handling descriptions: "collects", "uses", "shares", "processes", "stores"
- Epistemic hedges: "may collect", "might share", "could use"
- Factual descriptions: "information is stored on", "cookies are used for"
- Disclaimers: "cannot guarantee", "is not responsible for", "does not control third-party"
- DNT non-response: "does not respond to Do Not Track" (describes behavior, not a privacy-protective promise)

**USER_CONTROL** — A statement describing what users CAN do, their rights, or capabilities offered to them. The USER is the agent, not the company.

Key markers:
- User capabilities: "users can", "you may", "customers have the right to"
- Rights descriptions: "right to delete", "right to access", "right to opt out"
- User actions: "opt out", "unsubscribe", "download your data", "manage preferences"

## Critical Edge Cases

1. "Does not sell personal data" → COMPANY_COMMITMENT (self-binding restriction)
2. "Does not respond to Do Not Track signals" → PRACTICE (describes behavior, NOT a privacy-protective promise)
3. "Does not control third-party practices" → PRACTICE (scope disclaimer, not self-binding)
4. "Cannot guarantee security" → PRACTICE (disclaimer of limitation, not a promise)
5. "Retains data only as long as necessary" → COMPANY_COMMITMENT (self-binding retention limit)
6. "Users are responsible for keeping passwords safe" → PRACTICE (obligation placed on users by company)
7. "California residents may exercise their rights" → USER_CONTROL (user capability)

## Examples

### COMPANY_COMMITMENT
- "The company does not sell or rent personal data to third parties for marketing purposes without explicit user consent."
- "The company will not discriminate against users who exercise their privacy rights."
- "The company does not knowingly solicit or collect personal information from children under 18 without parental consent."
- "Mobile information will not be shared with third parties or affiliates for marketing purposes."
- "The company retains personal data only as long as necessary for purposes stated in the privacy policy."

### PRACTICE
- "The company uses automatic collection technologies for operational, performance, functionality, and marketing purposes."
- "SOSi collects personal information disclosed through specified mechanisms on its website."
- "The company discloses all categories of personal data collected to recipients listed in the Privacy Statement."
- "Meta collects purchase and transaction data including credit card information from users."
- "The company does not process or respond to Do Not Track settings or signals from web browsers."
- "The company does not control third parties' privacy practices."

### USER_CONTROL
- "Users can delete saved audio content from playlists and libraries through the Spotify service."
- "Users have the right to object to personal data processing based on legitimate interests under GDPR."
- "Users can opt-out of having their activity on the websites available to Google Analytics."
- "Users can review and change their personal information by logging into the Website."
- "Customers may request access to their personal data."

Respond with ONLY this JSON (no other text):
{{"classification": "COMPANY_COMMITMENT" | "PRACTICE" | "USER_CONTROL", "reasoning": "1-2 sentence explanation"}}
