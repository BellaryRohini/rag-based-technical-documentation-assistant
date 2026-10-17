# FastAPI Basics

## Creating an application
FastAPI is a Python framework for building APIs. Create an application by importing `FastAPI` and creating an instance: `app = FastAPI()`. Routes are declared using decorators such as `@app.get("/")` and `@app.post("/items")`.

## Path operations
The HTTP method in the decorator defines the operation. Use GET to read data, POST to submit or create data, PUT to replace data, PATCH to partially update data, and DELETE to remove data. The function below a decorator handles the request.

## Running the application
A common local development command is `uvicorn main:app --reload`, when the file is named `main.py` and the FastAPI instance is named `app`. The reload option restarts the server when code changes. Do not use reload mode as a production deployment strategy.

## Request bodies
FastAPI commonly uses Pydantic models to validate JSON request bodies. Define a class inheriting from `BaseModel`, add typed fields, and use it as a function parameter. FastAPI validates incoming data and returns a validation error response when the body does not match the schema.

## Error handling
Raise `HTTPException` to return an HTTP error response from a path operation. Set a suitable status code and a useful detail message. Do not return a successful response when a request has failed.
