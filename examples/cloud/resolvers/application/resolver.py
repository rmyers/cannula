import cannula

from .navigation import ALL_SECTIONS


application_resolver = cannula.Resolver(__name__)


@application_resolver.resolver("Query")
async def getNavigation(source, info, active: str):
    return [s for s in ALL_SECTIONS if s.is_enabled(info.context.user)]


@application_resolver.resolver("NavigationItem")
async def enabled(item, info):
    return item.is_enabled(info.context.user)
