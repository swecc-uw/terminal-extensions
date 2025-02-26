from typing import Callable, Optional, Union

CommandStr = str
InterceptorFunc = Callable[[CommandStr], Union[bool, CommandStr]]
CallbackFunc = Callable[[CommandStr, int, Optional[str], Optional[str]], None]
