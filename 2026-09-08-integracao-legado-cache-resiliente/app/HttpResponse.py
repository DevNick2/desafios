from enum import StrEnum

from fastapi.responses import JSONResponse


class Outcome(StrEnum):
    ACCEPTED = "accepted"
    UNAVAILABLE = "unavailable"


HTTP_STATUS = {
    Outcome.ACCEPTED: 202,
    Outcome.UNAVAILABLE: 503,
}


def to_response(outcome: Outcome) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_STATUS[outcome],
        content={"status": outcome.value},
    )
