CREATE TABLE agreements (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    content_md TEXT NOT NULL,
    version VARCHAR(20) DEFAULT '1.0.0',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE agreement_signs (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    agreement_type VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    signed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, agreement_type, version)
);

INSERT INTO agreements (type, title, version, content_md) VALUES
('platform', 'Platform Terms of Service', '1.0.0',
'# ClawsJoy Platform Terms of Service

## 1. Acceptance of Terms
By accessing or using ClawsJoy Platform ("the Platform"), you agree to be bound by these Terms of Service.

## 2. Description of Service
ClawsJoy provides an AI agent marketplace where developers can publish and users can subscribe to AI agents.

## 3. User Obligations
- You must provide accurate registration information.
- You are responsible for maintaining the confidentiality of your account.
- You agree not to misuse the Platform for any illegal or unauthorized purpose.

## 4. Intellectual Property
- Developers retain ownership of their agents.
- The Platform owns its infrastructure, branding, and core technology.

## 5. Limitation of Liability
ClawsJoy is not liable for any damages arising from the use of agents downloaded from the Platform.

## 6. Termination
We reserve the right to suspend or terminate access for violations of these terms.

## 7. Changes to Terms
We may update these terms at any time. Continued use constitutes acceptance of changes.
'),
('agent', 'Agent Developer Agreement', '1.0.0',
'# Agent Developer Agreement

## 1. Developer Role
As an Agent Developer, you create and publish AI agents on the ClawsJoy Platform.

## 2. Agent Standards
- All agents must comply with platform content guidelines.
- Agents must not contain malicious code, exploit vulnerabilities, or collect user data without consent.
- Agents must function as described in their listing.

## 3. Revenue Sharing
- Developers receive 80% of subscription revenue.
- Payouts are processed monthly for balances over $10.

## 4. Updates and Maintenance
- Developers are responsible for keeping agents functional and secure.
- Breaking changes must be versioned appropriately.

## 5. Removal
The Platform reserves the right to remove agents that violate policies or receive excessive negative reviews.

## 6. Indemnification
Developers agree to indemnify the Platform against claims arising from their agents.
'),
('developer', 'Developer API Agreement', '1.0.0',
'# Developer API Agreement

## 1. API Access
This agreement governs access to ClawsJoy Platform APIs for third-party developers.

## 2. API Keys
- API keys are personal and must not be shared.
- Rate limits apply as specified in the documentation.

## 3. Usage Restrictions
- You may not use the API to compete with ClawsJoy core services.
- You may not reverse-engineer the API or platform infrastructure.
- Automated scraping of user data is prohibited.

## 4. Data Handling
- You must comply with all applicable data protection laws.
- User data obtained via API must be handled securely and deleted when no longer needed.

## 5. Service Availability
- API availability is provided on a best-effort basis.
- We may deprecate API versions with reasonable notice.

## 6. Termination
Violation of this agreement may result in immediate API key revocation.
');
