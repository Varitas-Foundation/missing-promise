# Supplementary Reference Sample: 60 Marker-Free Statements

**What to do.** For each of the 60 statements below, type one of `CC`, `P`, or `UC` after `LABEL:`. Add a note after `NOTES:` only if the case is hard or you want to record why. Nothing else in this file needs editing. When done, run:

```bash
python research/empty_promise/scripts/score_supplementary_sample.py
```

**Why this sample exists.** The 200-statement reference set contains only four commitments of the *marker-free affirmative* type ("the company uses SSL encryption to protect data"; five after the September 5, 2026 correction of one reference label, made after this sample was adjudicated), yet that type is roughly half of the corpus commitment class and is exactly where the two judge panels disagree. Every statement here is marker-free: no "does not," "will not," "never," "cannot," "will," "shall," "must," "only," or performative verb. Panel labels are deliberately withheld so they cannot anchor you. Statements are shuffled across strata and corpora.

---

## Decision guide

Apply the two-part test from Section 3.1 of the paper. A statement is a **company commitment (CC)** when both hold:

1. **Protective direction.** It constrains the company's *own* future conduct toward user data, or the exercise of privacy rights, in a direction a user would regard as protective: limiting collection, use, sharing, retention, or exposure, or foreclosing a penalty for exercising a right.
2. **Falsifiability.** Some specific company behavior would violate it. Ask whether an FTC enforcement attorney could treat it as a material promise under the deception standard.

Otherwise it is a **practice (P)** if the company is the agent, or **user control (UC)** if the user is the agent.

### The boundary this sample is about

Affirmative present-tense protective statements are the hard case. The operative rule the paper states:

| Reads as | Label | Example |
|---|---|---|
| Names a specific measure or a bounded scope that a concrete behavior would violate | **CC** | "The company encrypts payment data in transit using TLS." / "The company deletes inquiry data within twelve months." / "The company asks for affirmative consent before sharing data outside its corporate family." |
| Purely aspirational, no measure, no ceiling, nothing specific to breach | **P** | "The company takes steps to protect your data." / "The company values your privacy." / "The company uses reasonable safeguards." |
| Affirmative commissive to *perform* a practice (binds, but limits nothing) | **P** | "The company will share your data with partners." |
| Describes a data flow, a capability, or a state of affairs | **P** | "The company collects information you provide." / "Third parties use cookies subject to their own policies." |
| Obligation placed on the user, or a scope disclaimer | **P** | "Users are responsible for keeping passwords safe." / "This policy does not apply to third-party sites." |
| User is the agent: rights, options, actions | **UC** | "Users can request deletion of their account." / "California residents may exercise their rights." |

### Edge cases the classification prompt fixes (for consistency, not for these statements)

1. "Does not sell personal data" is CC. 2. "Does not respond to Do Not Track signals" is P. 3. "Does not control third-party practices" is P. 4. "Cannot guarantee security" is P. 5. "Retains data only as long as necessary" is CC. 6. "Users are responsible for passwords" is P. 7. "California residents may exercise their rights" is UC.

### Things to ignore

- Whether the statement is *true* or the company is *reputable*. Judge the speech act only.
- Whether the sentence is well written. These are extracted paraphrases, not policy prose.
- Rights-based user statements ("users have the right to") stay UC even though they imply a company duty; the paper tests that boundary separately.

---

## Statements

### 1. msn.com  (OPP-115 2015)
<!-- id: msn.com_007_s4 -->

> The company removes cookies and other cross-session identifiers after 18 months of retention.

LABEL: CC
NOTES: Named retention ceiling: identifiers removed after 18 months. Retaining them longer would violate it.

### 2. avast  (OPPT 2026)
<!-- id: avast_009_s1 -->

> The company maintains administrative, technical, and physical safeguards for personal data protection.

LABEL: P
NOTES: The administrative, technical, and physical safeguards formula names categories of measures, not measures. Nothing specific to breach.

### 3. playstation.com  (OPP-115 2015)
<!-- id: playstation.com_039_s2 -->

> The company follows United States data protection and privacy regulations when processing personal data in the United States.

LABEL: P
NOTES: Generic assertion of legal compliance. It names no standard or measure and adds nothing to obligations the law already imposes. Contrast the reference set's HIPAA statement, which names a specific statute with substantive rules.

### 4. uber  (OPPT 2026)
<!-- id: uber_046_s4 -->

> Uber retains user-submitted selfies for identity verification for 3 years.

