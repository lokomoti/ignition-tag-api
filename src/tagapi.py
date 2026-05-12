from com.inductiveautomation.ignition.common import Dataset
from java.lang import Exception as JavaException
from java.util import Date
from system import dataset as sys_dataset
from system import date, tag

legacy_api = False

try:
    from system import historian, secrets
except ImportError:
    legacy_api = True

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False


class WebdevError(Exception):
    """Custom exception for Webdev errors."""

    pass


class WebdevResponseError(WebdevError):
    """Custom exception for WebdevResponse errors."""

    pass


class WebdevResponse(object):
    def __init__(
        self,
        html="",
        json=None,
        contentType="application/json",
        headers=None,
        statusCode=200,
    ):
        # type: (str, Dict, str, Dict, int) -> None
        self.html = html
        self.json = json if json is not None else {}
        self.contentType = contentType
        self.headers = headers if headers is not None else {}
        self.statusCode = statusCode

    @property
    def to_dict(self):
        # type: () -> Dict
        """Convert the WebdevResponse to a dictionary."""
        response = {
            "contentType": self.contentType,
            "headers": self.headers,
            "statusCode": self.statusCode,
        }
        if self.json:
            response["json"] = self.json
        elif self.html:
            response["html"] = self.html
        else:
            raise WebdevResponseError(
                "WebdevResponse must have either json or html content."
            )

        return response


if TYPE_CHECKING:
    from typing import (Callable, Dict, List, Literal, Optional, TypedDict,
                        Union)

    WebdevRequest = TypedDict(
        "WebdevRequest",
        {
            "context": Dict,
            "data": Union[Dict, List, str],
            "headers": Dict,
            "params": Dict,
            "remainingPath": str,
            "remoteAddr": str,
            "scheme": str,
        },
    )

    RawPointsBody = TypedDict(
        "RawPointsBody",
        {
            "paths": List[str],
            "startTime": str,
            "endTime": str,
            "includeBounds": bool,
            "columnNames": List[str],
            "returnFormat": Literal["WIDE", "LONG"],
            "returnSize": int,
            "excludeObservations": bool,
        },
    )

    AggregatedPointsBody = TypedDict(
        "AggregatedPointsBody",
        {
            "paths": List[str],
            "startTime": str,
            "endTime": str,
            "aggregationMode": Optional[str],
            "fillModes": Optional[list[str]],
            "includeBounds": bool,
            "columnNames": Optional[list[str]],
            "returnFormat": Optional[Literal["WIDE", "LONG"]],
            "returnSize": Optional[int],
            "excludeObservations": Optional[bool],
        },
    )

    RealtimeBody = TypedDict(
        "RealtimeBody",
        {
            "paths": List[str],
        },
    )

    EndpointFn = Callable[[WebdevRequest], WebdevResponse]
    RawAndAggregatedPointsBody = Union[RawPointsBody, AggregatedPointsBody]


def _dataset_to_list_of_dicts(ds):
    # type: (Dataset) -> List[Dict]
    """Convert an Ignition Dataset to a list of dictionaries."""
    pds = sys_dataset.toPyDataSet(ds)
    columns = pds.getColumnNames()
    return [dict(zip(columns, row)) for row in pds]


def _get_dates_from_body(body):
    # type: (RawAndAggregatedPointsBody) -> tuple[Date, Date]
    """Parse start and end times from the request body."""
    start_time = date.fromMillis(int(body["startTime"]))
    end_time = date.fromMillis(int(body["endTime"]))
    return start_time, end_time


def _get_force_legacy_api(request):
    # type: (WebdevRequest) -> bool
    """Check if the request has the header to force using the legacy API."""
    return request["headers"].get("X-Force-Legacy-API", "false").lower() == "true"


def _validate_request_body(body):
    # type: (RawAndAggregatedPointsBody) -> Optional[WebdevResponse]
    """Validate the request body for required fields."""
    if "paths" not in body or not isinstance(body["paths"], list):
        return WebdevResponse(
            json={
                "error": "Invalid request body: 'paths' is required and must be a list."
            },
            statusCode=400,
        )
    if "startTime" not in body or "endTime" not in body:
        return WebdevResponse(
            json={
                "error": "Invalid request body: 'startTime' and 'endTime' are required."
            },
            statusCode=400,
        )
    return None


