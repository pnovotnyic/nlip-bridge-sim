# Task review — stage 05, corrected in stage 07b
All 30 main intents per API with native requests, gold calls, and gold client answers.
Pilot intents are not included (they re-use a subset of main devices/sessions).

## L1
### L1-m01
**Intent:** Is the phone +9901000001 reachable right now?
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "phoneNumber": "+9901000001"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "phoneNumber": "+9901000001"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:59:50Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA", "SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m02
**Intent:** Check whether the device at IPv4 address 192.0.2.2 port 40002 can be reached.
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.2",
        "publicPort": 40002
      }
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.2",
        "publicPort": 40002
      }
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:59:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m03
**Intent:** Is the device with IPv6 address 2001:db8:a:3::1 reachable?
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:3::1"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:3::1"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_SMS" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_SMS", `lastStatusTime`: "2026-12-01T11:55:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m04
**Intent:** Check if phone +9901000004 is reachable.
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "phoneNumber": "9901000004"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "phoneNumber": "+9901000004"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed,unit_format | renamed,restructured | 4 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:30:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA", "SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'unit_format'], response=['renamed', 'restructured']

---
### L1-m05
**Intent:** Can the device at 192.0.2.5 port 40005 be reached?
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.5",
        "publicPort": 40005
      }
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.5",
        "publicPort": 40005
      }
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "NOT_CONNECTED" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "NOT_CONNECTED", `lastStatusTime`: "2026-12-01T10:00:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: false, `lastStatusTime`: "2026-12-01T10:00:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m06
**Intent:** Is the device at IPv6 address 2001:db8:a:6::1 currently reachable?
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:6::1"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:6::1"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:59:50Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA", "SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m07
**Intent:** Check the reachability status for phone +9901000007.
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "phoneNumber": "+9901000007"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "phoneNumber": "+9901000007"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:59:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m08
**Intent:** Is the device at address 192.0.2.8 port 40008 reachable?
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.8",
        "publicPort": 40008
      }
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.8",
        "publicPort": 40008
      }
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_SMS" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_SMS", `lastStatusTime`: "2026-12-01T11:55:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m09
**Intent:** Find out if the device with IPv6 address 2001:db8:a:9::1 can be reached.
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:9::1"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:9::1"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:30:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA", "SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m10
**Intent:** Check whether +9901000010 is reachable on the network.
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "phoneNumber": "9901000010"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "phoneNumber": "+9901000010"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "NOT_CONNECTED" | renamed,unit_format | renamed,restructured | 4 |
| `v0.6.0` | `done` | `reachabilityStatus`: "NOT_CONNECTED", `lastStatusTime`: "2026-12-01T10:00:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: false, `lastStatusTime`: "2026-12-01T10:00:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'unit_format'], response=['renamed', 'restructured']

---
### L1-m11
**Intent:** Is the device at 192.0.2.11 port 40011 currently reachable?
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.11",
        "publicPort": 40011
      }
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.11",
        "publicPort": 40011
      }
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:59:50Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA", "SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m12
**Intent:** Can the device with IPv6 address 2001:db8:a:c::1 be reached?
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:c::1"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:c::1"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:59:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m13
**Intent:** Check the reachability of phone number +9901000013.
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "phoneNumber": "+9901000013"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "phoneNumber": "+9901000013"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_SMS" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_SMS", `lastStatusTime`: "2026-12-01T11:55:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m14
**Intent:** Is the device at 192.0.2.14 port 40014 reachable on the network?
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.14",
        "publicPort": 40014
      }
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.14",
        "publicPort": 40014
      }
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:30:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA", "SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m15
**Intent:** Find out if the device with IPv6 2001:db8:a:f::1 is reachable.
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:f::1"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:f::1"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "NOT_CONNECTED" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "NOT_CONNECTED", `lastStatusTime`: "2026-12-01T10:00:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: false, `lastStatusTime`: "2026-12-01T10:00:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m16
**Intent:** Is phone +9901000016 currently reachable?
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "phoneNumber": "9901000016"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "phoneNumber": "+9901000016"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed,unit_format | renamed,restructured | 4 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:59:50Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA", "SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'unit_format'], response=['renamed', 'restructured']

---
### L1-m17
**Intent:** Check if the device at 192.0.2.17 port 40017 is reachable.
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.17",
        "publicPort": 40017
      }
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.17",
        "publicPort": 40017
      }
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:59:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m18
**Intent:** Is the device with IPv6 address 2001:db8:a:12::1 reachable?
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:12::1"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:12::1"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_SMS" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_SMS", `lastStatusTime`: "2026-12-01T11:55:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m19
**Intent:** Check reachability of phone +9901000019.
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "phoneNumber": "+9901000019"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "phoneNumber": "+9901000019"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:30:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA", "SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m20
**Intent:** Is the device at 192.0.2.20 port 40020 reachable right now?
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.20",
        "publicPort": 40020
      }
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.20",
        "publicPort": 40020
      }
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "NOT_CONNECTED" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "NOT_CONNECTED", `lastStatusTime`: "2026-12-01T10:00:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: false, `lastStatusTime`: "2026-12-01T10:00:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m21
**Intent:** Can the device with IPv6 address 2001:db8:a:15::1 be reached on the network?
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:15::1"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:15::1"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:59:50Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA", "SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m22
**Intent:** Is phone number +9901000022 reachable?
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "phoneNumber": "9901000022"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "phoneNumber": "+9901000022"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed,unit_format | renamed,restructured | 4 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:59:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA"] |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'unit_format'], response=['renamed', 'restructured']

---
### L1-m23
**Intent:** Check whether the device of subscriber dev023@nlipeval.example is reachable.
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "networkAccessIdentifier": "dev023@nlipeval.example"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "phoneNumber": "+9901000023"
    }
  }
}
```
(2 gold alternatives: {"phoneNumber": "+9901000023", "networkAccessIdentifier": "dev023@nlipeval.example"})
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_SMS" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_SMS", `lastStatusTime`: "2026-12-01T11:55:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["SMS"] |  |  | 0 |

**client_facts:** phone_number=+9901000023
**missing_info:** {'device.phoneNumber': 'fact'}
**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m24
**Intent:** Is the device at 192.0.2.24 port 40024 currently accessible on the network?
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.24",
        "publicPort": 40024
      }
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.24",
        "publicPort": 40024
      }
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:30:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA", "SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m25
**Intent:** Find out if the device with IPv6 2001:db8:a:19::1 is reachable.
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:19::1"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:19::1"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "NOT_CONNECTED" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "NOT_CONNECTED", `lastStatusTime`: "2026-12-01T10:00:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: false, `lastStatusTime`: "2026-12-01T10:00:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m26
**Intent:** Is phone +9901000026 reachable on the network right now?
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "phoneNumber": "9901000026"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "phoneNumber": "+9901000026"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed,unit_format | renamed,restructured | 4 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:59:50Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA", "SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'unit_format'], response=['renamed', 'restructured']

---
### L1-m27
**Intent:** Check the reachability of the device at 192.0.2.27 port 40027.
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.27",
        "publicPort": 40027
      }
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.27",
        "publicPort": 40027
      }
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:59:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m28
**Intent:** Is the device with IPv6 address 2001:db8:a:1c::1 reachable?
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:1c::1"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:1c::1"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_SMS" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_SMS", `lastStatusTime`: "2026-12-01T11:55:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m29
**Intent:** Can phone +9901000029 be reached?
**Operation:** retrieveReachability
**prompt_half:** True | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "phoneNumber": "+9901000029"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "phoneNumber": "+9901000029"
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "CONNECTED_DATA" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "CONNECTED_DATA", `lastStatusTime`: "2026-12-01T11:30:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: true, `connectivity`: ["DATA", "SMS"] |  |  | 0 |

**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
### L1-m30
**Intent:** Check if the device of subscriber dev030@nlipeval.example is reachable.
**Operation:** retrieveReachability
**prompt_half:** False | versions_behind (oldest): 2

**Native request at `v0.5.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/device-status/v0/connectivity",
  "body": {
    "device": {
      "networkAccessIdentifier": "dev030@nlipeval.example"
    }
  }
}
```
**Gold call at `v1.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/device-reachability-status/v1/retrieve",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:1e::1"
    }
  }
}
```
(2 gold alternatives: {"ipv6Address": "2001:db8:a:1e::1", "networkAccessIdentifier": "dev030@nlipeval.example"})
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.5.1` | `done` | `connectivityStatus`: "NOT_CONNECTED" | renamed | renamed,restructured | 3 |
| `v0.6.0` | `done` | `reachabilityStatus`: "NOT_CONNECTED", `lastStatusTime`: "2026-12-01T10:00:00Z" |  | restructured | 2 |
| `v1.0.0` | `done` | `reachable`: false, `lastStatusTime`: "2026-12-01T10:00:00Z" |  |  | 0 |

