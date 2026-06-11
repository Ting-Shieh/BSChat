from pydantic import BaseModel


class PersonScopeOutput(BaseModel):
    scope: str
    confidence: float
