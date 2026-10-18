# Reliability release: login, answers, diagrams and vision

## Production configuration

Set these values in `/etc/teaching-assistant/app.env` before deploying:

```dotenv
ACCESS_TOKEN_EXPIRE_MINUTES=480
AUTH_IDLE_TIMEOUT_MINUTES=30
MAX_TOKENS=8192
CHAT_OUTPUT_TOKEN_RESERVE=8192
CHAT_MAX_CONTINUATIONS=2
VISION_MODEL_NAME=Pro/moonshotai/Kimi-K2.6
VISION_MAX_TOKENS=4096
VISION_ENABLE_THINKING=false
```

Vision keeps its existing SiliconFlow key and endpoint. Both chat images and PDF OCR use streaming requests with explicit error categories. SiliconFlow vision requests disable optional reasoning by default; this avoids waiting for a full non-streaming reasoning response. No embedding or Qdrant rebuild is needed.

Login JWTs now reference Redis sessions under `auth_session:v1:`. Existing JWTs without a session ID require a new login. Only foreground user interaction renews the 30-minute idle deadline; the absolute lifetime is eight hours. `POST /api/auth/activity` renews an existing session atomically; `POST /api/auth/logout` revokes it. Session timestamps are returned by login and `/api/auth/me`. Background polling does not renew sessions.

Chat SSE sends a `meta` frame before generation, and `done` only after saving a completed answer. `length` triggers up to two continuations in the same answer. A stream ending without `done` is a failure. Failed drafts are not saved as successful versions. Pending user messages remain visible and can be regenerated using the original client message ID and stored attachments. A `replace` frame can apply validated diagram repair without modifying the surrounding explanation.

## Mathematical diagrams

Mathematical graph, tree and Hasse illustrations use a fenced `math-diagram` JSON object:

```math-diagram
{"version":1,"kind":"graph","directed":true,"nodes":[{"id":"a","label":"a"},{"id":"b","label":"b"}],"edges":[{"from":"a","to":"a","label":"e1"},{"from":"a","to":"b","label":"e2"}],"annotations":["Missing edges belong in annotations, not in the actual edge set."]}
```

Node IDs must be unique strings. Up to 30 nodes and 80 edges are supported. Graphs allow loops and parallel edges. Trees require one root; trees and Hasse diagrams cannot contain cycles. Hasse edges point from smaller to larger elements. Existing Mermaid diagrams remain supported, with explicit edge-label colors in each scene.

## Verification and rollback

Run the backend unittest suite, `npm test`, `npm run lint` and `npm run build`. An optional browser regression check is available:

```powershell
# Start the frontend dev server in another terminal first.
# PLAYWRIGHT_MODULE_PATH may point at the bundled Playwright module directory.
node scripts/verify-reliability-ui.mjs
```

The browser check mocks only API requests and verifies all three scenes, real KaTeX and SVG rendering, 390px overflow, and 401 sign-out. It writes screenshots into the ignored `frontend/dist/qa` directory.

Before deployment, back up MySQL, storage and the production environment file. There is no SQL migration for this release. On rollback, restore the previous code and environment file, revoke only the `auth_session:v1:*` sessions (not other Redis keys), and sign in again. New mathematical diagrams remain stored as JSON code blocks; an older frontend will show their source rather than the SVG illustration.
