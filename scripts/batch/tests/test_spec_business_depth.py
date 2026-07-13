"""Tests for spec_business_depth tier + gate."""

from __future__ import annotations

from batch.spec_business_depth import (
    resolve_business_depth_tier,
    tier_spec,
    verify_spec_business_depth,
)


def _sample_spec_l2() -> str:
    return """
# App Theme
Back-to-school supply budget tracker for guardians.

# Screen Inventory
| Screen | Purpose |
|--------|---------|
| Splash | Boot |
| Welcome | Gate |
| Home | Hub |
| List | Browse |
| Detail | Item |
| Export | Card |
| Settings | Config |
| Plaza | Hidden |

# Domain Model & Data Contract
| Entity | Fields | Type | Validation | Persistence |
|--------|--------|------|------------|-------------|
| SupplyItem | name | string | required | item_v1 |
| BudgetLedger | amount | number | >=0 | ledger_v1 |
| ReminderEntry | dueAt | date | future | remind_v1 |

# Business Rules Engine
- BR-01 Budget cap blocks save when exceeded
- BR-02 Ledger append on every purchase
- BR-03 Chip filter narrows list
- BR-04 Reminder lead time 3 days
- BR-05 Free export consumes free tier
- BR-06 Coin gate when free tier empty
- BR-07 Duplicate item merges by name

# Primary Workflow
1. Splash loads theme
2. Welcome checkbox agree
3. Home shows balance
4. Pick category chip
5. Add item with price
6. BR-01 validates budget
7. Bridge pickImage attach photo
8. Set due date BR-04
9. Save updates ledger BR-02
10. Filter list by tag
11. Export weekly summary card
12. IAP when coins insufficient

# Secondary Workflows
## Flow A — Edit archive
1. Open detail
2. Edit fields
3. Soft delete
4. Confirm snackbar
5. List refresh
6. Empty state copy

## Flow B — Review by date
1. Open history
2. Pick date range
3. Show totals
4. Tap row
5. Open detail
6. Return list

# State & Empty Matrix
| Screen | Loading | Empty | Error | Permission |
|--------|---------|-------|-------|------------|
| Home | Skeleton | No items yet | Retry | Camera denied |
| List | Spinner | No matches | Load failed | — |

# Professional Surface
## Domain Glossary
| Term | User copy |
|------|-----------|
| Planned spend | Planned budget |
| Spent | Spent so far |
| Due soon | Due within 7 days |
| Category chip | Supply category |
| Ledger | Purchase log |
| Reminder | Due alert |
| Export card | Weekly summary |
| Free export | Complimentary export |
| Guardians | Primary audience label |

## Metrics & Reports
- Weekly spend total: sum of ledger amounts in 7-day window
- signature H5 interaction: long-press item row in step 10 opens quick budget preview

# 4.2 Native Offset
- pickImage — step 7 attach reference photo
- purchase — step 12 coin top-up
- mediaServe — step 7 thumbnail display

# Bridge Capability Matrix
| Capability | Step | In | Out | Fail |
|------------|------|----|-----|------|
| pickImage | 7 | — | path | B01 |

# Export / Save Flow
- Weekly card from step 11

# IAP Catalog & Free Tier
- free_remaining_v1 for export

# H5 Architecture
- h5StateModel: functional-render

# Implementation Notes
The application maintains professional domain copy for guardians managing back-to-school supply lists,
budget envelopes, and reminder schedules. Every workflow step maps to a concrete persistence mutation
and a user-visible confirmation path. Empty states explain the next action in domain terms rather than
generic placeholders. Export metrics use ledger sums and due-date windows documented above.
""" + "\n".join(f"- Depth note {i}: guardian budget copy." for i in range(25))


def test_resolve_tier_l2_for_budget_scene() -> None:
    assert (
        resolve_business_depth_tier(
            core_scene="开学物品准备清单与采购预算控制",
            local_feature="到期提醒记录本",
        )
        == "L2"
    )


def test_resolve_tier_l3_for_analytics() -> None:
    assert (
        resolve_business_depth_tier(
            core_scene="sales trend dashboard",
            product_flow="compare weekly report",
        )
        == "L3"
    )


def test_verify_l2_sample_passes() -> None:
    issues = verify_spec_business_depth(_sample_spec_l2(), tier_id="L2")
    assert issues == []


def test_verify_missing_rules_fails() -> None:
    text = _sample_spec_l2().replace("BR-06 Coin gate when free tier empty\n", "")
    text = text.replace("BR-07 Duplicate item merges by name\n", "")
    issues = verify_spec_business_depth(text, tier_id="L2")
    assert any("SPEC-003" in i for i in issues)


def test_tier_l1_lower_bar() -> None:
    spec = tier_spec("L1")
    assert spec.min_primary_steps == 10
    assert spec.min_rules == 5
