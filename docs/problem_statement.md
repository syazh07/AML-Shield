Problem We Are Solving
Financial mule accounts are one of the most serious threats to the Indian banking system today. Criminals recruit ordinary people — students, unemployed youth, housewives — to open legitimate bank accounts and use them to launder illicit funds from cyber fraud, drug trafficking, and organized crime. Indian Overseas Bank, with 40 million customers across 3,400+ branches, a large Jan Dhan account base, and a strong NRI customer base (Tamil diaspora, Gulf remittances), faces a uniquely complex exposure to mule account operations. Existing rule-based AML systems catch patterns only after money has already moved — too late to prevent damage and too slow to satisfy RBI's escalating compliance expectations.
Our Solution — AML Shield
We're introducing AML Shield, a comprehensive anti-money laundering platform designed specifically for Indian Overseas Bank. This platform is fully operational within the bank's premises and uses multiple layers of intelligence to identify suspicious accounts from the moment they're created. It constantly monitors every transaction, using real-time data to map out entire networks of potential criminal activity. The platform also automates the process of reporting to regulatory bodies, all while ensuring that customer data remains secure within the bank's own data center. This means that every piece of customer information is kept safe and private, without being shared with external parties. By using graph intelligence, AML Shield can help Indian Overseas Bank stay one step ahead of financial crime and maintain the trust of its customers.
What Makes Our Solution Different
1. We Catch Mules Before They Open an Account
Most anti-money laundering systems only catch suspicious activity after a transaction has taken place. But we're changing that. Our system checks for potential issues right when a customer opens an account - whether that's in person at a branch or online. It's called the Onboarding Risk Engine, and it runs five checks all at the same time, getting the results back to you in just 30 seconds. This way, we can help prevent problems before they even start, rather than trying to fix them after the fact. By doing it this way, we're making the whole process more efficient and effective.
CKYC Registry Check — Has this Aadhaar or PAN been used to open multiple accounts across different banks this month?
Device Intelligence - Has the same phone or device been used to set up accounts with different names?
Graph Pre-Screening — Is this applicant's mobile number or email connected to any known mule network already in our graph database?
Watchlist Screening — Does this person appear on OFAC, UN, Interpol, or RBI defaulter lists?
ML Onboarding Score — Does the application pattern match historical mule account openings?
The outcome is a straightforward green, amber, or red decision, made even before the account is actually set up. If an account is flagged as red, it's blocked right away, essentially stopping the process in its tracks from the very beginning.

2. Real-Time Transaction Monitoring 
Here's how it works: every time a transaction happens through any of Indian Overseas Bank's channels - like UPI, NEFT, RTGS, IMPS, ATMs, mobile banking, or internet banking - Apache Flink takes a look at it. And it does this really fast, in under 100 milliseconds, using something called Complex Event Processing. What's cool about Flink is that it can remember what's happened with past transactions, so it can spot fraud patterns that might involve multiple steps - things that wouldn't be obvious if you just looked at one transaction on its own.
IOB-specific patterns we detect in real time:
Pass-Through — Money received and 90%+ transferred out within minutes, leaving near-zero balance
Structuring / Smurfing — Repeated transactions just below Rs. 50,000 threshold to avoid CTR reporting
Fan-In / Fan-Out — Multiple senders depositing into one account, immediately distributed to multiple receivers
Jan Dhan Spike — Dormant Jan Dhan account suddenly receiving multiple credits from unrelated sources (IOB-specific)
Gulf Remittance Layering — Inward SWIFT remittances from UAE, Saudi Arabia, Qatar immediately split via UPI to unrelated beneficiaries (IOB NRI-specific)
Impossible Travel — Same account logging in from Chennai at 8 AM and Delhi at 10:30 AM — physically impossible
Geo Inconsistency — Transaction location does not match registered address, VPN usage to mask location, device timezone manipulated to fake NRI status
Unusual Hours — Repeated high-value transactions between 1 AM and 4 AM

