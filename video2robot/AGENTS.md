# AGENTS.md

## Repo Purpose
This workspace is used to make remote instances self-sufficient for integration, debugging, environment bring-up, and validation tasks.

When a task-specific markdown file exists under `current_task/`, follow it as the mission-specific source of truth.
When a remediation log is required, keep it updated throughout execution, not only at the end.

## Remote Instance Access

This task requires connecting to a remote EC2 instance before executing any environment setup.

Instance:
- Host: 34.252.135.22
- User: ec2-user
- SSH key: ./dm-isaac-g1.pem

Use the following SSH command:

```bash
ssh -i ./dm-isaac-g1.pem ec2-user@34.252.135.22

## Core Operating Principles
- Act like an operator, not a note-taker.
- Do not stop at identifying blockers when a fix is possible.
- Prefer the smallest fix that restores the target workflow.
- Diagnose before broad mutation, but keep momentum toward an end-to-end working result.
- Keep changes scoped to the task.
- Do not make unrelated refactors.
- Do not upgrade broad dependency sets unless required by a specific incompatibility.
- Prefer reversible, inspectable changes.

## Task File Rules
For any active task in `current_task/`:
- read the task file before making changes
- treat it as the mission definition and acceptance criteria
- create and maintain the required remediation log immediately
- update the remediation log after every meaningful action:
  - command run
  - file changed
  - config changed
  - package installed
  - environment variable added or modified
  - validation attempt
  - failed attempt
  - discovered blocker
  - working fix

## Logging Rules
Every meaningful attempt must record:
- timestamp
- exact command run or exact file changed
- short reason
- result
- success or failure
- why it worked or failed
- whether it is:
  - live-only / instance-local
  - persistent and should be integrated permanently

Failed attempts must remain in the final log.

## Secrets and Credentials
- Never hardcode secrets, tokens, passwords, API keys, or private keys in tracked files.
- Use `.env`, runtime environment variables, mounted secrets, SSH agent, or operator-provided credentials.
- If a task requires an API key or external credential, verify whether it already exists before declaring it missing.
- If the workflow is blocked by missing credentials, gather concrete evidence and document the exact missing requirement.

## Discovery First
For remote-instance tasks:
1. identify the host and runtime environment
2. inspect GPU, CUDA, Python, Conda, Docker, ports, and disk state
3. inspect the repository state
4. inspect submodules and external dependencies
5. establish a baseline before making changes

Do not assume:
- container names
- environment names
- port bindings
- GPU compatibility
- presence of model weights
- presence of API keys
- submodules are initialized
- GUI dependencies are installed

## Validation Standard
Never declare success based only on:
- import success
- environment creation
- package installation
- server startup alone
- partial pipeline execution

Success requires the real target workflow to run end-to-end.

## Fix Loop
Use this loop repeatedly:
1. inspect
2. hypothesize
3. run baseline validation
4. apply the smallest plausible fix
5. rerun the most relevant validation immediately
6. log the result immediately
7. classify the fix as temporary or persistent

## Persistent Fix Discipline
Whenever a live fix works, determine whether it should become a durable fix in:
- provisioning scripts
- Docker image build
- environment bootstrap scripts
- system packages
- startup scripts
- documentation
- repo defaults or templates

Document the exact persistent follow-up.

## External Docs and Upstream Instructions
When the task depends on an external repo or upstream instructions:
- read the upstream README and linked setup docs
- follow upstream steps faithfully before inventing custom workarounds
- if the upstream instructions fail in this environment, record:
  - which step failed
  - exact error
  - why it failed here
  - smallest viable workaround
  - whether the workaround should be made permanent

## Network and GUI Rules
For workflows with web UI or browser access:
- verify the server binds successfully
- verify the correct port
- verify firewall / security-group / port-forward constraints
- verify local and remote access path
- verify the non-GUI path separately from the GUI path

## Media/Input Rules
If a task requires test media:
- use a small, legally safe sample input
- store it in a predictable local path inside the workspace
- record the source and local path in the remediation log
- prefer a short video that exercises the target workflow quickly

## Definition of Done
A task is done only when:
- the target workflow has been executed end-to-end
- the required remediation log is complete
- the minimal working procedure is documented
- persistent DevOps follow-ups are clearly separated from live-only fixes