# IEE 305 L-18: hosted LibreChat MCP demonstration

Updated October 26, 2026. Students need only a browser. This repository contains the complete deployment: clone or copy it to the EC2 host and run Docker Compose from the repository root.

The hosted MCP server is in `mcp/` and its classroom database is in `data/`.

## Components

| Service | Purpose | Public port |
| --- | --- | --- |
| caddy | HTTPS certificates and reverse proxy | 80, 443 |
| librechat | Browser UI, accounts, CreateAI model connection, MCP client | None directly |
| mongodb | Persistent accounts and conversations, with authentication | None |
| course-mcp | FastMCP tool with direct SQLModel queries and read-only SQLite access | None |

LibreChat reaches the CreateAI API and the public documentation MCP server over outbound HTTPS. It reaches the course MCP server through a private Docker network. The MCP tool queries its mounted SQLite file directly. Students receive neither model API keys nor direct database access.

Meilisearch, Redis, a RAG API, and a vector database are not required for this single-instance MCP exercise. Conversation search, file uploads, RAG, and unrelated tools are disabled. LibreChat may log a warning that its optional RAG API is unavailable; uploads are intentionally disabled. Outgoing account mail uses an external authenticated SMTP provider such as Amazon SES; a public mail server is not hosted on EC2.

## Before starting

- Linux EC2 instance with Docker Engine and Docker Compose v2. Start with roughly 2 vCPUs and 4 GiB RAM for a small rehearsal, then measure class concurrency. No GPU is needed.
- DNS hostname pointing to the instance's stable public address. Set only a working A record, or ensure any AAAA record also reaches this instance.
- Security group permitting inbound TCP 80/443 and administrative SSH only from your address. Do not open 3080, 8000, 8001, or 27017.
- A CreateAI Builder API base URL, project API key, and enabled model ID supporting tool calls. These are deployment inputs, not included credentials.
- Authenticated SMTP credentials and a verified sender. With SES, arrange production access rather than individually verifying every student recipient in its sandbox.
- Python 3 on the host for the optional secret-generation helper. Student laptops require none of these tools.

The supplied LibreChat all-in-one image is pinned by digest and reports v0.8.7. The course Python packages are pinned in each requirements.txt. The supporting image tags are explicit; the Python base tracks the 3.12 Bookworm image.

## Configure and start

From this folder on the EC2 host:

```bash
python3 scripts/init_env.py
```

This creates a private .env with independent random database, session, and credential-encryption secrets. It refuses to overwrite an existing .env. Keep these secrets stable: changing MONGO_PASSWORD does not change an existing MongoDB user's password, and changing CREDS_KEY/CREDS_IV can invalidate stored encrypted data.

Edit .env:

- COURSE_HOST: your hostname, without a scheme or path.
- ACME_EMAIL: address for certificate notices.
- CREATEAI_BASE_URL: the OpenAI-compatible API base, including the provider's required path. Do not use the Builder website URL or append /chat/completions.
- CREATEAI_API_KEY: your course project key.
- CREATEAI_MODEL: an exact model ID enabled for that project.
- EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_FROM: your SMTP settings. Port 587 with EMAIL_ENCRYPTION=starttls is the supplied starting point.
- ALLOW_PASSWORD_RESET: change to true after SMTP is configured, then verify delivery to an instructor test account before student onboarding.

Quote .env values containing special characters using Docker Compose's dotenv syntax. Never place keys in librechat.yaml or distribute .env to students.

```bash
docker compose config --quiet
docker compose pull
docker compose build
docker compose up -d
docker compose ps
```

Only Caddy publishes ports. Caddy obtains and renews certificates automatically once DNS and inbound connectivity are correct. Startup waits for the database, MCP server, and LibreChat health checks. Avoid publishing a second reverse proxy on the same host's ports 80/443.

The renderer applies CREATEAI_MODEL to the three model choices and validates the YAML using the pinned LibreChat schema. It retains API credentials as environment references. Placeholder CreateAI values are rejected at startup.

## Instructor and student accounts

Public registration and social login are disabled from the start.

Create the instructor account FIRST:

```bash
docker compose exec librechat npm run create-user -- instructor@asu.edu "Course Instructor" instructor --email-verified=true
```

Enter a strong password when prompted; do not leave the password blank. The first account becomes ADMIN. Do not place a password on the command line.

For students, create a local roster.txt containing one enrolled email address per line, with no header. Keep this roster out of any public repository. Then run:

```bash
docker compose exec -T librechat node config/course-users.cjs < roster.txt
```

The helper refuses to run before an initial account exists, skips existing emails without changing them, and creates ordinary accounts with independent cryptographically random passwords that it never prints or sends. It sends no email itself. Accounts are marked verified for login; possession of the email inbox is established through the password-reset link, because students are never given the random initial password.

Post the course URL in Canvas with these instructions:

1. Open the course site and choose Forgot password.
2. Enter the exact email address from the course roster.
3. Open the emailed link and choose a new password unique to this service.
4. Sign in and select a course demonstration.

Test this flow with an account in your own inbox first. SMTP delivery is required for this onboarding method. Leave password reset disabled until SMTP is ready. The pinned upstream invite-user script references a missing module, so this bundle deliberately uses the tested roster/reset workflow instead.

Roster changes can be applied by rerunning the helper. To revoke access, use the pinned application's ban-user command and its interactive prompts:

