# TOPOLOGY-DECISIONS

> **Program:** PRODUCT-02  
> **Owns:** Where capabilities live (Project / Workspace / Settings / Reserved)  
> **Patch:** PRODUCT-02-BLUEPRINT-PATCH-01 · OD-02 · OD-03 · OD-09  
> **Status:** OWNER-APPROVED · `owner_freeze` NOT SET

---

## 1. Primary invariant (OWNER-APPROVED)

**Project Command Center** is the main container for the commercial path of **one idea**.

Core capabilities are **not** separate products.

---

## 2. Placement map

### Project Command Center

| Capability | Notes |
|------------|-------|
| Intake | Project stage |
| Research | Project stage |
| Strategy | Project stage |
| Launch subtree | Offer, Channels, Budget, Checklist, Content, Visuals, Approval, Publication |
| Project Analytics | Operational truth of **one** project (OD-02) |
| Optimization | Post-MVP loop inside Project |

### Workspace

| Surface | Notes |
|---------|-------|
| Home | Entry / orientation |
| Projects | Index of commercial units |
| Knowledge library | Cross-project knowledge (if productized) |
| Portfolio Analytics | **Reserved** future aggregation — not public MVP |

### Settings / Admin

| Surface | Notes |
|---------|-------|
| General | Account/workspace preferences |
| Security / Integrations | Tokens, providers |
| Billing | Commercial admin — not a project stage |
| Team | Membership/roles — not a project stage |

### Reserved / support (not automatic Project stages)

| Capability | Classification until journey proof |
|------------|-------------------------------------|
| HR | Reserved (E) — default **not** project stage |
| Legal | Reserved / future project service (B) when journey exists |
| Finance | Reserved / future project service (B) when journey exists |
| Programmer | Reserved / future project service (B) when journey exists |
| CRM | **Reserved** (OD-09) — may later be project **or** workspace service |

Support capability may appear **inside** a Project only after a proven journey + owner approval.

---

## 3. Analytics dual-layer (OD-02 · OWNER-APPROVED)

| Layer | Role | MVP |
|-------|------|-----|
| **Project Analytics** | Canonical operational analytics for one project | MVP = **basic Outcome Capture only**; full Project Analytics = **post-MVP** |
| **Workspace Portfolio Analytics** | Future aggregation across projects | **Reserved** — not a public function |

**SUPERSEDED:** “Analytics-only-Project” exclusive lock from pack v1.

---

## 4. Launch subtree (OWNER-APPROVED)

```
Launch
├── Offer / Channels / Budget / Checklist
├── Content   ⎤ parallel
├── Visuals   ⎦
├── Approval packages
└── Publication (multi-instance)
```

---

## 5. Capability Registry vs topology

Registry controls **UX exposure** (available / reserved / hidden).  
Topology controls **where** a capability belongs when exposed.  
Neither is **authorization**.

---

## 6. Post-freeze follow-up (docs only; not this slice)

After `owner_freeze` = OWNER-FROZEN:

1. **IA patch** — align `INFORMATION_ARCHITECTURE.md` with dual-layer Analytics + Launch subtree + reserved support.  
2. **Journey references patch** — update Journey Map wording where it still implies linear conveyor or Analytics-only-Project.  
3. **Capability Registry patch** — classification/placement labels (A–F), Portfolio Analytics reserved, no premature public Analytics.

Do **not** change IA or Registry in PRODUCT-02-BLUEPRINT-PATCH-01.

---

## 7. Forbidden patterns

1. Separate top-level apps for Strategy / Launch / Analytics.  
2. Promoting HR/CRM/Legal/Finance/Programmer to mandatory Project stages.  
3. Public Workspace Portfolio Analytics before owner product decision.  
4. Treating Settings Billing/Team as commercial Project spine.
