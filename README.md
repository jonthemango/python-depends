## python-depends

`fastapi.Depends` is so useful and provides a nice API for providing dependencies to functions.

`Depends` calls are handled by fastapi within router functions so when building
fastapi like systems outside of router functions, a compatible API would be helpful.

#### Inspiration
I drew some inspiration from https://github.com/Lancetnik/FastDepends but ultimately 
decided to just make my own lib. If you want something official and installable use that. This is more of a pet project to customize for my specific use case. Theirs seems much more robust.

## Usage
You can swap out `depends.Depends` with `fastapi.Depends`, they're the same thing.
```python3
from depends import inject, Depends

def dep():
    return 3

@inject
def my_function(x: int = 5, a=Depends(dep)):
    return a + x

my_function(x=7) # 10
```

## Setup
I haven't gone through the trouble of pushing this to pypi or anything yet.

So for now use the code "as is" in your project or library
```sh
git clone https://github.com/jonthemango/python-depends.git
pip3 install requirements.txt -U
```

## "Advanced" Usage

Alternatively you can decorate more directly (more my usecase)

```python3
from depends import inject, Depends

def dep():
    return 3

def my_function(x: int = 5, a=Depends(dep)):
    return a + x

inject(my_function)(x=7) # 10
```

## Caveats
- Not all features are tested but there are tests in `tests`.
- `request: Request` is a faked object. Needed for fastapi `solve_dependencies`.
- Custom fields like Query, Header, etc are untested and likely would have mixed results. 
The tests assert these raise RunTimeError.
  

Async functions are awaited, sync functions use `asyncio.to_thread`
```python
import inspect
import asyncio
async def call(fn, *args, **kwargs):
    if inspect.iscoroutinefunction(fn):
        return await fn(*args, **kwargs)
    return await asyncio.to_thread(fn, *args, **kwargs)
```


## Tests

```sh
pip3 install -r requirements-tests.txt -U
pytest
```