**client_facts:** ipv6_address=2001:db8:a:1e::1
**missing_info:** {'device.ipv6Address': 'fact'}
**change_tags (oldest):** request=['renamed'], response=['renamed', 'restructured']

---
## L2
### L2-m01
**Intent:** Check if phone +9901000001 is located within 2 km of 52.520, 13.411 in Berlin.
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "msisdn": "+9901000001"
    },
    "latitude": 52.52,
    "longitude": 13.411,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "phoneNumber": "+9901000001"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 52.52,
        "longitude": 13.411
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:30Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:30Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:30Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:30Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m02
**Intent:** Is the device at 192.0.2.2 port 40002 within 2 km of 50.083, 14.432 in Prague?
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv4Addr": "192.0.2.2"
    },
    "uePort": 40002,
    "latitude": 50.083,
    "longitude": 14.432,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.2",
        "publicPort": 40002
      }
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 50.083,
        "longitude": 14.432
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 8 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:58:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m03
**Intent:** Is the device with IPv6 address 2001:db8:a:3::1 within 2 km of 51.500, 10.000?
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv6Addr": "2001:db8:a:3::1"
    },
    "latitude": 51.5,
    "longitude": 10.0,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:3::1"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 51.5,
        "longitude": 10.0
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 422, expected refusal `LOCATION_VERIFICATION.UNABLE_TO_LOCATE`

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `unrepresentable` | null | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "UNKNOWN" |  | changed_meaning | 1 |
| `v1.0.0` | `done` | `verificationResult`: "UNKNOWN" |  | changed_meaning | 1 |
| `v2.0.0` | `done` | `verificationResult`: "UNKNOWN" |  | changed_meaning | 1 |
| `v3.0.0` | `declined` | null |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m04
**Intent:** Is phone +9901000004 within 3 km of 48.860, 2.352 in Paris?
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "msisdn": "9901000004"
    },
    "latitude": 48.86,
    "longitude": 2.352,
    "accuracy": 3.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "phoneNumber": "+9901000004"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 48.86,
        "longitude": 2.352
      },
      "radius": 3000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `unrepresentable` | null | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:00:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:00:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:00:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:00:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m05