LABEL: CC
NOTES: Definite retention period for biometric selfies; retaining them past three years would violate it. Boundary case: the paraphrase says 'retains for', not 'deletes after', and a reader who treats retention schedules as descriptive would call it P.

### 5. betterhelp  (OPPT 2026)
<!-- id: betterhelp_032_s4 -->

> BetterHelp remains liable under DPF Principles if its agents process personal data inconsistently with DPF Principles.

LABEL: P
NOTES: DPF onward-transfer liability recital. It allocates legal responsibility and describes a legal state of affairs; it does not limit collection, use, sharing, retention, or exposure.

### 6. flock-safety  (OPPT 2026)
<!-- id: flock-safety_008_s1 -->

> Flock complies with the Data Privacy Framework Principles for all personal data transfers from the EU.

LABEL: CC
NOTES: Adherence to a named framework whose Principles limit use, onward transfer, and retention, bounded to EU transfers. The FTC treated false Safe Harbor and Privacy Shield compliance claims as deceptive, so the representation is material and falsifiable.

### 7. instacart  (OPPT 2026)
<!-- id: instacart_013_s1 -->

> The company employs reasonable administrative, physical, and technical measures to protect personal information from unauthorized access, use, and disclosure.

LABEL: P
NOTES: The 'reasonable measures' formula; the guide's explicit P example.

### 8. epic-games  (OPPT 2026)
<!-- id: epic-games_007_s2 -->

> Epic collects parent/guardian email address when a user indicates they are a child to provide notice and seek consent.

LABEL: P
NOTES: Describes a collection flow within the COPPA consent process.

### 9. allstate.com  (OPP-115 2015)
<!-- id: allstate.com_001_s1 -->

> Allstate respects user privacy and works to protect personal information.

LABEL: P
NOTES: Aspirational; no measure, no ceiling.

### 10. stripe  (OPPT 2026)
<!-- id: stripe_036_s4 -->

> State laws and individual companies may provide additional sharing limitations beyond federal law requirements.

LABEL: P
NOTES: GLBA model-notice boilerplate describing the legal landscape; state law and other companies are the agents.

### 11. reddit.com  (OPP-115 2015)
<!-- id: reddit.com_006_s3 -->

> Reddit logs and retains indefinitely the IP address from which an account is initially created.

LABEL: P
NOTES: Describes a data flow; indefinite retention limits nothing.

### 12. walmart  (OPPT 2026)
<!-- id: walmart_019_s1 -->

> Walmart adheres to Digital Advertising Alliance self-regulatory principles for interest-based advertising.

LABEL: CC
NOTES: Adherence to a named self-regulatory code with substantive requirements (honoring opt-outs, sensitive-data limits, data security), bounded to interest-based advertising; the program's accountability mechanism enforces it and the FTC can reach the claim under Section 5. Weakest member of the framework family: relabel P if adherence to an industry code is read as a program description.

### 13. peloton  (OPPT 2026)
<!-- id: peloton_033_s2 -->

> Peloton shares Fitness Data when authorized by the user or their authorized representative.

LABEL: P
NOTES: Describes conditional sharing. The main verb is the practice and no exclusivity is stated; it would be CC as 'shares only when authorized'.

### 14. fool.com  (OPP-115 2015)
<!-- id: fool.com_052_s2 -->

> By using the sites and providing personal data, users consent to data processing in the United States under US laws.

LABEL: P
NOTES: Deemed-consent term imposed on users by use of the site. It is not a user option or right, so not UC, and it constrains nothing the company does.

### 15. cellebrite  (OPPT 2026)
<!-- id: cellebrite_010_s3 -->

> Data transfers outside Europe are conducted under standard data protection contract clauses with adequate safeguards determined by the EU Commission.

LABEL: P
NOTES: Describes the transfer mechanism (standard contractual clauses). The reference set adjudicated the same form (L3Harris) as P.

### 16. gamestop.com  (OPP-115 2015)
<!-- id: gamestop.com_029_s5 -->

> Third-party advertisers have no access to user contact information stored by the company unless the user chooses to share it.

LABEL: CC
NOTES: Negation in substance: advertisers have no access to contact information absent user choice. Limits third-party exposure with a bounded exception.

### 17. sidearmsports.com  (OPP-115 2015)
<!-- id: sidearmsports.com_011_s2 -->

> When personal information is collected by a third party other than SIDEARM Sports, users are notified at the same time.