```bash
docker compose exec librechat npm run ban-user
```

Students cannot create or share MCP servers or saved Agents through the supplied configuration. The course choices are file-configured model specifications, so no manual Agent creation or sharing step is necessary. Recheck role permissions after any LibreChat upgrade.

## Classroom choices

All three choices use CREATEAI_MODEL:

- **Time-and-Motion Tools:** the course get_operator_summary tool.
- **Comparison — No Tools:** the same model with no attached MCP tools.
- **Documentation Tools:** the existing public documentation MCP service at https://developers.openai.com/mcp.

Start a fresh conversation for each comparison; previous tool results already in a conversation remain usable context. The comparison prompt explicitly states that database access is unavailable, so this is a teaching contrast rather than a controlled benchmark of the model.

Suggested prompts:

- “Use the time-and-motion tool to compare OP-14 and OP-03. Show observation counts and recorded minutes. Can these values rank productivity?”
- “Compare OP-53 and OP-99. Explain the difference between zero observations and a missing operator.”
- “Change OP-14's recorded time.” Discuss the actual response and the retrieval-only tool boundary.
- In Documentation Tools: “Use the documentation tools to find how an MCP server is connected to an agent. Cite the returned documentation.”

The Python structure follows L-17:

```text
mcp/
  server.py       Response model, engine setup, and tool: query and calculation
  models.py       Existing SQLModel table mappings
data/
  tam.db          Fixed classroom database, mounted read-only
```

The get_operator_summary tool opens a fresh SQLModel Session, finds the operator, retrieves its observations, sums the durations with an explicit loop, and returns OperatorSummary. The query and calculation are directly inside the decorated function. There is no time_motion.py helper.

OperatorSummary is defined directly in server.py above the tool and is not a database table. The response annotation exposes field types, constraints, and descriptions during MCP discovery. Constructing OperatorSummary validates the returned fields. Missing operators raise ToolError; SQLAlchemy failures become a short database error.

SQLite opens in mode=ro in addition to the read-only Docker mount. TAM_DATABASE is server configuration; the model cannot choose a database path or SQL query. No course-api container or requests dependency is needed. The original L-17 materials remain unchanged.

## Verify before class

```bash
docker compose exec course-mcp python smoke_test.py
```

Expected results on the supplied database:

| Operator | Observations | Recorded minutes |
| --- | ---: | ---: |
| OP-14 | 14 | 202.95 |
| OP-03 | 29 | 923.0 |
| OP-53 | 0 | 0 |
| OP-99 | Tool error | Missing operator |

The smoke test checks the output schema, structured results, and actual MCP calls over HTTP, the missing-record error, and SQLite write rejection. It requires no model key.

Then test in the browser with a normal student account:

1. Login and password reset both work; self-registration is unavailable.
2. The three configured choices are visible, and student server/agent creation is unavailable.
3. A real CreateAI request streams successfully.
4. The model selects the course tool, receives results, and answers from them. Plain chat success alone does not verify tool calling.
5. Inspect tool arguments and returned values. Confirm a fresh Comparison conversation has no course tool.
6. Verify documentation lookup and representative concurrent student requests.
7. Confirm the CreateAI course quota and any account-level limits cover the expected class activity.

No real CreateAI request is made by the supplied scripts. Its credentials, model behavior, quotas, and delivery to actual ASU inboxes must be rehearsed on the deployed service.

## Operations

```bash
docker compose logs --tail=100 librechat course-mcp
docker compose restart librechat
docker compose down
```

Use docker compose up -d --force-recreate librechat after changing .env; a restart alone does not update container environment variables. Rebuild after Python source changes with docker compose up -d --build course-mcp.

Named volumes preserve MongoDB, LibreChat files, and Caddy certificate state across container replacement. The SQLite source remains in data/tam.db. Preserve .env securely alongside backups. Do not use docker compose down -v unless intentionally deleting the deployment's persisted data.

For a consistent EC2/EBS backup, stop the stack, take snapshots of every volume holding the deployment and Docker data, and start it again. A live disk snapshot alone is not a tested application-consistent backup. Restore to a separate host and verify login and conversations before relying on the backup.

This bundle has no ongoing infrastructure automation and does not provision EC2, DNS, SES, or a CreateAI project.

## References

- [LibreChat custom endpoints](https://www.librechat.ai/docs/quick_start/custom_endpoints)
- [LibreChat MCP configuration](https://www.librechat.ai/docs/configuration/librechat_yaml/object_structure/mcp_servers)
- [MCP connection allowlist](https://www.librechat.ai/docs/configuration/librechat_yaml/object_structure/mcp_settings)
- [LibreChat authentication](https://www.librechat.ai/docs/configuration/authentication)
- [LibreChat email configuration](https://www.librechat.ai/docs/configuration/authentication/email)
- [TAT-C AI deployment reference](https://github.com/code-lab-org/tatc-ai)
- [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https)
- [Amazon SES production access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)
## Updating the earlier HTTP-adapter deployment

After backing up your configuration and replacing the bundle files, run:

```bash
docker compose up -d --build --remove-orphans
```

This recreates the MCP service with its database mount and removes the old course-api service from this Compose project. Account and conversation volumes retain their existing names. Keep your existing .env rather than generating new secrets. The earlier downloadable bundle is retained locally as IEE305_L18_Hosted_HTTP_Reference.zip.