**Intent:** Is the device at 192.0.2.5 port 40005 located within 2 km of 40.408, -3.716 in Madrid?
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv4Addr": "192.0.2.5"
    },
    "uePort": 40005,
    "latitude": 40.408,
    "longitude": -3.716,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.5",
        "publicPort": 40005
      }
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 40.408,
        "longitude": -3.716
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 8 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-11-30T12:00:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-11-30T12:00:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-11-30T12:00:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-11-30T12:00:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m06
**Intent:** Is the device with IPv6 2001:db8:a:6::1 within 2 km of 41.902, 12.502 in Rome?
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv6Addr": "2001:db8:a:6::1"
    },
    "latitude": 41.902,
    "longitude": 12.502,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:6::1"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 41.902,
        "longitude": 12.502
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:15Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m07
**Intent:** Check if phone +9901000007 is within 2 km of 52.376, 4.898 in Amsterdam.
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "msisdn": "+9901000007"
    },
    "latitude": 52.376,
    "longitude": 4.898,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "phoneNumber": "+9901000007"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 52.376,
        "longitude": 4.898
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:30Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:30Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:30Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:30Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m08
**Intent:** Is the device at 192.0.2.8 port 40008 within 2 km of 52.225, 21.024 in Warsaw?
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv4Addr": "192.0.2.8"
    },
    "uePort": 40008,
    "latitude": 52.225,
    "longitude": 21.024,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.8",
        "publicPort": 40008
      }
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 52.225,
        "longitude": 21.024
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `unrepresentable` | null | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 8 |
| `v0.2.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:58:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m09
**Intent:** Is the device with IPv6 2001:db8:a:9::1 within 2 km of 47.501, 19.040 in Budapest, using a location no older than 10 minutes?
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv6Addr": "2001:db8:a:9::1"
    },
    "latitude": 47.501,
    "longitude": 19.04,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:9::1"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 47.501,
        "longitude": 19.04
      },
      "radius": 2000
    },
    "maxAge": 600
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `unrepresentable` | null | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:50:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:50:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:50:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:50:00Z" |  |  | 0 |

**missing_info:** {'maxAge': 'intent_text'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m10
**Intent:** Check if phone +9901000010 is within 2 km of 47.368, 8.530 in Zurich.
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "msisdn": "9901000010"
    },
    "latitude": 47.368,
    "longitude": 8.53,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "phoneNumber": "+9901000010"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 47.368,
        "longitude": 8.53
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:00:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:00:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:00:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:00:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m11
**Intent:** Is the device at 192.0.2.11 port 40011 within 2 km of 52.400, 13.000?
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv4Addr": "192.0.2.11"
    },
    "uePort": 40011,
    "latitude": 52.4,
    "longitude": 13.0,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.11",
        "publicPort": 40011
      }
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 52.4,
        "longitude": 13.0
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 422, expected refusal `LOCATION_VERIFICATION.UNABLE_TO_LOCATE`

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `unrepresentable` | null | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 8 |
| `v0.2.0` | `done` | `verificationResult`: "UNKNOWN" |  | changed_meaning | 1 |
| `v1.0.0` | `done` | `verificationResult`: "UNKNOWN" |  | changed_meaning | 1 |
| `v2.0.0` | `done` | `verificationResult`: "UNKNOWN" |  | changed_meaning | 1 |
| `v3.0.0` | `declined` | null |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m12
**Intent:** Is the device with IPv6 2001:db8:a:c::1 within 2 km of 53.357, -6.266 in Dublin?
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv6Addr": "2001:db8:a:c::1"
    },
    "latitude": 53.357,
    "longitude": -6.266,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:c::1"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 53.357,
        "longitude": -6.266
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:15Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m13
**Intent:** Check if phone +9901000013 is within 2 km of 50.731, 7.112 in Bonn.
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "msisdn": "+9901000013"
    },
    "latitude": 50.731,
    "longitude": 7.112,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "phoneNumber": "+9901000013"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 50.731,
        "longitude": 7.112
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `unrepresentable` | null | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:59:30Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:59:30Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:59:30Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:59:30Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m14
**Intent:** Is the device at 192.0.2.14 port 40014 within 2 km of 52.524, 13.405 in Berlin?
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv4Addr": "192.0.2.14"
    },
    "uePort": 40014,
    "latitude": 52.524,
    "longitude": 13.405,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.14",
        "publicPort": 40014
      }
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 52.524,
        "longitude": 13.405
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `unrepresentable` | null | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 8 |
| `v0.2.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:58:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m15
**Intent:** Is the device with IPv6 2001:db8:a:f::1 within 2 km of 50.067, 14.425 in Prague?
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv6Addr": "2001:db8:a:f::1"
    },
    "latitude": 50.067,
    "longitude": 14.425,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:f::1"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 50.067,
        "longitude": 14.425
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:50:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:50:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:50:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:50:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m16
**Intent:** Check if phone +9901000016 is within 2 km of 48.208, 16.379 in Vienna, using a fresh location reading.
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "msisdn": "9901000016"
    },
    "latitude": 48.208,
    "longitude": 16.379,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "phoneNumber": "+9901000016"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 48.208,
        "longitude": 16.379
      },
      "radius": 2000
    },
    "maxAge": 0
  }
}
```
**Gold backend response:** HTTP 422, expected refusal `LOCATION_VERIFICATION.UNABLE_TO_FULFILL_MAX_AGE`

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `declined` | null | renamed,restructured,unit_format,newly_required |  | 6 |
| `v0.2.0` | `declined` | null |  |  | 0 |
| `v1.0.0` | `declined` | null |  |  | 0 |
| `v2.0.0` | `declined` | null |  |  | 0 |
| `v3.0.0` | `declined` | null |  |  | 0 |

**missing_info:** {'maxAge': 'intent_text'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=[]

---
### L2-m17
**Intent:** Is the device at 192.0.2.17 port 40017 within 2 km of 48.864, 2.346 in Paris?
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv4Addr": "192.0.2.17"
    },
    "uePort": 40017,
    "latitude": 48.864,
    "longitude": 2.346,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.17",
        "publicPort": 40017
      }
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 48.864,
        "longitude": 2.346
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 8 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-11-30T12:00:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-11-30T12:00:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-11-30T12:00:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-11-30T12:00:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m18
**Intent:** Is the device with IPv6 2001:db8:a:12::1 within 2 km of 40.412, -3.691 in Madrid?
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv6Addr": "2001:db8:a:12::1"
    },
    "latitude": 40.412,
    "longitude": -3.691,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:12::1"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 40.412,
        "longitude": -3.691
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `unrepresentable` | null | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:59:15Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m19
**Intent:** Is phone +9901000019 within 2 km of 51.000, 10.000?
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "msisdn": "+9901000019"
    },
    "latitude": 51.0,
    "longitude": 10.0,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "phoneNumber": "+9901000019"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 51.0,
        "longitude": 10.0
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 422, expected refusal `LOCATION_VERIFICATION.UNABLE_TO_LOCATE`

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `unrepresentable` | null | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "UNKNOWN" |  | changed_meaning | 1 |
| `v1.0.0` | `done` | `verificationResult`: "UNKNOWN" |  | changed_meaning | 1 |
| `v2.0.0` | `done` | `verificationResult`: "UNKNOWN" |  | changed_meaning | 1 |
| `v3.0.0` | `declined` | null |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m20
**Intent:** Is the device at 192.0.2.20 port 40020 within 2 km of 52.359, 4.892 in Amsterdam?
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv4Addr": "192.0.2.20"
    },
    "uePort": 40020,
    "latitude": 52.359,
    "longitude": 4.892,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.20",
        "publicPort": 40020
      }
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 52.359,
        "longitude": 4.892
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 8 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:58:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m21
**Intent:** Check if the device with IPv6 2001:db8:a:15::1 is within 2 km of 52.229, 21.018 in Warsaw.
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv6Addr": "2001:db8:a:15::1"
    },
    "latitude": 52.229,
    "longitude": 21.018,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:15::1"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 52.229,
        "longitude": 21.018
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:50:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:50:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:50:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:50:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m22
**Intent:** Is phone +9901000022 within 2 km of 47.505, 19.034 in Budapest?
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "msisdn": "9901000022"
    },
    "latitude": 47.505,
    "longitude": 19.034,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "phoneNumber": "+9901000022"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 47.505,
        "longitude": 19.034
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:00:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:00:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:00:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:00:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m23
**Intent:** Is the device of subscriber dev023@nlipeval.example within 2 km of 47.372, 8.553 in Zurich?
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "externalId": "dev023@nlipeval.example"
    },
    "latitude": 47.372,
    "longitude": 8.553,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "phoneNumber": "+9901000023"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 47.372,
        "longitude": 8.553
      },
      "radius": 2000
    }
  }
}
```
(2 gold alternatives: {"phoneNumber": "+9901000023", "networkAccessIdentifier": "dev023@nlipeval.example"})
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `unrepresentable` | null | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 8 |
| `v0.2.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-11-30T12:00:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-11-30T12:00:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-11-30T12:00:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-11-30T12:00:00Z" |  |  | 0 |

**client_facts:** phone_number=+9901000023
**missing_info:** {'device.phoneNumber': 'fact'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m24
**Intent:** Is the device at 192.0.2.24 port 40024 within 3 km of 38.726, -9.139 in Lisbon?
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv4Addr": "192.0.2.24"
    },
    "uePort": 40024,
    "latitude": 38.726,
    "longitude": -9.139,
    "accuracy": 3.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.24",
        "publicPort": 40024
      }
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 38.726,
        "longitude": -9.139
      },
      "radius": 3000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `unrepresentable` | null | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 8 |
| `v0.2.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:59:15Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m25
**Intent:** Is the device with IPv6 2001:db8:a:19::1 within 2 km of 53.341, -6.272 in Dublin?
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv6Addr": "2001:db8:a:19::1"
    },
    "latitude": 53.341,
    "longitude": -6.272,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:19::1"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 53.341,
        "longitude": -6.272
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:30Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:30Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:30Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:30Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m26
**Intent:** Check if phone +9901000026 is within 2 km of 50.735, 7.106 in Bonn, using a location that is at most 5 minutes old.
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "msisdn": "9901000026"
    },
    "latitude": 50.735,
    "longitude": 7.106,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "phoneNumber": "+9901000026"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 50.735,
        "longitude": 7.106
      },
      "radius": 2000
    },
    "maxAge": 300
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:58:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:58:00Z" |  |  | 0 |

**missing_info:** {'maxAge': 'intent_text'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m27
**Intent:** Is the device at 192.0.2.27 port 40027 within 2 km of 51.500, 10.000, with a location no older than 1 hour?
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv4Addr": "192.0.2.27"
    },
    "uePort": 40027,
    "latitude": 51.5,
    "longitude": 10.0,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.27",
        "publicPort": 40027
      }
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 51.5,
        "longitude": 10.0
      },
      "radius": 2000
    },
    "maxAge": 3600
  }
}
```
**Gold backend response:** HTTP 422, expected refusal `LOCATION_VERIFICATION.UNABLE_TO_FULFILL_MAX_AGE`

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `declined` | null | renamed,restructured,unit_format,newly_required |  | 7 |
| `v0.2.0` | `declined` | null |  |  | 0 |
| `v1.0.0` | `declined` | null |  |  | 0 |
| `v2.0.0` | `declined` | null |  |  | 0 |
| `v3.0.0` | `declined` | null |  |  | 0 |

**missing_info:** {'maxAge': 'intent_text'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=[]

---
### L2-m28
**Intent:** Is the device with IPv6 2001:db8:a:1c::1 within 2 km of 50.071, 14.449 in Prague?
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv6Addr": "2001:db8:a:1c::1"
    },
    "latitude": 50.071,
    "longitude": 14.449,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv6Address": "2001:db8:a:1c::1"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 50.071,
        "longitude": 14.449
      },
      "radius": 2000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `unrepresentable` | null | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:00:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:00:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:00:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-12-01T11:00:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m29
**Intent:** Check if phone +9901000029 is within 3 km of 48.212, 16.373 in Vienna.
**Operation:** verifyLocation
**prompt_half:** True | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "msisdn": "+9901000029"
    },
    "latitude": 48.212,
    "longitude": 16.373,
    "accuracy": 3.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "phoneNumber": "+9901000029"
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 48.212,
        "longitude": 16.373
      },
      "radius": 3000
    }
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `unrepresentable` | null | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 7 |
| `v0.2.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-11-30T12:00:00Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-11-30T12:00:00Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-11-30T12:00:00Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "PARTIAL", `lastLocationTime`: "2026-11-30T12:00:00Z" |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
### L2-m30
**Intent:** Is the device at 192.0.2.30 port 40030 within 2 km of 48.848, 2.340 in Paris, using a fresh reading?
**Operation:** verifyLocation
**prompt_half:** False | versions_behind (oldest): 4