LABEL: P
NOTES: Notification practice. Notice is transparency, not a limit on collection, use, sharing, retention, or exposure, and the user is the recipient rather than the agent; the reference set labeled comparable notice-mechanism statements P. Relabel CC if contemporaneous notice is read as a falsifiable protective undertaking.

### 18. github  (OPPT 2026)
<!-- id: github_019_s1 -->

> GitHub uses administrative, technical, and physical security controls to protect personal data.

LABEL: P
NOTES: Same safeguards formula as 2.

### 19. amazon  (OPPT 2026)
<!-- id: amazon_006_s3 -->

> The company follows the Payment Card Industry Data Security Standard when handling credit card data.

LABEL: CC
NOTES: Named external technical standard for a bounded data type. PCI DSS compliance is auditable, and non-compliance would violate the representation.

### 20. meta  (OPPT 2026)
<!-- id: meta_138_s1 -->

> Meta shares information with other Meta Companies to promote safety, security and integrity.

LABEL: P
NOTES: Describes an intra-group data flow.

### 21. perplexity  (OPPT 2026)
<!-- id: perplexity_014_s2 -->

> For enterprise customers, chat content, file uploads, and metadata are not used for training or fine-tuning AI models.

LABEL: CC
NOTES: Passive negation limiting use: enterprise data is not used for training. Bounded scope, and training on it would violate the statement.

### 22. barnesandnoble.com  (OPP-115 2015)
<!-- id: barnesandnoble.com_010_s2 -->

> The company respects user preferences regarding their personal information.

LABEL: P
NOTES: Aspirational; names no mechanism for honoring preferences.

### 23. southwest-airlines  (OPPT 2026)
<!-- id: southwest-airlines_018_s2 -->

> The company makes reasonable good faith efforts to remove or anonymize posted content about minors upon user request.

LABEL: CC
NOTES: Specific action (remove or anonymize) on a specific trigger (request) for a bounded class (content about minors), limiting exposure. The hedge 'reasonable good faith efforts' softens the standard of performance, not the existence of the undertaking; refusing such requests would violate it. Relabel P if hedged effort language is treated as aspirational.

### 24. geocaching.com  (OPP-115 2015)
<!-- id: geocaching.com_024_s1 -->

> Users outside the United States consent to transfer of personal information to the United States.

LABEL: P
NOTES: Deemed-consent term, as in 14.

### 25. earthkam.org  (OPP-115 2015)
<!-- id: earthkam.org_010_s1 -->

> The company limits the number of people with physical access to its database and servers.

LABEL: CC
NOTES: Names a control (restricted physical access to the database and servers) and carries the self-limitation marker 'limits'. Access-control subtype: relabel together with 33 if only named technologies count as measures.

### 26. spotify  (OPPT 2026)
<!-- id: spotify_018_s1 -->

> Spotify Service has a minimum age limit that varies by country or region.

LABEL: P
NOTES: State of affairs about eligibility.

### 27. lexisnexis  (OPPT 2026)
<!-- id: lexisnexis_021_s2 -->

> The company may require users to verify their identity to protect privacy and security when processing rights requests.

LABEL: P
NOTES: Permissive 'may require'; identity verification is a procedural step in request handling. The reference set adjudicated the same form (Shopify) as P.

### 28. dcccd.edu  (OPP-115 2015)
<!-- id: dcccd.edu_015_s1 -->

> DCCCD has implemented industry best practices in security measures to prevent information interception and abuse.

LABEL: P
NOTES: 'Industry best practices' names no measure.

### 29. eyematch-ai  (OPPT 2026)
<!-- id: eyematch-ai_002_s2 -->

> The company uses encryption to secure user photos.

LABEL: CC
NOTES: Names a specific measure (encryption) for a bounded object (photos); the paradigm marker-free affirmative commitment in the guide.

### 30. everydayhealth.com  (OPP-115 2015)
<!-- id: everydayhealth.com_041_s1 -->

> The company prioritizes security of personal information and undertakes reasonable security measures to protect data on servers.

LABEL: P
NOTES: Aspirational; 'reasonable security measures'.

### 31. www.loc.gov  (OPP-115 2015)
<!-- id: www.loc.gov_003_s1 -->

> The Library collects several types of information automatically without commercial marketing use.

LABEL: CC
NOTES: The informative content is a use limitation: the collected information carries no commercial marketing use, which is falsifiable and protective; the collection clause is the frame. Relabel P if the main verb governs the label.

### 32. epic-games  (OPPT 2026)
<!-- id: epic-games_009_s3 -->

> Epic receives parent or guardian email addresses directly from child users for parental consent verification.

