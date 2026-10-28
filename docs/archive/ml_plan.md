# AML Shield - Machine Learning Pipeline Plan

## 1. Goal
Build a Machine Learning and Graph Intelligence Proof-of-Concept (POC) for the **AML Shield** platform using the provided `mule_sample_data.csv`. The pipeline will focus entirely on the backend data science, ensuring the best possible detection results for identifying mule accounts, and providing explainable reasons for every flagged account.

## 2. Approach: Weak Supervision & Explainability
Since the provided dataset (`mule_sample_data.csv`) lacks explicit "fraud" or "mule" labels, we cannot immediately train a supervised model. Instead, we will use a **Weak Supervision** approach:
1. **Rule-Based Pre-Labeling**: Programmatically generate initial synthetic labels using strict heuristic rules defined in the problem statement (e.g., severe Pass-Through or Structuring behaviors).
2. **Supervised Learning**: Train an XGBoost / Random Forest classifier using these synthetic labels so the model can learn complex, non-linear interactions across all features.
3. **Anomaly Detection**: Use an unsupervised Isolation Forest alongside the supervised model to catch anomalous behaviors that rules might miss.
4. **Explainability**: Integrate **SHAP** to calculate feature importance, producing a human-readable "Reason for Flagging".

## 3. Implementation Steps (Python Pipeline)

### Step 1: Data Processing & Feature Engineering (`ml_pipeline/01_feature_engineering.py`)
Extract meaningful features from the raw transaction logs, aggregating at the Account (`ACID`) level.
- **Velocity Features**: Total transaction volume, transaction frequency, average transaction size.
- **Rule-Based Features**:
  - **Pass-Through**: High incoming volume immediately followed by outgoing transfers, leaving a near-zero balance.
  - **Structuring / Smurfing**: Repeated transactions just below the Rs. 50,000 threshold.
  - **Unusual Velocity**: High frequency of transactions in a short time.

### Step 2: Graph Intelligence (`ml_pipeline/02_graph_features.py`)
Use `networkx` to represent the flow of money as a directed graph.
- **Fan-In / Fan-Out**: Identify accounts receiving money from many sources (Fan-In) and sending it out to many others (Fan-Out).
- **Network Centrality**: Calculate PageRank and Betweenness Centrality for each account to find bottleneck or controller accounts.

### Step 3: ML Model Training & Explainability (`ml_pipeline/03_model_training.py`)
- Combine rule-based flags and graph features into a single matrix.
- Generate synthetic labels and train an XGBoost model.
- Train an Isolation Forest model on the same feature set.
- Generate a final composite **Risk Score (0-100)**.
- Use `shap` to extract the most important features that contributed to a high score.

### Step 4: Final Output Generation (`ml_pipeline/04_generate_report.py`)
Produce a final CSV report, `flagged_mule_accounts.csv`, containing:
- `ACID` (Account ID)
- `Risk_Score`
- `Is_Flagged` (Boolean)
- `Reason_for_Flagging` (e.g., "Flagged due to: High Structuring Activity, High PageRank Centrality")