**Native request at `v0.1.0` (oldest):**
```json
{
  "method": "POST",
  "path": "/location/v0/verify",
  "body": {
    "ueId": {
      "ipv4Addr": "192.0.2.30"
    },
    "uePort": 40030,
    "latitude": 48.848,
    "longitude": 2.34,
    "accuracy": 2.0
  }
}
```
**Gold call at `v3.0.0` (server):**
```json
{
  "method": "POST",
  "path": "/location-verification/v3/verify",
  "body": {
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.30",
        "publicPort": 40030
      }
    },
    "area": {
      "areaType": "CIRCLE",
      "center": {
        "latitude": 48.848,
        "longitude": 2.34
      },
      "radius": 2000
    },
    "maxAge": 3600
  }
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.1.0` | `done` | `verificationResult`: true | renamed,restructured,unit_format,newly_required | unit_format,changed_meaning | 8 |
| `v0.2.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v1.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v2.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:15Z" |  | newly_required | 1 |
| `v3.0.0` | `done` | `verificationResult`: "TRUE", `lastLocationTime`: "2026-12-01T11:59:15Z" |  |  | 0 |

**client_facts:** max_age_acceptable=If a fresh reading is not possible, a reading up to one hour old is acceptable.
**missing_info:** {'maxAge': 'fact'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['unit_format', 'changed_meaning']

---
## L3
### L3-m01
**Intent:** Give the phone +9901000001 a stable low-latency connection to the game server at 198.51.100.20 for the next hour.
**Operation:** createSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 3600,
    "ueId": {
      "msisdn": "+9901000001"
    },
    "asId": {
      "ipv4addr": "198.51.100.20"
    },
    "qos": "QOS_E"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 3600,
    "device": {
      "phoneNumber": "+9901000001"
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.20"
    },
    "qosProfile": "QOS_M"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 3600, `asId`: {"ipv4addr": "198.51.100.20"} | renamed,restructured,unit_format,newly_required | renamed,unit_format,newly_required | 13 |
| `v0.9.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv4Address": "198.51.100.20"} | newly_required | unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv4Address": "198.51.100.20"} | newly_required | unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv4Address": "198.51.100.20"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv4Address": "198.51.100.20"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv4Address": "198.51.100.20"} |  |  | 0 |

**client_facts:** duration_preference=If QOS_E cannot be given for the full hour, use QOS_M for the full time rather than a shorter session.
**missing_info:** {'qosProfile': 'fact'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m02
**Intent:** Create a QoS session for the device at 192.0.2.2 port 40002 to the game server at 198.51.100.20 for 30 minutes using the low-latency profile.
**Operation:** createSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 1800,
    "ueId": {
      "ipv4addr": "192.0.2.2"
    },
    "asId": {
      "ipv4addr": "198.51.100.20"
    },
    "qos": "QOS_E"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 1800,
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.2",
        "publicPort": 40002
      }
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.20"
    },
    "qosProfile": "QOS_E"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 1800, `asId`: {"ipv4addr": "198.51.100.20"} | renamed,restructured,unit_format,newly_required | renamed,unit_format,newly_required | 14 |
| `v0.9.0` | `done` | `duration`: 1800, `applicationServer`: {"ipv4Address": "198.51.100.20"} | newly_required | unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 1800, `applicationServer`: {"ipv4Address": "198.51.100.20"} | newly_required | unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 1800, `applicationServer`: {"ipv4Address": "198.51.100.20"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 1800, `applicationServer`: {"ipv4Address": "198.51.100.20"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 1800, `applicationServer`: {"ipv4Address": "198.51.100.20"} |  |  | 0 |

**missing_info:** {'device.ipv4Address.publicPort': 'intent_text'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m03
**Intent:** Set up a video call connection from the device with IPv6 2001:db8:a:3::1 to the conference server at 2001:db8:b::10 for 45 minutes.
**Operation:** createSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 2700,
    "ueId": {
      "ipv6addr": "2001:db8:a:3::1"
    },
    "asId": {
      "ipv6addr": "2001:db8:b::10"
    },
    "qos": "QOS_M"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 2700,
    "device": {
      "ipv6Address": "2001:db8:a:3::1"
    },
    "applicationServer": {
      "ipv6Address": "2001:db8:b::10"
    },
    "qosProfile": "QOS_M"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 2700, `asId`: {"ipv6addr": "2001:db8:b::10"} | renamed,restructured,unit_format,newly_required | renamed,unit_format,newly_required | 13 |
| `v0.9.0` | `done` | `duration`: 2700, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} | newly_required | unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 2700, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} | newly_required | unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 2700, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 2700, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 2700, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m04
**Intent:** Give phone +9901000004 a balanced connection to the streaming server at 198.51.100.30/32 for 1 hour, using device port 8080.
**Operation:** createSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 3600,
    "ueId": {
      "msisdn": "9901000004"
    },
    "asId": {
      "ipv4addr": "198.51.100.30/32"
    },
    "uePorts": {
      "ports": [
        8080
      ]
    },
    "qos": "QOS_M"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 3600,
    "device": {
      "phoneNumber": "+9901000004"
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.30/32"
    },
    "devicePorts": {
      "ports": [
        8080
      ]
    },
    "qosProfile": "QOS_M"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 3600, `asId`: {"ipv4addr": "198.51.100.30/32"} | renamed,restructured,unit_format,newly_required | renamed,unit_format,newly_required | 15 |
| `v0.9.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} | newly_required | unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} | newly_required | unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m05
**Intent:** Create a large-file transfer session for the device at 192.0.2.5 port 40005 to the content server at 198.51.100.40, server port 443, for 4 hours.
**Operation:** createSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 14400,
    "ueId": {
      "ipv4addr": "192.0.2.5"
    },
    "asId": {
      "ipv4addr": "198.51.100.40"
    },
    "asPorts": {
      "ports": [
        443
      ]
    },
    "qos": "QOS_L"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 14400,
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.5",
        "publicPort": 40005
      }
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.40"
    },
    "applicationServerPorts": {
      "ports": [
        443
      ]
    },
    "qosProfile": "QOS_L"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 14400, `asId`: {"ipv4addr": "198.51.100.40"} | renamed,restructured,unit_format,newly_required | renamed,unit_format,newly_required | 16 |
| `v0.9.0` | `done` | `duration`: 14400, `applicationServer`: {"ipv4Address": "198.51.100.40"} | newly_required | unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 14400, `applicationServer`: {"ipv4Address": "198.51.100.40"} | newly_required | unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 14400, `applicationServer`: {"ipv4Address": "198.51.100.40"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 14400, `applicationServer`: {"ipv4Address": "198.51.100.40"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 14400, `applicationServer`: {"ipv4Address": "198.51.100.40"} |  |  | 0 |

**missing_info:** {'device.ipv4Address.publicPort': 'intent_text'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m06
**Intent:** Set up a messaging session for the device with IPv6 2001:db8:a:6::1 to the message broker at 198.51.100.50 for the next 24 hours.
**Operation:** createSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 86400,
    "ueId": {
      "ipv6addr": "2001:db8:a:6::1"
    },
    "asId": {
      "ipv4addr": "198.51.100.50"
    },
    "qos": "QOS_S"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 86400,
    "device": {
      "ipv6Address": "2001:db8:a:6::1"
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.50"
    },
    "qosProfile": "QOS_S"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 86400, `asId`: {"ipv4addr": "198.51.100.50"} | renamed,restructured,unit_format,newly_required | renamed,unit_format,newly_required | 13 |
| `v0.9.0` | `done` | `duration`: 86400, `applicationServer`: {"ipv4Address": "198.51.100.50"} | newly_required | unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 86400, `applicationServer`: {"ipv4Address": "198.51.100.50"} | newly_required | unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 86400, `applicationServer`: {"ipv4Address": "198.51.100.50"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 86400, `applicationServer`: {"ipv4Address": "198.51.100.50"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 86400, `applicationServer`: {"ipv4Address": "198.51.100.50"} |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m07
**Intent:** Give phone +9901000007 a low-latency session to the game server at 198.51.100.20 for 20 minutes, with notifications to https://app.example.org/notify/session.
**Operation:** createSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 1200,
    "ueId": {
      "msisdn": "+9901000007"
    },
    "asId": {
      "ipv4addr": "198.51.100.20"
    },
    "qos": "QOS_E",
    "notificationUrl": "https://app.example.org/notify/session"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 1200,
    "device": {
      "phoneNumber": "+9901000007"
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.20"
    },
    "qosProfile": "QOS_E",
    "sink": "https://app.example.org/notify/session"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 1200, `asId`: {"ipv4addr": "198.51.100.20"} | renamed,restructured,unit_format,newly_required,changed_meaning | renamed,unit_format,newly_required | 14 |
| `v0.9.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.20"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.10.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.20"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.11.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.20"} | unit_format | unit_format | 2 |
| `v1.0.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.20"} | unit_format | unit_format | 2 |
| `v1.1.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.20"} |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required', 'changed_meaning'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m08
**Intent:** Create a video streaming session for the device at 192.0.2.8 port 40008 to the media server at 198.51.100.60, server ports 5000–5100, for 1.5 hours.
**Operation:** createSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 5400,
    "ueId": {
      "ipv4addr": "192.0.2.8"
    },
    "asId": {
      "ipv4addr": "198.51.100.60"
    },
    "asPorts": {
      "ranges": [
        {
          "from": 5000,
          "to": 5100
        }
      ]
    },
    "qos": "QOS_M"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 5400,
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.8",
        "publicPort": 40008
      }
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.60"
    },
    "applicationServerPorts": {
      "ranges": [
        {
          "from": 5000,
          "to": 5100
        }
      ]
    },
    "qosProfile": "QOS_M"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 5400, `asId`: {"ipv4addr": "198.51.100.60"} | renamed,restructured,unit_format,newly_required | renamed,unit_format,newly_required | 18 |