3. Graph Intelligence — See the Entire Criminal Network
What really sets us apart is our graph engine, which is powered by Neo4j. It creates a map of all the connections between different things like accounts, people, devices, phone numbers, virtual payment addresses, IP addresses, and beneficiaries. So, when we flag one account, it instantly shows us the entire network of connected accounts and relationships.
We run four graph algorithms continuously:
Louvain Community Detection — Identifies tightly connected clusters of mule accounts operating as a coordinated ring
PageRank — Identifies the controller account at the centre of the mule network.
Betweenness Centrality — Finds the money flow bottlenecks where layering is happening
Temporal Pattern Mining — Detects coordinated behaviour across accounts — "Account A always sends to B within 10 minutes of receiving from C"
Network Link Analysis using Neo4j's built-in graph algorithms scores accounts based on their network neighbourhood position. If an account is connected to a bunch of other accounts that are known to be bad, then it gets flagged too - even if it looks perfectly fine on its own. This is basically "guilt by association", but it's based on math and how the accounts are all linked together.
IOB-specific graph patterns we have built:
Jan Dhan Mule Rings — Multiple Jan Dhan accounts opened at same branch same week, all receiving from same sources
DBT Subsidy Diversion — PM-KISAN, MGNREGA, scholarship credits immediately diverted to unrelated accounts
If someone who already works with us helps a new customer get set up and that same person is linked to more than five suspicious accounts that get flagged, we automatically send the case to our special team that watches for insider threats.
Gulf Remittance Hawala Network — NRI accounts that never actually log in from abroad but receive large international remittances
4. ML Models Working in Parallel
Our machine learning ensemble combines ML models simultaneously to produce a single composite risk score:
XGBoost — Processes 50+ transaction features and produces a base risk score in under 10 milliseconds
Network Link Analysis — Using Neo4j's built-in graph algorithms scores accounts based on their network neighbourhood position
LSTM Autoencoder — Learns each account's normal behaviour pattern and flags any deviation — catches brand new mule tactics not in training data
Random Forest Classifier — Analyses transaction sequences to detect structuring and layering patterns
To come up with a final score, we combine the results of all four tests, giving more importance to some than others, and this gives us a Final Composite Risk Score that ranges from 0 to 100.
5. Every Alert Explained in Plain English and Tamil
Regulators want to know what's going on, and investigators need to understand the details. We provide both. With every alert, you get:
SHAP Values — Exact mathematical breakdown of which features drove the risk score ("device sharing contributed +34 points, pass-through pattern contributed +28 points, dormancy break contributed +18 points")
LLM-Generated Summary — Our on-premise Llama 3 model (running entirely inside IOB's data center, never sending data outside) generates a plain-English or Tamil language explanation of exactly why the account was flagged and what the investigator should do next
Even someone who is new to the field and doesn't know much about AML can quickly understand the alert summary and make a good decision right away.

6. AML Copilot — RAG-Powered Investigation Chatbot
Our investigation dashboard has a built-in tool called AML Copilot. It's like having a super knowledgeable colleague who's always available, 24/7. AML Copilot is a RAG-powered chatbot grounded in PMLA, RBI, and IOB case knowledge. It's based on a lot of information and can help with all sorts of questions and tasks. The AML Copilot is designed to be a helpful resource that can provide guidance and support whenever you need it.
Complete PMLA Act and PML Rules 2005
All RBI AML Master Directions and circulars
FATF 40 Recommendations and international typology reports
FIU-IND guidance notes for CTR, STR, CCR, NTR filing
IOB's own historical confirmed mule case database
IOB internal investigation notes and escalation procedures
An investigator can ask questions like "Why was this account flagged?" or "Show me similar past cases" and get a precise answer in just three seconds. They can also ask "What does PMLA say I should do next?" or "Are there other accounts connected to the same device?" - and receive a reliable response, backed by evidence, in no time. This helps them make informed decisions quickly, whether they're asking in English or Tamil.
Our chatbot is completely hosted on IOB's own GPU server, which uses Llama 3 technology. This means that no query, answer, or document is ever shared or leaves IOB's premises - everything stays right there.
7. Automated Regulatory Reporting
Every regulatory report IOB is required to file is generated automatically in the exact prescribed format:
CTR — Cash Transaction Reports for transactions above Rs. 10 lakhs
STR — Suspicious Transaction Reports filed within 7 working days of concluding suspicion, filed to FIU-IND
CCR — Counterfeit Currency Report
NTR — Non-Profit Organization Transaction Reports
CBWTR — Cross Border Wire Transfer Report, threshold ₹5 lakh
Compliance reports are automatically filled in using alert data and SHAP explanations. The compliance officer reviews and signs these reports digitally before sending them straight to FIU-IND through an API. The Camunda BPM workflow engine keeps track of deadlines and escalates issues when needed. By doing things this way, IOB's compliance team can save over 80% of the time they used to spend getting regulatory reports ready.
8. Bank-Grade Security — 100% On-Premise
Since this is a public sector bank handling the most sensitive customer data in the country, our security architecture is non-negotiable:
Thales Luna HSM — Physical hardware security module in IOB's data center for master encryption key management
Tokenisation — All PII replaced with tokens at the ingestion point before entering any analytics pipeline. Real Aadhaar and PAN numbers never flow through Flink, ML models, or graph engine
Zero Trust Architecture — No service or user is ever trusted by default. Every request verified every time using mTLS between all microservices
CyberArk PAM — Privileged access management with session recording and Just-In-Time access windows
Federated Learning — ML models can be trained collaboratively with other banks without any raw customer data being shared
Immutable Audit Trail — Every action, every decision, every model score logged in WORM (Write Once Read Many) storage, signed by the HSM, and available for RBI inspection on demand
IOB Active Directory Integration — No new user management. Every investigator uses their existing IOB credentials via SAML 2.0 SSO
9. Augments Existing System — Does Not Replace It
Our system doesn't replace the existing AML platform that IOB has already invested in, such as NICE Actimize or Oracle FCCM. Instead, it works on top of their current platform, enhancing every single alert with additional information like graph scores, machine learning scores, and easy-to-understand explanations. This way, IOB's initial investment remains safe and valuable. Our platform also helps identify high-risk cases that might have been missed by their current system, Actimize, making it a useful addition to their existing tools. By doing so, we ensure that IOB's existing investment is fully protected and still useful, while our system provides extra benefits to help them in their anti-money laundering efforts.
10.Low-Cost Solution - Designed to Fit Within PSU Procurement Constraints
We've built our entire system using open-source tools - things like Apache Kafka, Apache Flink, and Apache Spark. We're also using Neo4j Community, PyTorch, and a few other technologies like Llama 3 and LlamaIndex. Then there's PostgreSQL, Drools, Camunda BPM, Grafana, and Kubernetes. What's really important to us is that out of the 40 technologies we're using, 33 of them are completely free to use. This was a deliberate choice, because we wanted to make sure our system would fit within the procurement constraints of PSU and meet all the requirements of the GeM portal.
Tech Stack Summary
Onboarding Intelligence: CKYC API + Device Fingerprinting, Watchlist Screening (RBI / PEP / OFAC), ML Onboarding Risk Score
Real-Time Monitoring: Apache Flink (CEP Engine), Apache Kafka + Debezium CDC, MaxMind GeoIP (Geo Detection)
Graph Intelligence: Neo4j Graph Database, Louvain + PageRank Algorithms
ML Risk Scoring: XGBoost + LSTM Autoencoder, Feast Feature Store + MLflow, SHAP Explainability Engine
AI Copilot & Compliance: Llama 3 8B (On-Premise), LlamaIndex + pgvector (RAG), STR / CTR → FIU-IND Auto Filing
We didn't create a generic tool for anti-money laundering and implement it at Indian Overseas Bank. Instead, we designed this tool specifically with Indian Overseas Bank in mind, taking into account its unique situation, including its Finacle CBS system, the regulations it faces after being under PCA, its exposure to the Jan Dhan scheme, the profile of its Gulf NRI remittances, the fact that many of its staff speak Tamil, its budget constraints as a public sector undertaking, and its existing investment in Actimize. Every decision we made about the architecture of the tool was based on one of these specific factors related to Indian Overseas Bank.
Our system can identify suspicious accounts before they're even opened, and it can detect money laundering schemes as they happen. It also explains its decisions in a way that's easy to understand, in both English and Tamil. Plus, it automates all the necessary regulatory filings and creates a secure record of everything that happens, which the RBI can rely on. And the best part is, it does all this without ever moving any customer data out of IOB's secure data center.
