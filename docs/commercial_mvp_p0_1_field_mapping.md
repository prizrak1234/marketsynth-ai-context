# Commercial MVP P0.1 — Field mapping

| ProductIntakeDraft | ProjectBrief | Notes |
|--------------------|--------------|-------|
| projectBasics.name | project_basics.project_name | |
| projectBasics.ideaDescription | project_basics.idea_description | |
| projectBasics.businessType/stage/geography | corresponding basics | |
| projectBasics.interfaceLanguage | language + preferred_language | |
| product.* | product.* | `whatIsSold`→`product_or_service`, etc. |
| product.price / priceUnknown | MoneyValue mode | unknown never → 0 |
| market.* | market.* | |
| audience.* | audience.* | customerModel→business_model; pains/objections |
| economics.* | economics.* | MoneyValue modes preserved |
| materials.items | materials_summary.items | **metadata only** |
| assumptions / missingData / readiness | same | |
| currentStep | **not persisted** | FE-only |
| backendSync | FE meta | excluded from fingerprint |
| file binaries | **unsupported** | |

CampaignBrief fields are **not** mapped.