| `v0.9.0` | `done` | `duration`: 5400, `applicationServer`: {"ipv4Address": "198.51.100.60"} | newly_required | unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 5400, `applicationServer`: {"ipv4Address": "198.51.100.60"} | newly_required | unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 5400, `applicationServer`: {"ipv4Address": "198.51.100.60"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 5400, `applicationServer`: {"ipv4Address": "198.51.100.60"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 5400, `applicationServer`: {"ipv4Address": "198.51.100.60"} |  |  | 0 |

**missing_info:** {'device.ipv4Address.publicPort': 'intent_text'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m09
**Intent:** Set up a low-latency connection for the device with IPv6 2001:db8:a:9::1 to the application server at 2001:db8:b::/64 for 25 minutes.
**Operation:** createSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 1500,
    "ueId": {
      "ipv6addr": "2001:db8:a:9::1"
    },
    "asId": {
      "ipv6addr": "2001:db8:b::/64"
    },
    "qos": "QOS_E"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 1500,
    "device": {
      "ipv6Address": "2001:db8:a:9::1"
    },
    "applicationServer": {
      "ipv6Address": "2001:db8:b::/64"
    },
    "qosProfile": "QOS_E"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 1500, `asId`: {"ipv6addr": "2001:db8:b::/64"} | renamed,restructured,unit_format,newly_required | renamed,unit_format,newly_required | 13 |
| `v0.9.0` | `done` | `duration`: 1500, `applicationServer`: {"ipv6Address": "2001:db8:b::/64"} | newly_required | unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 1500, `applicationServer`: {"ipv6Address": "2001:db8:b::/64"} | newly_required | unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 1500, `applicationServer`: {"ipv6Address": "2001:db8:b::/64"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 1500, `applicationServer`: {"ipv6Address": "2001:db8:b::/64"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 1500, `applicationServer`: {"ipv6Address": "2001:db8:b::/64"} |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m10
**Intent:** Give phone +9901000010 a large-data transfer connection to the backup server at 198.51.100.70 for 2 hours, with status notifications to https://app.example.org/notify/data.
**Operation:** createSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 7200,
    "ueId": {
      "msisdn": "9901000010"
    },
    "asId": {
      "ipv4addr": "198.51.100.70"
    },
    "qos": "QOS_L",
    "notificationUrl": "https://app.example.org/notify/data"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 7200,
    "device": {
      "phoneNumber": "+9901000010"
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.70"
    },
    "qosProfile": "QOS_L",
    "sink": "https://app.example.org/notify/data"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 7200, `asId`: {"ipv4addr": "198.51.100.70"} | renamed,restructured,unit_format,newly_required,changed_meaning | renamed,unit_format,newly_required | 14 |
| `v0.9.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.70"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.10.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.70"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.11.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.70"} | unit_format | unit_format | 2 |
| `v1.0.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.70"} | unit_format | unit_format | 2 |
| `v1.1.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.70"} |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required', 'changed_meaning'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m11
**Intent:** Create a 2-hour low-latency session for the device at 192.0.2.11 port 40011 to the game server at 198.51.100.20.
**Operation:** createSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 7200,
    "ueId": {
      "ipv4addr": "192.0.2.11"
    },
    "asId": {
      "ipv4addr": "198.51.100.20"
    },
    "qos": "QOS_E"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 7200,
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.11",
        "publicPort": 40011
      }
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.20"
    },
    "qosProfile": "QOS_M"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 7200, `asId`: {"ipv4addr": "198.51.100.20"} | renamed,restructured,unit_format,newly_required | renamed,unit_format,newly_required | 14 |
| `v0.9.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.20"} | newly_required | unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.20"} | newly_required | unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.20"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.20"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.20"} |  |  | 0 |

**client_facts:** duration_preference=If QOS_E cannot be given for the full two hours, use QOS_M for the full time rather than a shorter session.
**missing_info:** {'device.ipv4Address.publicPort': 'intent_text', 'qosProfile': 'fact'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m12
**Intent:** Set up a telemetry session for the device with IPv6 2001:db8:a:c::1 to the telemetry server at 198.51.100.0/24 for 12 hours, with event notifications to https://app.example.org/notify/telemetry.
**Operation:** createSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 43200,
    "ueId": {
      "ipv6addr": "2001:db8:a:c::1"
    },
    "asId": {
      "ipv4addr": "198.51.100.0/24"
    },
    "qos": "QOS_S",
    "notificationUrl": "https://app.example.org/notify/telemetry"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 43200,
    "device": {
      "ipv6Address": "2001:db8:a:c::1"
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.0/24"
    },
    "qosProfile": "QOS_S",
    "sink": "https://app.example.org/notify/telemetry"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 43200, `asId`: {"ipv4addr": "198.51.100.0/24"} | renamed,restructured,unit_format,newly_required,changed_meaning | renamed,unit_format,newly_required | 14 |
| `v0.9.0` | `done` | `duration`: 43200, `applicationServer`: {"ipv4Address": "198.51.100.0/24"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.10.0` | `done` | `duration`: 43200, `applicationServer`: {"ipv4Address": "198.51.100.0/24"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.11.0` | `done` | `duration`: 43200, `applicationServer`: {"ipv4Address": "198.51.100.0/24"} | unit_format | unit_format | 2 |
| `v1.0.0` | `done` | `duration`: 43200, `applicationServer`: {"ipv4Address": "198.51.100.0/24"} | unit_format | unit_format | 2 |
| `v1.1.0` | `done` | `duration`: 43200, `applicationServer`: {"ipv4Address": "198.51.100.0/24"} |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required', 'changed_meaning'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m13
**Intent:** Give phone +9901000013 a video call connection to the conference server at 2001:db8:b::10 for 1 hour, with device ports 5060 and 5061.
**Operation:** createSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 3600,
    "ueId": {
      "msisdn": "+9901000013"
    },
    "asId": {
      "ipv6addr": "2001:db8:b::10"
    },
    "uePorts": {
      "ports": [
        5060,
        5061
      ]
    },
    "qos": "QOS_M"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 3600,
    "device": {
      "phoneNumber": "+9901000013"
    },
    "applicationServer": {
      "ipv6Address": "2001:db8:b::10"
    },
    "devicePorts": {
      "ports": [
        5060,
        5061
      ]
    },
    "qosProfile": "QOS_M"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 3600, `asId`: {"ipv6addr": "2001:db8:b::10"} | renamed,restructured,unit_format,newly_required | renamed,unit_format,newly_required | 15 |
| `v0.9.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} | newly_required | unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} | newly_required | unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m14
**Intent:** Create a high-throughput file transfer session for the device at 192.0.2.14 port 40014 to the CDN at 198.51.100.40, server port 443, for 3 hours.
**Operation:** createSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 10800,
    "ueId": {
      "ipv4addr": "192.0.2.14"
    },
    "asId": {
      "ipv4addr": "198.51.100.40"
    },
    "asPorts": {
      "ports": [
        443
      ]
    },
    "qos": "QOS_L"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 10800,
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.14",
        "publicPort": 40014
      }
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.40"
    },
    "applicationServerPorts": {
      "ports": [
        443
      ]
    },
    "qosProfile": "QOS_L"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 10800, `asId`: {"ipv4addr": "198.51.100.40"} | renamed,restructured,unit_format,newly_required | renamed,unit_format,newly_required | 16 |
| `v0.9.0` | `done` | `duration`: 10800, `applicationServer`: {"ipv4Address": "198.51.100.40"} | newly_required | unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 10800, `applicationServer`: {"ipv4Address": "198.51.100.40"} | newly_required | unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 10800, `applicationServer`: {"ipv4Address": "198.51.100.40"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 10800, `applicationServer`: {"ipv4Address": "198.51.100.40"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 10800, `applicationServer`: {"ipv4Address": "198.51.100.40"} |  |  | 0 |

**missing_info:** {'device.ipv4Address.publicPort': 'intent_text'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m15
**Intent:** Set up a 6-hour IoT telemetry session for the device with IPv6 2001:db8:a:f::1 to the platform at 198.51.100.50, with status updates to https://app.example.org/notify/iot.
**Operation:** createSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 21600,
    "ueId": {
      "ipv6addr": "2001:db8:a:f::1"
    },
    "asId": {
      "ipv4addr": "198.51.100.50"
    },
    "qos": "QOS_S",
    "notificationUrl": "https://app.example.org/notify/iot"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 21600,
    "device": {
      "ipv6Address": "2001:db8:a:f::1"
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.50"
    },
    "qosProfile": "QOS_S",
    "sink": "https://app.example.org/notify/iot"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 21600, `asId`: {"ipv4addr": "198.51.100.50"} | renamed,restructured,unit_format,newly_required,changed_meaning | renamed,unit_format,newly_required | 14 |
| `v0.9.0` | `done` | `duration`: 21600, `applicationServer`: {"ipv4Address": "198.51.100.50"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.10.0` | `done` | `duration`: 21600, `applicationServer`: {"ipv4Address": "198.51.100.50"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.11.0` | `done` | `duration`: 21600, `applicationServer`: {"ipv4Address": "198.51.100.50"} | unit_format | unit_format | 2 |
| `v1.0.0` | `done` | `duration`: 21600, `applicationServer`: {"ipv4Address": "198.51.100.50"} | unit_format | unit_format | 2 |
| `v1.1.0` | `done` | `duration`: 21600, `applicationServer`: {"ipv4Address": "198.51.100.50"} |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required', 'changed_meaning'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m16
**Intent:** Create a low-latency gaming session for the subscriber dev016@nlipeval.example to the game server at 198.51.100.20 for 15 minutes.
**Operation:** createSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 900,
    "ueId": {
      "externalId": "dev016@nlipeval.example"
    },
    "asId": {
      "ipv4addr": "198.51.100.20"
    },
    "qos": "QOS_E"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 900,
    "device": {
      "phoneNumber": "+9901000016"
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.20"
    },
    "qosProfile": "QOS_E"
  }
}
```
(2 gold alternatives: {"phoneNumber": "+9901000016", "networkAccessIdentifier": "dev016@nlipeval.example"})
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 900, `asId`: {"ipv4addr": "198.51.100.20"} | renamed,restructured,unit_format,newly_required | renamed,unit_format,newly_required | 14 |
| `v0.9.0` | `done` | `duration`: 900, `applicationServer`: {"ipv4Address": "198.51.100.20"} | newly_required | unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 900, `applicationServer`: {"ipv4Address": "198.51.100.20"} | newly_required | unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 900, `applicationServer`: {"ipv4Address": "198.51.100.20"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 900, `applicationServer`: {"ipv4Address": "198.51.100.20"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 900, `applicationServer`: {"ipv4Address": "198.51.100.20"} |  |  | 0 |

**client_facts:** phone_number=+9901000016
**missing_info:** {'device.phoneNumber': 'fact'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m17
**Intent:** Give phone +9901000017 a streaming session to the media server at 198.51.100.60 for 90 minutes, with application server ports 5000–5100 and notifications to https://app.example.org/notify/stream.
**Operation:** createSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 5400,
    "ueId": {
      "msisdn": "+9901000017"
    },
    "asId": {
      "ipv4addr": "198.51.100.60"
    },
    "asPorts": {
      "ranges": [
        {
          "from": 5000,
          "to": 5100
        }
      ]
    },
    "qos": "QOS_M",
    "notificationUrl": "https://app.example.org/notify/stream"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 5400,
    "device": {
      "phoneNumber": "+9901000017"
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.60"
    },
    "applicationServerPorts": {
      "ranges": [
        {
          "from": 5000,
          "to": 5100
        }
      ]
    },
    "qosProfile": "QOS_M",
    "sink": "https://app.example.org/notify/stream"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 5400, `asId`: {"ipv4addr": "198.51.100.60"} | renamed,restructured,unit_format,newly_required,changed_meaning | renamed,unit_format,newly_required | 18 |
| `v0.9.0` | `done` | `duration`: 5400, `applicationServer`: {"ipv4Address": "198.51.100.60"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.10.0` | `done` | `duration`: 5400, `applicationServer`: {"ipv4Address": "198.51.100.60"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.11.0` | `done` | `duration`: 5400, `applicationServer`: {"ipv4Address": "198.51.100.60"} | unit_format | unit_format | 2 |
| `v1.0.0` | `done` | `duration`: 5400, `applicationServer`: {"ipv4Address": "198.51.100.60"} | unit_format | unit_format | 2 |
| `v1.1.0` | `done` | `duration`: 5400, `applicationServer`: {"ipv4Address": "198.51.100.60"} |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required', 'changed_meaning'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m18
**Intent:** Create a large-data transfer session for the device at 192.0.2.18 port 40018 to the archive server at 198.51.100.70 for 4 hours, with notifications to https://app.example.org/notify/archive.
**Operation:** createSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 14400,
    "ueId": {
      "ipv4addr": "192.0.2.18"
    },
    "asId": {
      "ipv4addr": "198.51.100.70"
    },
    "qos": "QOS_L",
    "notificationUrl": "https://app.example.org/notify/archive"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 14400,
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.18",
        "publicPort": 40018
      }
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.70"
    },
    "qosProfile": "QOS_L",
    "sink": "https://app.example.org/notify/archive"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 14400, `asId`: {"ipv4addr": "198.51.100.70"} | renamed,restructured,unit_format,newly_required,changed_meaning | renamed,unit_format,newly_required | 15 |
| `v0.9.0` | `done` | `duration`: 14400, `applicationServer`: {"ipv4Address": "198.51.100.70"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.10.0` | `done` | `duration`: 14400, `applicationServer`: {"ipv4Address": "198.51.100.70"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.11.0` | `done` | `duration`: 14400, `applicationServer`: {"ipv4Address": "198.51.100.70"} | unit_format | unit_format | 2 |
| `v1.0.0` | `done` | `duration`: 14400, `applicationServer`: {"ipv4Address": "198.51.100.70"} | unit_format | unit_format | 2 |
| `v1.1.0` | `done` | `duration`: 14400, `applicationServer`: {"ipv4Address": "198.51.100.70"} |  |  | 0 |

**missing_info:** {'device.ipv4Address.publicPort': 'intent_text'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required', 'changed_meaning'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m19
**Intent:** Set up a low-latency gaming session for the device with IPv6 2001:db8:a:13::1 to 198.51.100.20 for 10 minutes, with notifications to https://app.example.org/notify/game.
**Operation:** createSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 600,
    "ueId": {
      "ipv6addr": "2001:db8:a:13::1"
    },
    "asId": {
      "ipv4addr": "198.51.100.20"
    },
    "qos": "QOS_E",
    "notificationUrl": "https://app.example.org/notify/game"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 600,
    "device": {
      "ipv6Address": "2001:db8:a:13::1"
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.20"
    },
    "qosProfile": "QOS_E",
    "sink": "https://app.example.org/notify/game"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 600, `asId`: {"ipv4addr": "198.51.100.20"} | renamed,restructured,unit_format,newly_required,changed_meaning | renamed,unit_format,newly_required | 14 |
| `v0.9.0` | `done` | `duration`: 600, `applicationServer`: {"ipv4Address": "198.51.100.20"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.10.0` | `done` | `duration`: 600, `applicationServer`: {"ipv4Address": "198.51.100.20"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.11.0` | `done` | `duration`: 600, `applicationServer`: {"ipv4Address": "198.51.100.20"} | unit_format | unit_format | 2 |
| `v1.0.0` | `done` | `duration`: 600, `applicationServer`: {"ipv4Address": "198.51.100.20"} | unit_format | unit_format | 2 |
| `v1.1.0` | `done` | `duration`: 600, `applicationServer`: {"ipv4Address": "198.51.100.20"} |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required', 'changed_meaning'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m20
**Intent:** Give phone +9901000020 a balanced video-call session to the conference server at 2001:db8:b::10 for 2 hours, with QoS notifications to https://app.example.org/notify/video.
**Operation:** createSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 7200,
    "ueId": {
      "msisdn": "9901000020"
    },
    "asId": {
      "ipv6addr": "2001:db8:b::10"
    },
    "qos": "QOS_M",
    "notificationUrl": "https://app.example.org/notify/video"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 7200,
    "device": {
      "phoneNumber": "+9901000020"
    },
    "applicationServer": {
      "ipv6Address": "2001:db8:b::10"
    },
    "qosProfile": "QOS_M",
    "sink": "https://app.example.org/notify/video"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 7200, `asId`: {"ipv6addr": "2001:db8:b::10"} | renamed,restructured,unit_format,newly_required,changed_meaning | renamed,unit_format,newly_required | 14 |
| `v0.9.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.10.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} | renamed,restructured,unit_format,newly_required | renamed,restructured,unit_format,newly_required | 6 |
| `v0.11.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} | unit_format | unit_format | 2 |
| `v1.0.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} | unit_format | unit_format | 2 |
| `v1.1.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv6Address": "2001:db8:b::10"} |  |  | 0 |

**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required', 'changed_meaning'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m21
**Intent:** Create a messaging session for the subscriber dev021@nlipeval.example to the broker at 198.51.100.50 for 8 hours.
**Operation:** createSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 28800,
    "ueId": {
      "externalId": "dev021@nlipeval.example"
    },
    "asId": {
      "ipv4addr": "198.51.100.50"
    },
    "qos": "QOS_S"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 28800,
    "device": {
      "ipv6Address": "2001:db8:a:15::1"
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.50"
    },
    "qosProfile": "QOS_S"
  }
}
```
(2 gold alternatives: {"ipv6Address": "2001:db8:a:15::1", "networkAccessIdentifier": "dev021@nlipeval.example"})
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 28800, `asId`: {"ipv4addr": "198.51.100.50"} | renamed,restructured,unit_format,newly_required | renamed,unit_format,newly_required | 14 |
| `v0.9.0` | `done` | `duration`: 28800, `applicationServer`: {"ipv4Address": "198.51.100.50"} | newly_required | unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 28800, `applicationServer`: {"ipv4Address": "198.51.100.50"} | newly_required | unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 28800, `applicationServer`: {"ipv4Address": "198.51.100.50"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 28800, `applicationServer`: {"ipv4Address": "198.51.100.50"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 28800, `applicationServer`: {"ipv4Address": "198.51.100.50"} |  |  | 0 |

**client_facts:** ipv6_address=2001:db8:a:15::1
**missing_info:** {'device.ipv6Address': 'fact'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m22
**Intent:** Set up a low-latency connection from the device at 192.0.2.22 port 40022 to the realtime server at 198.51.100.30/32 for 20 minutes.
**Operation:** createSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "POST",
  "path": "/qod/v0/sessions",
  "body": {
    "duration": 1200,
    "ueId": {
      "ipv4addr": "192.0.2.22"
    },
    "asId": {
      "ipv4addr": "198.51.100.30/32"
    },
    "qos": "QOS_E"
  }
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "POST",
  "path": "/quality-on-demand/v1/sessions",
  "body": {
    "duration": 1200,
    "device": {
      "ipv4Address": {
        "publicAddress": "192.0.2.22",
        "publicPort": 40022
      }
    },
    "applicationServer": {
      "ipv4Address": "198.51.100.30/32"
    },
    "qosProfile": "QOS_E"
  }
}
```
**Gold backend response:** HTTP 201

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 1200, `asId`: {"ipv4addr": "198.51.100.30/32"} | renamed,restructured,unit_format,newly_required | renamed,unit_format,newly_required | 14 |
| `v0.9.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} | newly_required | unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} | newly_required | unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} |  |  | 0 |

**missing_info:** {'device.ipv4Address.publicPort': 'intent_text'}
**change_tags (oldest):** request=['renamed', 'restructured', 'unit_format', 'newly_required'], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m23
**Intent:** Get the details of session a1b2c3d4-0001-4000-8000-000000000001.
**Operation:** getSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "GET",
  "path": "/qod/v0/sessions/a1b2c3d4-0001-4000-8000-000000000001",
  "body": null
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "GET",
  "path": "/quality-on-demand/v1/sessions/a1b2c3d4-0001-4000-8000-000000000001",
  "body": null
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 1800, `asId`: {"ipv4addr": "198.51.100.10"} |  | renamed,unit_format,newly_required | 8 |
| `v0.9.0` | `done` | `duration`: 1800, `applicationServer`: {"ipv4Address": "198.51.100.10"} |  | renamed,restructured,unit_format,newly_required | 4 |
| `v0.10.0` | `done` | `duration`: 1800, `applicationServer`: {"ipv4Address": "198.51.100.10"} |  | renamed,restructured,unit_format,newly_required | 4 |
| `v0.11.0` | `done` | `duration`: 1800, `applicationServer`: {"ipv4Address": "198.51.100.10"} |  | unit_format | 1 |
| `v1.0.0` | `done` | `duration`: 1800, `applicationServer`: {"ipv4Address": "198.51.100.10"} |  | unit_format | 1 |
| `v1.1.0` | `done` | `duration`: 1800, `applicationServer`: {"ipv4Address": "198.51.100.10"} |  |  | 0 |

**change_tags (oldest):** request=[], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m24
**Intent:** Show me the current status of QoS session a1b2c3d4-0001-4000-8000-000000000003.
**Operation:** getSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "GET",
  "path": "/qod/v0/sessions/a1b2c3d4-0001-4000-8000-000000000003",
  "body": null
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "GET",
  "path": "/quality-on-demand/v1/sessions/a1b2c3d4-0001-4000-8000-000000000003",
  "body": null
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 7200, `asId`: {"ipv4addr": "198.51.100.30/32"} |  | renamed,unit_format,newly_required | 8 |
| `v0.9.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} |  | unit_format,newly_required | 3 |
| `v0.10.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} |  | unit_format,newly_required | 3 |
| `v0.11.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 7200, `applicationServer`: {"ipv4Address": "198.51.100.30/32"} |  |  | 0 |

**change_tags (oldest):** request=[], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m25
**Intent:** Retrieve the details for session a1b2c3d4-0001-4000-8000-000000000005.
**Operation:** getSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "GET",
  "path": "/qod/v0/sessions/a1b2c3d4-0001-4000-8000-000000000005",
  "body": null
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "GET",
  "path": "/quality-on-demand/v1/sessions/a1b2c3d4-0001-4000-8000-000000000005",
  "body": null
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 1200, `asId`: {"ipv4addr": "198.51.100.40"} |  | renamed,unit_format,newly_required | 7 |
| `v0.9.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.40"} |  | unit_format,newly_required | 3 |
| `v0.10.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.40"} |  | unit_format,newly_required | 3 |
| `v0.11.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.40"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.40"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 1200, `applicationServer`: {"ipv4Address": "198.51.100.40"} |  |  | 0 |

**change_tags (oldest):** request=[], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m26
**Intent:** What is the status of the QoS session with ID a1b2c3d4-0001-4000-8000-000000000008?
**Operation:** getSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "GET",
  "path": "/qod/v0/sessions/a1b2c3d4-0001-4000-8000-000000000008",
  "body": null
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "GET",
  "path": "/quality-on-demand/v1/sessions/a1b2c3d4-0001-4000-8000-000000000008",
  "body": null
}
```
**Gold backend response:** HTTP 200

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | `duration`: 3600, `asId`: {"ipv6addr": "2001:db8:b::/64"} |  | renamed,unit_format,newly_required | 8 |
| `v0.9.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv6Address": "2001:db8:b::/64"} |  | unit_format,newly_required | 3 |
| `v0.10.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv6Address": "2001:db8:b::/64"} |  | unit_format,newly_required | 3 |
| `v0.11.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv6Address": "2001:db8:b::/64"} |  |  | 0 |
| `v1.0.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv6Address": "2001:db8:b::/64"} |  |  | 0 |
| `v1.1.0` | `done` | `duration`: 3600, `applicationServer`: {"ipv6Address": "2001:db8:b::/64"} |  |  | 0 |

**change_tags (oldest):** request=[], response=['renamed', 'unit_format', 'newly_required']

---
### L3-m27
**Intent:** Delete the QoS session a1b2c3d4-0001-4000-8000-000000000002.
**Operation:** deleteSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "DELETE",
  "path": "/qod/v0/sessions/a1b2c3d4-0001-4000-8000-000000000002",
  "body": null
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "DELETE",
  "path": "/quality-on-demand/v1/sessions/a1b2c3d4-0001-4000-8000-000000000002",
  "body": null
}
```
**Gold backend response:** HTTP 204

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | null |  |  | 0 |
| `v0.9.0` | `done` | null |  |  | 0 |
| `v0.10.0` | `done` | null |  |  | 0 |
| `v0.11.0` | `done` | null |  |  | 0 |
| `v1.0.0` | `done` | null |  |  | 0 |
| `v1.1.0` | `done` | null |  |  | 0 |

**change_tags (oldest):** request=[], response=[]

---
### L3-m28
**Intent:** Cancel and remove the QoS session a1b2c3d4-0001-4000-8000-000000000004.
**Operation:** deleteSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "DELETE",
  "path": "/qod/v0/sessions/a1b2c3d4-0001-4000-8000-000000000004",
  "body": null
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "DELETE",
  "path": "/quality-on-demand/v1/sessions/a1b2c3d4-0001-4000-8000-000000000004",
  "body": null
}
```
**Gold backend response:** HTTP 204

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | null |  |  | 0 |
| `v0.9.0` | `done` | null |  |  | 0 |
| `v0.10.0` | `done` | null |  |  | 0 |
| `v0.11.0` | `done` | null |  |  | 0 |
| `v1.0.0` | `done` | null |  |  | 0 |
| `v1.1.0` | `done` | null |  |  | 0 |

**change_tags (oldest):** request=[], response=[]

---
### L3-m29
**Intent:** Terminate and delete session a1b2c3d4-0001-4000-8000-000000000006.
**Operation:** deleteSession
**prompt_half:** True | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "DELETE",
  "path": "/qod/v0/sessions/a1b2c3d4-0001-4000-8000-000000000006",
  "body": null
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "DELETE",
  "path": "/quality-on-demand/v1/sessions/a1b2c3d4-0001-4000-8000-000000000006",
  "body": null
}
```
**Gold backend response:** HTTP 204

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | null |  |  | 0 |
| `v0.9.0` | `done` | null |  |  | 0 |
| `v0.10.0` | `done` | null |  |  | 0 |
| `v0.11.0` | `done` | null |  |  | 0 |
| `v1.0.0` | `done` | null |  |  | 0 |
| `v1.1.0` | `done` | null |  |  | 0 |

**change_tags (oldest):** request=[], response=[]

---
### L3-m30
**Intent:** Remove the QoS session with ID a1b2c3d4-0001-4000-8000-000000000007.
**Operation:** deleteSession
**prompt_half:** False | versions_behind (oldest): 5

**Native request at `v0.8.1` (oldest):**
```json
{
  "method": "DELETE",
  "path": "/qod/v0/sessions/a1b2c3d4-0001-4000-8000-000000000007",
  "body": null
}
```
**Gold call at `v1.1.0` (server):**
```json
{
  "method": "DELETE",
  "path": "/quality-on-demand/v1/sessions/a1b2c3d4-0001-4000-8000-000000000007",
  "body": null
}
```
**Gold backend response:** HTTP 204

**Gold client answers by version:**

| client_version | status | result summary | tags request | tags response | breaking crossed |
|---|---|---|---|---|---|
| `v0.8.1` | `done` | null |  |  | 0 |
| `v0.9.0` | `done` | null |  |  | 0 |
| `v0.10.0` | `done` | null |  |  | 0 |
| `v0.11.0` | `done` | null |  |  | 0 |
| `v1.0.0` | `done` | null |  |  | 0 |
| `v1.1.0` | `done` | null |  |  | 0 |

**change_tags (oldest):** request=[], response=[]

---
