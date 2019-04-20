import cProfile
import pstats
import io
import inspect
import logging
import typing


class ProfileMiddleware:

    def __init__(
        self,
        level: int = logging.DEBUG,
        logger: typing.Optional[logging.Logger] = None,
    ):
        self.level = level
        self.logger = logger or logging.getLogger(__name__)
        self.profiler = cProfile.Profile()

    async def resolve(self, _next, _resource, _info, **kwargs):
        type_name = _info.parent_type.name  # schema type (Query, Mutation)
        field_name = _info.field_name  # The attribute being resolved

        if type_name not in ['Query', 'Mutation']:
            return await self.run_it(_next, _resource, _info, **kwargs)

        self.logger.log(
            self.level,
            f'Profiling {field_name} on {type_name}'
        )

        self.profiler.enable()

        results = await self.run_it(_next, _resource, _info, **kwargs)

        self.profiler.disable()
        s = io.StringIO()
        # TODO(rmyers): Add support for 3.7+
        ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
        ps.print_stats()
        self.profiler.clear()

        self.logger.log(
            self.level,
            f'{type_name}: {field_name} profile:\n{s.getvalue()}'
        )

        return results

    async def run_it(self, _next, _resource, _info, **kwargs):
        if inspect.isawaitable(_next):
            results = await _next(_resource, _info, **kwargs)
        else:
            results = _next(_resource, _info, **kwargs)

        if inspect.isawaitable(results):
            return await results
        return results
