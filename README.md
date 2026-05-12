# Ignition Tag Data API

Secure Web Dev API for realtime and historical Ignition tag data retrieval.

## Overview

This project provides a Web Dev-based REST API for accessing Ignition tag data, supporting both realtime reads and historical queries with aggregation. Originally developed for Grafana integration, it serves as a general-purpose data access layer for OT/IT integration use cases.

### Features

- **Realtime Tag Reads**: Query current tag values via `/real-time` endpoint
- **Raw Historical Points**: Retrieve raw historical data via `/query/raw-points`
- **Aggregated Historical Data**: Query aggregated data (Average, Min, Max, etc.) via `/query/aggregated-points`
- **API Key Authentication**: Secure endpoints using Ignition secrets
- **Legacy API Support**: Backward compatibility with Ignition 8.0 historian API
- **Health Check**: Monitor API availability via `/health` endpoint

### Use Cases

- Grafana dashboard data source for live and historical metrics
- Integration with external BI/reporting tools
- Data pipeline feeds for analytics and archives
- Mobile and web app backends for plant-floor dashboards
- MES/ERP integration endpoints

## Installation

### For Ignition Web Dev Module

1. Copy `src/tagapi.py` into your Ignition project's scripting.
2. Ensure Ignition 8.0+ is installed with Web Dev module enabled
3. Create a Webdev python resource with POST endpoint exposed.

### Example Web Dev Handler

```python
def doPost(request, session):
	return tagapi.handle_request(request, "Tag History API")
```

## API Endpoints

### Health Check

```
GET /health
Response: {"status": "ok"}
```

### Realtime Tag Read

```
POST /real-time
Headers: X-API-Key: your-api-key
Body: {
  "paths": ["[default]Device/Tag1", "[default]Device/Tag2"]
}
Response: {
  "data": [
    {"[default]Device/Tag1": 42.5},
    {"[default]Device/Tag2": 100}
  ]
}
```

### Raw Historical Points

```
POST /query/raw-points
Headers: X-API-Key: your-api-key
Body: {
  "paths": ["[default]Device/Temperature"],
  "startTime": "1683590400000",
  "endTime": "1683676800000",
  "includeBounds": false,
  "returnFormat": "WIDE",
  "returnSize": -1,
  "excludeObservations": false
}
Response: {
  "data": [
    {"t_stamp": "2023-05-09T00:00:00Z", "[default]Device/Temperature": 72.1},
    {"t_stamp": "2023-05-09T01:00:00Z", "[default]Device/Temperature": 73.2}
  ]
}
```

### Aggregated Historical Points

```
POST /query/aggregated-points
Headers: X-API-Key: your-api-key
Body: {
  "paths": ["[default]Device/Temperature"],
  "startTime": "1683590400000",
  "endTime": "1683676800000",
  "aggregationMode": "Average",
  "fillModes": ["DERIVED"],
  "includeBounds": false,
  "returnFormat": "WIDE",
  "returnSize": 1,
  "excludeObservations": false
}
Response: {
  "data": [
    {"t_stamp": "2023-05-09T00:00:00Z", "[default]Device/Temperature": 72.65}
  ]
}
```

## Configuration

### API Key Validation

Set up a Secret Provider in Ignition with API keys stored as secrets. Pass the provider name to `handle_request()`:

```python
handle_request(request, secret_provider="MySecretProvider")
```

To disable authentication, pass `None`:

```python
handle_request(request, None)
```

The API expects `X-API-Key` header.

### Force Legacy API

Pass the `X-Force-Legacy-API: true` header to force use of the legacy `tag.queryTagHistory()` API instead of the modern historian module.
