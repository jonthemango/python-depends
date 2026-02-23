import asyncio
import pytest
from fastapi import Cookie, Header, Query
from starlette.requests import Request
from depends import inject, Depends


@pytest.mark.asyncio
async def test_sync_dependency():

    def get_db():
        return "db"

    def handler(db=Depends(get_db)):
        return f"using {db}"

    result = await inject(handler)()

    assert result == "using db"


@pytest.mark.asyncio
async def test_async_dependency():

    async def get_db():
        return "adb"

    async def handler(db=Depends(get_db)):
        return f"using {db}"

    result = await inject(handler)()

    assert result == "using adb"


@pytest.mark.asyncio
async def test_nested_dependencies():

    def dep_a():
        return "A"

    def dep_b(a=Depends(dep_a)):
        return f"B({a})"

    def handler(b=Depends(dep_b)):
        return b

    result = await inject(handler)()

    assert result == "B(A)"


@pytest.mark.asyncio
async def test_dependency_cache_enabled():

    calls = 0

    def dep():
        nonlocal calls
        calls += 1
        return "x"

    def handler(a=Depends(dep), b=Depends(dep)):
        return a + b

    result = await inject(handler)()

    assert result == "xx"
    assert calls == 1


@pytest.mark.asyncio
async def test_dependency_cache_disabled():

    calls = 0

    def dep():
        nonlocal calls
        calls += 1
        return "x"

    def handler(
        a=Depends(dep, use_cache=False),
        b=Depends(dep, use_cache=False),
    ):
        return a + b

    result = await inject(handler)()

    assert result == "xx"
    assert calls == 2



@pytest.mark.asyncio
async def test_request_injection(fake_request: Request):

    def dep(req: Request):
        return req is not None

    def handler(v=Depends(dep)):
        return v

    result = await inject(handler)(request=fake_request)

    assert result is True



@pytest.mark.asyncio
async def test_yield_dependency_cleanup():

    events = []

    async def dep():
        events.append("enter")
        yield "resource"
        events.append("exit")

    async def handler(r=Depends(dep)):
        events.append("handler")
        return r

    result = await inject(handler)()

    assert result == "resource"
    assert events == ["enter", "handler", "exit"]



@pytest.mark.asyncio
async def test_background_tasks():

    ran = False

    from starlette.background import BackgroundTasks

    def dep(tasks: BackgroundTasks):
        def job():
            nonlocal ran
            ran = True

        tasks.add_task(job)
        return "ok"

    def handler(v=Depends(dep)):
        return v

    result = await inject(handler)()

    assert result == "ok"
    assert ran is True


@pytest.mark.asyncio
async def test_kwargs_override_dependency():

    def dep():
        return "dep"

    def handler(v=Depends(dep)):
        return v

    result = await inject(handler)(v="manual")

    assert result == "manual"



@pytest.mark.asyncio
async def test_request_cache_shared(fake_request):

    calls = 0

    def dep():
        nonlocal calls
        calls += 1
        return "x"

    def handler(a=Depends(dep)):
        return a

    executor = inject(handler)

    await executor(request=fake_request)
    await executor(request=fake_request)

    # same request = same cache
    assert calls == 1



@pytest.mark.asyncio
async def test_request_isolation():

    calls = 0

    def dep():
        nonlocal calls
        calls += 1
        return "x"

    def handler(a=Depends(dep)):
        return a

    executor = inject(handler)

    await executor()
    await executor()

    # new request each call
    assert calls == 2


@pytest.mark.asyncio
async def test_sync_handler_execution():

    def handler():
        return 123

    result = await inject(handler)()

    assert result == 123


@pytest.mark.asyncio
async def test_deep_dependency_chain():

    def a(): return "A"
    def b(x=Depends(a)): return x + "B"
    def c(x=Depends(b)): return x + "C"
    def d(x=Depends(c)): return x + "D"

    result = await inject(d)()

    assert result == "ABCD"


