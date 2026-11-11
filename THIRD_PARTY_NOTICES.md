# Credits and source provenance

This is an independently maintained fork, not an official Ariston product.

* Home Assistant platforms, entity descriptions, configuration and shared-client
  lifecycle derive from [mauropriori/ariston_net](https://github.com/mauropriori/ariston_net),
  commit `837925d1f540b05bced1bc658dc85a277b0d8130` (version 0.1.2).
  Mauro Priori maintains that fork of Tamás Füstös / fustom's
  [original integration](https://github.com/fustom/ariston-remotethermo-home-assistant-v3).
  Its original MIT notice, Copyright (c) 2021 fustom, is preserved in LICENSE.
* `custom_components/fp_ariston_consumi/vendor/ariston_net_api` is an isolated copy
  of [mauropriori/python-ariston-api](https://github.com/mauropriori/python-ariston-api),
  commit `e2a294553c346c87e29c7eec434c271a97ed45c3`.
  Original author: Tamás Füstös / fustom; resilience and Lydos fixes by Mauro Priori.
  The complete original MIT notice, Copyright (c) 2022 fustom, is included alongside it.
  Imports remain relative, so an installed `ariston_net_api` cannot replace this copy.
* The historical Lydos report URL and four-period format were checked against
  [chomupashchuk/aquaariston-remotethermo-api](https://github.com/chomupashchuk/aquaariston-remotethermo-api),
  commit `207d70c458636514c0ee73e4b7c967140e48ada1`, `aristonaqua.py`.
  No implementation code from that project is distributed here.
* Original upstream regression tests retain their test cases and are supplemented
  by FP standalone, migration, cache and Home Assistant platform tests.

FP changes (2026, Fabio Piras) add a standalone domain, private client namespace,
stable identifiers, manual-only reports, local persistence, configuration upgrade,
and a staged migration/rollback guide. Ariston and product names belong to their
respective owners.
