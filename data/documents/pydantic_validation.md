# Pydantic Validation

## Models and fields
Pydantic models are Python classes that inherit from `BaseModel`. Type annotations define the expected data types and are used to validate and parse input. For example, `class Item(BaseModel): name: str; price: float` defines a model with a string name and numeric price.

## Field constraints
Use `Field` to define constraints and metadata, such as minimum and maximum string lengths, numeric bounds, and descriptions. For example, `name: str = Field(min_length=1, max_length=80)` restricts the length of a name.

## Optional values
In Python type annotations, `str | None` means a value may be a string or `None`. A default value of `None` makes the field optional to provide in a typical Pydantic model. Required fields should not be given a default.

## Validation errors
When input fails validation, Pydantic reports which field failed and why. FastAPI integrates with Pydantic to validate request data and returns a structured HTTP 422 response for invalid request bodies by default.
