import typing


class Status(typing.NamedTuple):
    label: str
    color: str = 'hxEmphasisPurple'
    working: bool = False
    icon: str = None
    tooltip: str = None