LABEL: P
NOTES: Describes a collection flow.

### 33. microsoft  (OPPT 2026)
<!-- id: microsoft_014_s2 -->

> Microsoft stores personal data on computer systems with limited access in controlled facilities.

LABEL: CC
NOTES: Names two controls (limited access, controlled facilities) for stored data. Access-control subtype, paired with 25.

### 34. steampowered.com  (OPP-115 2015)
<!-- id: steampowered.com_017_s2 -->

> Valve has taken reasonable steps to protect user information from unauthorized access or disclosure.

LABEL: P
NOTES: 'Reasonable steps'; aspirational.

### 35. united-airlines  (OPPT 2026)
<!-- id: united-airlines_027_s1 -->

> The company maintains physical, electronic, and procedural safeguards to protect user information.

LABEL: P
NOTES: Safeguards formula, as in 2.

### 36. disinfo.com  (OPP-115 2015)
<!-- id: disinfo.com_016_s1 -->

> Cookies and web beacons used by the company are not linked to personal information.

LABEL: CC
NOTES: Negation in substance limiting data combination: tracking identifiers are not linked to personal information. Linking them would violate it.

### 37. redorbit.com  (OPP-115 2015)
<!-- id: redorbit.com_006_s2 -->

> The company stores user profiles containing information about individual users' viewing preferences.

LABEL: P
NOTES: Describes stored data.

### 38. minecraft.gamepedia.com  (OPP-115 2015)
<!-- id: minecraft.gamepedia.com_009_s2 -->

> The company takes children's privacy seriously and encourages parental involvement in children's online experience.

LABEL: P
NOTES: Aspirational.

### 39. barnesandnoble.com  (OPP-115 2015)
<!-- id: barnesandnoble.com_053_s2 -->

> Protecting privacy and security of personal information is a priority for Barnes & Noble.

LABEL: P
NOTES: Aspirational.

### 40. earthkam.org  (OPP-115 2015)
<!-- id: earthkam.org_009_s1 -->

> The company takes reasonable steps to verify parent/guardian identity before granting access to child's personal information.

LABEL: CC
NOTES: A verification gate before disclosure of a child's data, limiting exposure; parallels the reference commitment 'asks for affirmative consent before sharing'. 'Reasonable steps' hedges the method, not the gate. Relabel P together with 23 if hedged process statements are treated as aspirational.

### 41. meta  (OPPT 2026)
<!-- id: meta_075_s3 -->

> The company stops collecting GPS information when users turn off Location Services on their device.

LABEL: CC
NOTES: Limits collection on a concrete trigger; collecting GPS data after Location Services is off would violate it. The company is the agent, so not UC.

### 42. everydayhealth.com  (OPP-115 2015)
<!-- id: everydayhealth.com_035_s3 -->

> The company deletes and removes a child's information from systems upon parent or guardian request.

LABEL: CC
NOTES: Specific action (deletion) on a specific trigger (parental request), limiting retention and exposure. The company is the agent, unlike the reference UC statement in which parents may email to request removal.

### 43. msn.com  (OPP-115 2015)
<!-- id: msn.com_007_s3 -->

> The company removes the entirety of IP addresses after 6 months of retention.

LABEL: CC
NOTES: Named retention ceiling, as in 1.

### 44. lodgemfg.com  (OPP-115 2015)
<!-- id: lodgemfg.com_001_s1 -->

> The company transmits transactions using 128-bit secure socket layers (SSL) for data protection.

LABEL: CC
NOTES: Named measure (128-bit SSL) for a bounded object (transactions).

### 45. mlb.mlb.com  (OPP-115 2015)
<!-- id: mlb.mlb.com_031_s5 -->

> Children under thirteen without parental consent receive a message indicating ineligibility when attempting to access restricted services.

LABEL: P
NOTES: Describes the mechanics of an age gate from the child's side (a message). The protective content, no restricted service to under-13s without consent, is implied rather than stated, and the reference set labeled the comparable child-account handling statement P. Relabel CC if the implied gate is read as the undertaking.

### 46. internetbrands.com  (OPP-115 2015)
<!-- id: internetbrands.com_100_s2 -->

> The company has a policy not to disclose personal information to third parties for direct marketing if residents opt-out.

LABEL: CC
NOTES: Negation in substance: a policy not to disclose to third parties for direct marketing once residents opt out. Limits sharing and forecloses disregarding an exercised right (Shine the Light recital).

### 47. meta  (OPPT 2026)
<!-- id: meta_100_s2 -->