def query_aggregated_points(request):
    # type: (WebdevRequest) -> WebdevResponse
    """Query aggregated historical tag values based on the request parameters."""
    data = request["data"]  # type: AggregatedPointsBody
    validation_response = _validate_request_body(data)

    if validation_response is not None:
        return validation_response

    if legacy_api or _get_force_legacy_api(request):
        try:
            ds = tag.queryTagHistory(
                paths=data["paths"],
                startDate=_get_dates_from_body(data)[0],
                endDate=_get_dates_from_body(data)[1],
                returnSize=data.get("returnSize", 1),
                returnFormat=data.get("returnFormat", "Wide"),
                includeBoundingValues=data.get("includeBounds", False),
                aggregationMode=data.get("aggregationMode", "Average"),
            )
        except JavaException as e:
            return WebdevResponse(
                json={"error": "Error querying aggregated points: {}".format(str(e))},
                statusCode=500,
            )
    else:
        try:
            aggregation_mode = data.get("aggregationMode", "Average")

            ds = historian.queryAggregatedPoints(
                paths=data["paths"],
                startTime=_get_dates_from_body(data)[0],
                endTime=_get_dates_from_body(data)[1],
                aggregates=[aggregation_mode for _ in data["paths"]],
                fillModes=data.get("fillModes", ["DERIVED" for _ in data["paths"]]),
                returnFormat=data.get("returnFormat", "WIDE"),
                returnSize=data.get("returnSize", 1),
                includeBounds=data.get("includeBounds", False),
                excludeObservations=data.get("excludeObservations", False),
            )
        except JavaException as e:
            return WebdevResponse(
                json={"error": "Error querying aggregated points: {}".format(str(e))},
                statusCode=500,
            )

    return WebdevResponse(json={"data": _dataset_to_list_of_dicts(ds)})


def query_raw_points(request):
    # type: (WebdevRequest) -> WebdevResponse
    """Query raw historical tag values based on the request parameters."""
    data = request["data"]  # type: RawPointsBody
    validation_response = _validate_request_body(data)

    if validation_response is not None:
        return validation_response

    dates = _get_dates_from_body(data)

    if legacy_api or _get_force_legacy_api(request):
        try:
            ds = tag.queryTagHistory(
                paths=data["paths"],
                startDate=dates[0],
                endDate=dates[1],
                includeBoundingValues=data.get("includeBounds", False),
                returnFormat=data.get("returnFormat", "Wide"),
                returnSize=data.get("returnSize", -1),
                excludeObservations=data.get("excludeObservations", False),
            )
        except JavaException as e:
            return WebdevResponse(
                json={"error": "Error querying raw points: {}".format(str(e))},
                statusCode=500,
            )
    else:
        try:
            ds = historian.queryRawPoints(
                paths=data["paths"],
                startTime=dates[0],
                endTime=dates[1],
                includeBounds=data.get("includeBounds", False),
                returnFormat=data.get("returnFormat", "WIDE"),
                returnSize=-1,  # TODO: Fix when IA fixes StreamingDataset return size issue
                excludeObservations=data.get("excludeObservations", False),
            )
        except JavaException as e:
            return WebdevResponse(
                json={"error": "Error querying raw points: {}".format(str(e))},
                statusCode=500,
            )

    return WebdevResponse(json={"data": _dataset_to_list_of_dicts(ds)})


def query_real_time_points(request):
    # type: (WebdevRequest) -> WebdevResponse
    """Query real-time tag values based on the request parameters."""
    data = request["data"]  # type: RealtimeBody
    paths = data.get("paths")

    if not paths or not isinstance(paths, list):
        return WebdevResponse(
            json={
                "error": "Invalid request body: 'paths' is required and must be a list."
            },
            statusCode=400,
        )

    return WebdevResponse(
        json={
            "data": [
                {path: tag_value.value}
                for path, tag_value in zip(paths, tag.readBlocking(paths))
            ]
        }
    )


def _get_api_key(request, api_key_header):
    # type: (WebdevRequest, str) -> Optional[str]
    """Get the API key from the request headers."""
    for header_name, header_value in request["headers"].items():
        if header_name.lower() == api_key_header.lower():
            return header_value
    return None


def _validate_api_key(api_key, secret_provider):
    # type: (str, str) -> bool
    """Validate API key for the API."""
    for secret in secrets.getSecrets(secret_provider):
        with secrets.readSecretValue(secret_provider, secret["name"]) as p:
            if api_key == p.getSecretAsString():
                return True

    return False


def validate_request_auth(request, secret_provider, api_key_header="X-API-Key"):
    # type: (WebdevRequest, str, str) -> Optional[WebdevResponse]
    """Validate the request by checking the API key."""
    api_key = _get_api_key(request, api_key_header)
    api_key = api_key.strip() if api_key else None

    if not api_key:
        return WebdevResponse(
            json={"error": "API key missing"},
            statusCode=401,
        )
    if not _validate_api_key(api_key, secret_provider):
        return WebdevResponse(
            json={"error": "Invalid API key"},
            statusCode=403,
        )

    return


_ROUTER = {
    "/query/aggregated-points": query_aggregated_points,
    "/query/raw-points": query_raw_points,
    "/real-time": query_real_time_points,
    "/health": lambda request: WebdevResponse(json={"status": "ok"}),
}  # type: Dict[str, EndpointFn]


def _route_request(request):
    # type: (WebdevRequest) -> WebdevResponse
    """Route the incoming request."""
    endpoint_fn = _ROUTER.get(request["remainingPath"])
    if endpoint_fn is None:
        return WebdevResponse(
            json={"error": "Endpoint not found"},
            statusCode=404,
        )
    return endpoint_fn(request)


def handle_request(request, secret_provider):
    # type: (WebdevRequest, str) -> Dict
    """Main entry point for handling incoming Webdev requests."""
    if secret_provider and not legacy_api:
        validation_response = validate_request_auth(request, secret_provider)

        if validation_response is not None:
            return validation_response

    return _route_request(request).to_dict
