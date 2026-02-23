import asyncio
import inspect
from contextlib import AsyncExitStack
from typing import Union
from fastapi.dependencies.utils import get_dependant, solve_dependencies
from starlette.requests import Request


async def call(fn, *args, **kwargs):
    if inspect.iscoroutinefunction(fn):
        return await fn(*args, **kwargs)
    return await asyncio.to_thread(fn, *args, **kwargs)


def make_fake_request():
    scope = {
        "type": "http",
        "headers": [],
        "query_string": b"",
        "path_params": {},
        "state": {},
    }

    request = Request(scope)
    request.scope["fastapi_astack"] = AsyncExitStack()
    request.scope["fastapi_inner_astack"] = AsyncExitStack()
    request.scope["fastapi_function_astack"] = AsyncExitStack()
    request.scope["fastapi_dependency_cache"] = {}
    return request


def inject(fn):
    """
    Turn a function using fastapi.Depends into an injectable callable.
    """
    dependant = get_dependant(
        path="manual",
        call=fn,
    )

    async def executor(*args, request: Union[Request, None] = None, **kwargs):
        request = request or make_fake_request()

        astack = request.scope.get("fastapi_astack")
        inner_stack = request.scope.get("fastapi_inner_astack")
        function_stack = request.scope.get("fastapi_function_astack")
        cache = request.scope.get("fastapi_dependency_cache")

        if kwargs:
            from starlette.datastructures import QueryParams
            request._query_params = QueryParams(kwargs)

        solved_dependency = None
        try:
            solved_dependency = await solve_dependencies(
                request=request,
                dependant=dependant,
                body=None,
                dependency_overrides_provider=None,
                async_exit_stack=inner_stack,
                dependency_cache=cache,
                embed_body_fields=True
            )

            if solved_dependency.errors:
                raise RuntimeError(solved_dependency.errors)

            final_kwargs = {**solved_dependency.values, **kwargs}
            result = await call(fn, *args, **final_kwargs)
            return result

        finally:
            await astack.aclose() if astack else None
            await inner_stack.aclose() if inner_stack else None
            await function_stack.aclose() if function_stack else None
            if solved_dependency and solved_dependency.background_tasks:
                await solved_dependency.background_tasks()

    return executor
