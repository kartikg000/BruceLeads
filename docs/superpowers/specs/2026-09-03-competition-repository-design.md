# Competition Repository Design

## Goal

Prepare BruceLeads for submission to an AI Growth & Agentic Commerce competition. The repository should help judges understand the business problem, agentic workflow, implementation, setup process, and responsible-use boundaries within a few minutes.

## Audience

- Competition judges evaluating usefulness, originality, AI integration, and execution
- Developers who want to run or inspect the project
- Potential users evaluating the lead-generation and outreach workflow

## Positioning

BruceLeads is an agent-assisted growth workflow for discovering high-intent business leads, enriching contact data, generating contextual outreach with Gemini, reviewing drafts, and sending through Gmail. It supports commerce by reducing the manual work between identifying demand and starting a qualified business conversation.

The repository will describe only implemented behavior. Future ideas will be explicitly labeled as roadmap items.

## README Structure

1. Product name, one-sentence value proposition, and competition-track positioning
2. Concise problem and solution statements
3. Implemented feature highlights
4. Agentic growth workflow: discover, enrich, reason/generate, human review, execute
5. Architecture diagram using portable Mermaid syntax
6. Technology stack
7. Screenshots/demo section using only real available assets; otherwise clear capture guidance
8. Quick start using the unified `localhost:8001` application
9. Configuration and credentials
10. Testing, build, and Windows packaging instructions
11. Responsible-use and legal guidance
12. Roadmap, contribution, security, and license links

## Supporting Repository Files

- `LICENSE`: MIT license matching the existing README claim
- `CONTRIBUTING.md`: setup, branch, testing, and pull-request expectations
- `SECURITY.md`: private vulnerability reporting guidance and supported version policy
- `.github/ISSUE_TEMPLATE/bug_report.yml`: structured bug reports
- `.github/ISSUE_TEMPLATE/feature_request.yml`: structured feature requests
- `.github/pull_request_template.md`: verification and scope checklist

## Visual Assets

No fabricated screenshots will be added. The README will include a demo section that can reference real screenshots after they are captured from the running application. Mermaid will provide an immediately renderable architecture visual on GitHub.

## Verification

- Every README command must match current scripts and port configuration
- All referenced files and internal links must exist
- No secrets, personal credentials, or local paths may be added
- Frontend production build must pass
- Backend flow tests and import check must pass
- Markdown must contain no unfinished placeholders such as `TBD` or `TODO`

## Out of Scope

- Adding new product functionality
- Publishing or pushing the repository
- Claiming autonomous behavior beyond the implemented workflow
- Sending real emails or performing large scraping runs