> Third-party apps can retain information previously shared by users even after access expires.

LABEL: P
NOTES: Third-party capability; not protective.

### 48. bankofamerica.com  (OPP-115 2015)
<!-- id: bankofamerica.com_075_s2 -->

> Users may still receive untailored advertising from Bank of America even after opting out of tailored advertising.

LABEL: P
NOTES: Caveat on the limits of an opt-out. It describes a state of affairs, and receiving advertising is not a user capability.

### 49. pimeyes  (OPPT 2026)
<!-- id: pimeyes_016_s2 -->

> The company avoids targeting social media, social networking platforms, and professional networks on search engines and crawlers.

LABEL: CC
NOTES: Limits collection scope: crawlers do not target social and professional networks. 'Avoids' is a soft verb, but the named scope makes a violating configuration concrete.

### 50. zacks.com  (OPP-115 2015)
<!-- id: zacks.com_004_s1 -->

> During registration, Zacks.com includes user contact information on the Zacks Investment Research opt-in marketing list.

LABEL: P
NOTES: Describes a marketing-list practice; not protective.

### 51. tesla  (OPPT 2026)
<!-- id: tesla_025_s7 -->

> Tesla applies privacy-preserving techniques or removes personal data from reports before sending analytics to Tesla.

LABEL: CC
NOTES: Names a measure (removal of personal data, or privacy-preserving techniques) at a fixed point (before transmission), limiting collection. The disjunction weakens the named measure; relabel P if 'privacy-preserving techniques' is read as aspirational.

### 52. archives.gov  (OPP-115 2015)
<!-- id: archives.gov_052_s2 -->

> Users expressly consent to network traffic monitoring when using this government computer system.

LABEL: P
NOTES: Deemed-consent banner term, as in 14.

### 53. roblox  (OPPT 2026)
<!-- id: roblox_007_s1 -->

> The company automatically sets stronger privacy settings for accounts of users under 13 years old.

LABEL: CC
NOTES: The company sets protective defaults for a bounded group; creating under-13 accounts with standard settings would violate it. 'Stronger' is relative, so relabel P if the measure is judged unnamed.

### 54. gravy-analytics  (OPPT 2026)
<!-- id: gravy-analytics_029_s2 -->

> The company deletes personal information from its systems if discovered from children under 16.

LABEL: CC
NOTES: Specific deletion on a specific trigger for a bounded group; the affirmative form of the standard COPPA deletion commitment.

### 55. foxsports.com  (OPP-115 2015)
<!-- id: foxsports.com_004_s1 -->

> FSD Services are not targeted to children and are designed for a general audience.

LABEL: P
NOTES: Audience and design statement; it says nothing about data handling. Contrast 'does not knowingly collect from children', which is CC.

### 56. safegraph  (OPPT 2026)
<!-- id: safegraph_007_s1 -->

> SafeGraph uses reasonable measures to protect information against unauthorized access, disclosure, alteration, or destruction.

LABEL: P
NOTES: The 'reasonable measures' formula.

### 57. acbj.com  (OPP-115 2015)
<!-- id: acbj.com_005_s1 -->

> The company collects personally identifiable information with user specific knowledge and consent.

LABEL: P
NOTES: Collection description with a consent qualifier. The reference set adjudicated the same form (Cellebrite, 'collects ... with explicit user consent') as P. Relabel CC if the qualifier is read as 'only with knowledge and consent', which covert collection would violate.

### 58. binance  (OPPT 2026)
<!-- id: binance_028_s3 -->

> Binance retains date of birth information when underage individuals attempt KYC identity verification to prevent re-registration and protect platform security.

LABEL: P
NOTES: Retention for a security purpose with no ceiling; not protective toward the data subject.

### 59. redfin  (OPPT 2026)
<!-- id: redfin_035_s1 -->

> Redfin retains personal information as long as the user actively uses the Services.

LABEL: P
NOTES: States the basis of the retention period without a ceiling: no 'only' or 'no longer than', and nothing about retention after use ends. Relabel CC if 'as long as' is read as exclusive, which would align it with 4.

### 60. aol.com  (OPP-115 2015)
<!-- id: aol.com_040_s1 -->

> AOL Inc. complies with the U.S.-EU Safe Harbor Framework regarding collection, use, and retention of personal information from EU member countries.

LABEL: CC
NOTES: Safe Harbor compliance claim for a bounded population. The FTC brought deception actions against false Safe Harbor claims, and the Framework's principles limit use, onward transfer, and retention.
