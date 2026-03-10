# Visible Cognition Platform — Product Preview

This preview is a high-level walkthrough of the intended user experience and core product surfaces defined in the master architecture plan.

## Experience Snapshot

Visible Cognition Platform is designed to feel like a premium AI operations deck: cinematic, reactive, and readable.

- **Alive UI:** motion-guided transitions, organism activations, and state-linked visual feedback
- **Operational clarity:** dashboard-first orchestration with explicit provider and session health
- **Trust by design:** server-side key handling, strict auth boundaries, and auditable vault actions

## End-to-End User Journey Preview

1. **Landing + Sign Up**
   - User lands on a premium marketing/auth surface with a clear value proposition and account actions.
   - User can register with email/password or continue with Google/GitHub.

2. **Verification + Onboarding**
   - Email-verified users complete onboarding, select theme intensity, and optionally connect their first provider key.

3. **Dashboard Control Deck**
   - User sees provider organism status, quick launch to studio, recent sessions, health/cost panel, and onboarding guidance.

4. **Vault Setup (Get Key → Verify)**
   - Each provider card supports:
     - **Get API Key** (official outbound link)
     - **Documentation**
     - **Paste Key**
   - User follows guided flow: generate key externally, paste in vault, click verify, and watch organism state activate.

5. **Prompt Studio Launch**
   - User composes prompt with advanced controls (templates, optimizer, presets, output style, revision passes).

6. **Live Chamber Run**
   - Real telemetry drives visual behavior: ingress, votes, generation/revision, contradiction signals, synthesis, and final release.

7. **Replay + History**
   - User replays previous sessions with timeline/event views and export support.

## Surface-by-Surface Preview

### Landing / Auth
- Premium hero + concise product narrative
- Email auth + OAuth (Google/GitHub)
- Verification and reset-password flows

### Dashboard
- Provider organism grid
- Orchestration/session status
- Quick actions and activity feed
- Cost/health/security summary

### Vault
- Encrypted key lifecycle: save, validate, rotate, delete
- Provider diagnostics and masked key previews
- Guided key acquisition support for all initial providers

### Prompt Studio
- Large prompt workspace with structured controls
- Template/snippet support and profile save workflows
- Run-to-chamber flow for visible execution

### Chamber
- Event-driven visual scene with side rail feed and answer panel
- Provider state transitions mapped to real telemetry events
- Readable layout on desktop and simplified premium mobile experience

### History / Replay
- Session list + filters
- Trace/event table + final output snapshot
- Replay timeline and JSON export

## What “Production-Grade” Means in This Plan

- No placeholder pages or non-functional surface actions
- Typed contracts for telemetry and orchestration boundaries
- Server-side only provider calls and secret handling
- Strong route/auth guards and verified-email gating
- Phase-based delivery with testable milestones

## Preview Acceptance Checklist

A practical readiness preview for implementation:

- [ ] Auth + verification + OAuth paths operational
- [ ] Vault UX includes get-key links + inline guidance + verify action
- [ ] Dashboard shows provider readiness before first run
- [ ] Studio launches real orchestration runs
- [ ] Chamber visuals are wired to real telemetry contract
- [ ] History supports replay and export
- [ ] No stub buttons or placeholder routes

## Related Documents

- [Visible Cognition Platform — Master Architecture Plan](./visible-cognition-platform-master-architecture.md)