@pytest.mark.asyncio
async def test_dependency_with_parameters():

    def dep():
        return 10

    def handler(x: int, v=Depends(dep)):
        return x*v

    result = await inject(handler)(x=5)

    assert result == 50


@pytest.mark.asyncio
async def test_dependency_exception_propagates():

    def dep():
        raise ValueError("boom")

    def handler(v=Depends(dep)):
        return v

    with pytest.raises(ValueError):
        await inject(handler)()


@pytest.mark.asyncio
async def test_yield_cleanup_on_handler_error():

    events = []

    async def dep():
        events.append("enter")
        yield "x"
        events.append("exit")

    async def handler(v=Depends(dep)):
        events.append("handler")
        raise RuntimeError()

    with pytest.raises(RuntimeError):
        await inject(handler)()

    assert events == ["enter", "handler", "exit"]



@pytest.mark.asyncio
async def test_multiple_yield_cleanup_order():

    events = []

    async def dep1():
        events.append("enter1")
        yield
        events.append("exit1")

    async def dep2():
        events.append("enter2")
        yield
        events.append("exit2")

    async def handler(
        a=Depends(dep1),
        b=Depends(dep2),
    ):
        events.append("handler")

    await inject(handler)()

    assert events == [
        "enter1",
        "enter2",
        "handler",
        "exit2",
        "exit1",
    ]


@pytest.mark.asyncio
async def test_background_task_after_execution():

    order = []

    from starlette.background import BackgroundTasks

    async def dep(tasks: BackgroundTasks):
        def job():
            order.append("background")

        tasks.add_task(job)
        yield "x"
        order.append("cleanup")

    async def handler(v=Depends(dep)):
        order.append("handler")

    await inject(handler)()

    assert order == ["handler", "cleanup", "background"]


@pytest.mark.asyncio
async def test_request_shared_across_dependencies(fake_request):

    ids = []

    def dep1(req: Request):
        ids.append(id(req))

    def dep2(req: Request):
        ids.append(id(req))

    def handler(
        a=Depends(dep1),
        b=Depends(dep2),
    ):
        pass

    await inject(handler)(request=fake_request)

    assert ids[0] == ids[1]


@pytest.mark.asyncio
async def test_parallel_execution_isolated():

    calls = 0

    async def dep():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return "x"

    async def handler(v=Depends(dep)):
        return v

    executor = inject(handler)

    await asyncio.gather(
        executor(),
        executor(),
        executor(),
    )

    # each call has its own request/cache
    assert calls == 3


@pytest.mark.asyncio
async def test_solve_depends_as_annotated_decorator():

    def dep():
        return 3

    @inject
    def handler(a=Depends(dep), x: int = 5):
        return a + x

    @inject
    def reverse_handler(x: int = 5, a=Depends(dep)):
        return a + x

    # Calling decorated handler
    result = await handler()  # no arguments, defaults apply
    assert result == 8

    result2 = await handler(x=7)  # override x
    assert result2 == 10

    # Calling decorated handler
    result = await reverse_handler()  # no arguments, defaults apply
    assert result == 8

    result2 = await reverse_handler(x=7)  # override x
    assert result2 == 10


@pytest.mark.asyncio
async def test_query_dependency():
    from fastapi import Query
    def dep(q: str = Query(...)):
        return q

    def handler(value=Depends(dep)):
        return value

    with pytest.raises(RuntimeError):
        await inject(handler)()


@pytest.mark.asyncio
async def test_cookie_dependency():
    def dep(my_cookie: str = Cookie(...)):
        return my_cookie

    def handler(value=Depends(dep)):
        return value

    with pytest.raises(RuntimeError):
        await inject(handler)()


@pytest.mark.asyncio
async def test_combined_dependencies():
    def dep_header(user_agent: str = Header(...)):
        return user_agent

    def dep_query(q: str = Query(...)):
        return q

    def handler(u=Depends(dep_header), v=Depends(dep_query)):
        return f"{u}:{v}"

    with pytest.raises(RuntimeError):
        await inject(handler)()

