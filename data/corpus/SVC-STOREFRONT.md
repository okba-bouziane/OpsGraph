# Service: storefront-web
*Sample data, fictional.*

Document ID: SVC-STOREFRONT
Type: Service
Kind: Web app
Owner: TEAM-DISCOVERY
Depends on: SVC-CATALOG (critical); SVC-SEARCH (degraded without it); SVC-CHECKOUT (critical for buying); SVC-REDIS (page cache)
Alerts: StorefrontDown, StorefrontSlowPages
Tier: 1

## What it does
The customer-facing website and the web view used by the mobile app. It renders product pages, the home page and the cart.

## Failure modes
If search is down, the storefront hides the search box and shows category pages only. If the catalog is down, product pages fail and the storefront shows a maintenance page. Product pages are cached in Redis for 60 seconds.

## Targets
Pages must render in under 800 ms at the 95th percentile. StorefrontDown fires when more than 5% of requests fail for 3 minutes.
