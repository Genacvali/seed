#!/usr/bin/env bash
cat <<'TXT'
namespace                     op       time      details
------------------------------------------------------------
seed_demo.events              query      260ms  plan:COLLSCAN docs:200000 keys:0
seed_demo.events              query      210ms  plan:COLLSCAN docs:200000 keys:0
TXT
