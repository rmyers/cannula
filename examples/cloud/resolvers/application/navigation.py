import typing


class Item(typing.NamedTuple):
    id: str
    icon: str
    url: str
    name: str
    className: str = 'navigation-item'
    disabledMessage: str = 'You do not have access to this resource'
    role: str = None

    def is_enabled(self, user):
        if self.role is not None:
            return user.has_role(self.role)
        return True


class Section(typing.NamedTuple):
    title: str
    items: typing.List[Item]
    role: str = None

    def is_enabled(self, user):
        if self.role is not None:
            return user.has_role(self.role)
        return True


ALL_SECTIONS = [
    Section(title='Compute', items=[
        Item(
            id='compute-servers',
            icon='server',
            url='/servers/',
            name='Servers',
            role='compute:server'
        ),
        Item(
            id='compute-images',
            icon='image',
            url='/images/',
            name='Images',
            role='compute:image',
        ),
        Item(
            id='compute-flavors',
            icon='flavor',
            url='/flavors/',
            name='Flavors',
            role='compute:flavor',
        ),
    ]),
    Section(title='Networks', items=[
        Item(
            id='network',
            icon='network',
            url='/networks/',
            name='Networks',
            role='network',
        ),
        Item(
            id='network-new',
            icon='add',
            url='/networks/new/',
            name='Create Network',
            role='network',
        ),
    ]),
    Section(title='Volumes', items=[
        Item(
            id='volumes',
            icon='volume',
            url='/volumes/',
            name='Volumes',
            role='volume',
        ),
        Item(
            id='volume-new',
            icon='add',
            url='/volumes/new/',
            name='Create Volume',
            role='volume',
        ),
    ])
]
