# LLM Cache, Quota and Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent recommendation caching, a daily per-user LLM quota, privacy-preserving logs, and 30-day retention.

**Architecture:** PostgreSQL stores `EntreeCacheRecommandation` and `JournalAppelLLM`. A focused service computes keys, cache lookups, quota and logs; Django signals invalidate each user's cache after task or preference changes. `RecommandationIAView` orchestrates cache, quota, LLM, fallback and log persistence.

**Tech Stack:** Django 6, Django REST Framework, PostgreSQL, standard-library `hashlib`, `hmac`, `secrets`.

**Spec:** `docs/llm-cache-quota-logging.md`

## Global Constraints

- Cache key format: `llm_reco:{user_id}:{hash}`, TTL exactly 24 hours.
- Invalidate cache on `post_save` and `post_delete` for `Tache` and `PreferenceUtilisateur`.
- Limit external LLM attempts to 10 per user per calendar day using `timezone.localdate()`.
- After quota: return valid cache, otherwise `_recommandation_meilleur_moment`.
- Persist only HMAC user hash, SHA-256 prompt hash, prompt length, duration, status, cache hit and error class; never prompt or response content.
- Purge logs older than 30 days on a cryptographically random 1% sample of endpoint requests.

---

### Task 1: Persistent Models and Migration

**Files:**
- Modify: `backend/api/models.py`, `backend/api/admin.py`
- Create: `backend/api/migrations/0001_llm_cache_and_logs.py`
- Test: `backend/api/test_llm_performance.py`

**Interfaces:**
- Produces `EntreeCacheRecommandation(utilisateur, cle, recommandation, expire_a)`.
- Produces `JournalAppelLLM(user_hash, prompt_hash, prompt_length, duration_ms, status, cache_hit, error_type)`.

- [ ] Write failing model tests for unique cache keys, user/expiry index behavior, and log fields with no raw user FK.
- [ ] Run `..\venv\Scripts\python.exe manage.py test api.test_llm_performance --keepdb`; expect import failure.
- [ ] Add both models, status choices, indexes and admin registrations; create and inspect the migration.
- [ ] Re-run the focused tests; expect pass.
- [ ] Commit `feat: persist LLM cache and call logs`.

### Task 2: Cache, Quota, Logs and Invalidation Services

**Files:**
- Create: `backend/api/recommandation_performance.py`, `backend/api/signals.py`
- Modify: `backend/api/apps.py`
- Test: `backend/api/test_llm_performance.py`

**Interfaces:**
- `construire_cle_cache(utilisateur, taches, preferences) -> str`
- `obtenir_cache(cle, now) -> dict | None`
- `quota_disponible(utilisateur, now) -> bool`
- `journaliser_appel_llm(...) -> None`
- `purger_journaux_anciens() -> int`
- `invalider_cache_utilisateur(utilisateur_id) -> None`

- [ ] Write failing tests for canonical key stability, expired cache miss, quota after ten external attempts, HMAC/SHA fields, forced purge, and all four signals.
- [ ] Run the focused tests and confirm each failure is caused by missing functions/signals.
- [ ] Implement the service with `transaction.atomic()` for quota accounting, `secrets.randbelow(100) == 0` for purge selection, and HMAC based on `settings.SECRET_KEY`.
- [ ] Connect signals through `ApiConfig.ready()`; do not log raw prompt, response, exception message or user ID.
- [ ] Re-run focused tests; expect pass.
- [ ] Commit `feat: add LLM cache quota and retention services`.

### Task 3: Endpoint Orchestration and Documentation State

**Files:**
- Modify: `backend/api/views.py`, `backend/api/tests.py`, `AGENTS.md`
- Test: `backend/api/tests.py`, `backend/api/test_llm_performance.py`

**Interfaces:**
- `RecommandationIAView.get()` returns the unchanged public recommendation contract for cache hit, LLM success, quota cache, quota fallback and LLM fallback.

- [ ] Write failing endpoint tests: cache hit skips `appeler_llm`; cache miss writes cache/log; quota returns latest valid cache; quota without cache returns rules; failed LLM logs an error and returns rules.
- [ ] Run `..\venv\Scripts\python.exe manage.py test api.tests.RecommandationIAEndpointTests api.test_llm_performance --keepdb`; expect endpoint assertions to fail.
- [ ] Integrate service calls in order: purge sample, compute key, cache, quota, LLM, parse, cache persist, fallback. Use only user-scoped data and retain the response contract.
- [ ] Mark the three section 5.4 cases `[x]` with exact implementation notes in `AGENTS.md`.
- [ ] Run full backend tests and frontend tests:
  `..\venv\Scripts\python.exe manage.py test --keepdb`
  and `npm test -- --watchAll=false --runInBand` with existing `NODE_PATH` and `CI=true` environment.
- [ ] Review diff and commit `feat: add LLM recommendation performance controls`.

## Self-Review

- Spec coverage: Tasks 1-3 cover persistent storage, 24-hour cache, all four invalidation signals, calendar quota, cache/rules quota paths, privacy fields, probabilistic 30-day retention and endpoint behavior.
- Placeholder scan: no implementation placeholders remain; all functions, files, tests and commands are named.
- Type consistency: Task 1 model names are the exact types consumed by Task 2, whose functions are the exact functions consumed by Task 3.
